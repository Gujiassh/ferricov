use super::contract::{
    BaselineResult, BenchmarkCase, BenchmarkSuite, CaseResult, CaseSummary, CorrectnessGate,
    Distribution, GateStatus, Outcome, Phase, RawSample, SampleArtifacts, SampleMetrics,
    ShimMetrics,
};
use super::tree::{
    artifact_ref, copy_fixture, output_changes, output_totals, safe_repository_path, sha256_file,
    snapshot_tree,
};
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use tempfile::TempDir;

const MEASUREMENT_BACKEND: &str = "linux-rusage-children-v1";
const CLOCK: &str = "monotonic";

pub fn run_baseline(
    repository_root: &Path,
    suite_path: &Path,
    manifest_path: &Path,
    output_root: &Path,
) -> Result<PathBuf, Box<dyn Error>> {
    require_linux()?;
    let repository_root = repository_root.canonicalize()?;
    let suite_path = repository_file(&repository_root, suite_path)?;
    let manifest_path = repository_file(&repository_root, manifest_path)?;
    let output_root = if output_root.is_absolute() {
        output_root.to_owned()
    } else {
        repository_root.join(output_root)
    };
    require_empty_output_root(&output_root)?;
    validate_input(&repository_root, &suite_path, &manifest_path)?;

    let suite_content = fs::read(&suite_path)?;
    let suite: BenchmarkSuite = serde_json::from_slice(&suite_content)?;
    validate_suite_semantics(&suite)?;
    let suite_sha256 = super::tree::sha256_bytes(&suite_content);
    let manifest_content = fs::read(&manifest_path)?;
    let manifest: Value = serde_json::from_slice(&manifest_content)?;
    let manifest_sha256 = super::tree::sha256_bytes(&manifest_content);
    let identity = manifest_identity(&manifest)?;
    verify_runtime_identity(&identity, &suite)?;

    let measurement_tool_path =
        safe_repository_path(&repository_root, &suite.measurement_tool.path)?;
    let actual_tool_sha256 = sha256_file(&measurement_tool_path)?;
    if actual_tool_sha256 != suite.measurement_tool.sha256 {
        return Err("benchmark measurement tool hash mismatch".into());
    }

    fs::create_dir_all(&output_root)?;
    let samples_root = output_root.join("samples");
    fs::create_dir(&samples_root)?;
    let mut sequence = 0;
    let mut raw_sample_refs = Vec::new();
    let mut case_results = Vec::new();

    for case in &suite.cases {
        let executable_sha256 = identity
            .executables
            .get(&case.command)
            .ok_or_else(|| format!("manifest does not identify executable {}", case.command))?;
        let mut case_samples = Vec::new();
        for (phase, runs) in [
            (Phase::Warmup, case.warmup_runs),
            (Phase::Measured, case.measured_runs),
        ] {
            for phase_index in 0..runs {
                let captured = capture_sample(CaptureRequest {
                    repository_root: &repository_root,
                    output_root: &output_root,
                    samples_root: &samples_root,
                    suite: &suite,
                    case,
                    phase,
                    phase_index,
                    sequence,
                    suite_sha256: &suite_sha256,
                    manifest_sha256: &manifest_sha256,
                    image_reference: &identity.image_reference,
                    image_sha256: &identity.image_sha256,
                    executable_sha256,
                    manifest_user: &identity.user,
                    measurement_tool_path: &measurement_tool_path,
                })?;
                sequence += 1;
                if !captured.sample.outcome_matches_expected {
                    return Err(format!(
                        "approved Oracle workload {} returned an unexpected outcome; raw sample retained at {}",
                        case.id,
                        captured.sample_path.display()
                    )
                    .into());
                }
                raw_sample_refs.push(artifact_ref(&output_root, &captured.sample_path)?);
                case_samples.push(captured.sample);
            }
        }
        case_results.push(case_result(case, &case_samples)?);
    }

    let result = BaselineResult {
        schema_version: 1,
        result_id: format!("{}-oracle", suite.suite_id),
        recorded_at: recorded_at()?,
        status: "baseline_only",
        performance_gate: GateStatus {
            status: "not_evaluated",
            reason: "candidate_not_available",
        },
        correctness_gate: CorrectnessGate {
            status: "not_evaluated",
            reason: "candidate_not_available",
            required_evidence_scope: "compatibility",
            evidence: None,
        },
        suite: artifact_ref(&repository_root, &suite_path)?,
        execution_manifest: artifact_ref(&repository_root, &manifest_path)?,
        measurement_tool: artifact_ref(&repository_root, &measurement_tool_path)?,
        raw_samples: raw_sample_refs,
        cases: case_results,
    };
    let result_path = output_root.join("result.json");
    write_json(&result_path, &result)?;
    validate_result(&repository_root, &result_path)?;
    Ok(result_path)
}

struct ManifestIdentity {
    image_reference: String,
    image_sha256: String,
    user: String,
    executables: BTreeMap<String, String>,
}

fn manifest_identity(document: &Value) -> Result<ManifestIdentity, Box<dyn Error>> {
    let scope = string_at(document, "/evidence/scope")?;
    if scope == "harness_self_test" {
        return Err("harness self-test manifest cannot identify an Oracle baseline".into());
    }
    let executable_values = document
        .pointer("/executables")
        .and_then(Value::as_array)
        .ok_or("execution manifest does not contain executables")?;
    let mut executables = BTreeMap::new();
    for entry in executable_values {
        let name = string_at(entry, "/name")?.to_owned();
        let sha256 = string_at(entry, "/sha256")?.to_owned();
        if executables.insert(name.clone(), sha256).is_some() {
            return Err(format!("duplicate execution manifest executable: {name}").into());
        }
    }
    Ok(ManifestIdentity {
        image_reference: string_at(document, "/image/reference")?.to_owned(),
        image_sha256: string_at(document, "/image/docker_image_id")?.to_owned(),
        user: string_at(document, "/execution/user")?.to_owned(),
        executables,
    })
}

fn string_at<'a>(document: &'a Value, pointer: &str) -> Result<&'a str, Box<dyn Error>> {
    document
        .pointer(pointer)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("execution manifest string is missing: {pointer}").into())
}

fn verify_runtime_identity(
    identity: &ManifestIdentity,
    suite: &BenchmarkSuite,
) -> Result<(), Box<dyn Error>> {
    let resolved_suite_image = inspect_image_id(&suite.image_reference)?;
    require_image_identity(
        &suite.image_reference,
        &resolved_suite_image,
        &identity.image_sha256,
    )?;
    let resolved_manifest_image = inspect_image_id(&identity.image_reference)?;
    require_image_identity(
        &identity.image_reference,
        &resolved_manifest_image,
        &identity.image_sha256,
    )?;

    let commands = suite
        .cases
        .iter()
        .map(|case| case.command.as_str())
        .collect::<BTreeSet<_>>();
    for command in commands {
        let output = run_output(
            Command::new("docker")
                .args(["run", "--rm", "--network", "none", "--entrypoint", "sh"])
                .arg(&identity.image_reference)
                .args([
                    "-c",
                    "p=$(command -v -- \"$1\") && test -n \"$p\" && sha256sum \"$p\"",
                    "sh",
                    command,
                ]),
        )?;
        let digest = String::from_utf8(output.stdout)?
            .split_ascii_whitespace()
            .next()
            .ok_or("Oracle executable hash output is empty")?
            .to_owned();
        let actual = format!("sha256:{digest}");
        let expected = identity
            .executables
            .get(command)
            .ok_or_else(|| format!("execution manifest does not identify {command}"))?;
        if &actual != expected {
            return Err(format!(
                "Oracle executable identity mismatch for {command}: expected {expected}, found {actual}"
            )
            .into());
        }
    }
    Ok(())
}

fn inspect_image_id(reference: &str) -> Result<String, Box<dyn Error>> {
    let output = run_output(
        Command::new("docker")
            .args(["image", "inspect", "--format", "{{.Id}}"])
            .arg(reference),
    )?;
    Ok(String::from_utf8(output.stdout)?.trim().to_owned())
}

fn require_image_identity(
    reference: &str,
    actual: &str,
    expected: &str,
) -> Result<(), Box<dyn Error>> {
    if actual != expected {
        return Err(format!(
            "Oracle image identity mismatch for {reference}: expected {expected}, found {actual}"
        )
        .into());
    }
    Ok(())
}

struct CaptureRequest<'a> {
    repository_root: &'a Path,
    output_root: &'a Path,
    samples_root: &'a Path,
    suite: &'a BenchmarkSuite,
    case: &'a BenchmarkCase,
    phase: Phase,
    phase_index: usize,
    sequence: usize,
    suite_sha256: &'a str,
    manifest_sha256: &'a str,
    image_reference: &'a str,
    image_sha256: &'a str,
    executable_sha256: &'a str,
    manifest_user: &'a str,
    measurement_tool_path: &'a Path,
}

struct CapturedSample {
    sample: RawSample,
    sample_path: PathBuf,
}

fn capture_sample(request: CaptureRequest<'_>) -> Result<CapturedSample, Box<dyn Error>> {
    let phase_text = match request.phase {
        Phase::Warmup => "warmup",
        Phase::Measured => "measured",
    };
    let sample_id = format!(
        "{}-{phase_text}-{:03}",
        request.case.id, request.phase_index
    );
    let sample_root = request.samples_root.join(&sample_id);
    fs::create_dir(&sample_root)?;
    let work = TempDir::new()?;
    if let Some(fixture) = &request.case.fixture {
        let source = safe_repository_path(request.repository_root, &fixture.path)?;
        copy_fixture(&source, work.path())?;
    }
    let initial_tree = snapshot_tree(work.path())?;
    let evidence = TempDir::new()?;
    let metrics_path = evidence.path().join("metrics.json");
    let stdout_path = evidence.path().join("stdout.bin");
    let stderr_path = evidence.path().join("stderr.bin");
    let host_user = host_user()?;

    let mut command = Command::new("docker");
    command.args(["run", "--rm", "--network", "none"]);
    command.args(["--user", request.manifest_user]);
    command.args(["--workdir", "/work"]);
    for (key, value) in &request.suite.environment_variables {
        command.args(["--env", &format!("{key}={value}")]);
    }
    command
        .arg("--volume")
        .arg(format!("{}:/work", work.path().display()))
        .arg("--volume")
        .arg(format!("{}:/evidence", evidence.path().display()))
        .arg("--volume")
        .arg(format!(
            "{}:/ferricov/measure.py:ro",
            request.measurement_tool_path.display()
        ))
        .args(["--entrypoint", "python3"])
        .arg(request.image_reference)
        .args([
            "/ferricov/measure.py",
            "--metrics",
            "/evidence/metrics.json",
            "--stdout",
            "/evidence/stdout.bin",
            "--stderr",
            "/evidence/stderr.bin",
            "--chown",
            &host_user,
            "--",
            &request.case.command,
        ])
        .args(&request.case.arguments);
    let docker = command.output()?;
    if !metrics_path.is_file() {
        return Err(format!(
            "container-internal measurement failed for {}: docker_status={:?} stderr={}",
            request.case.id,
            docker.status.code(),
            String::from_utf8_lossy(&docker.stderr)
        )
        .into());
    }
    if !docker.stdout.is_empty() || !docker.stderr.is_empty() {
        return Err(format!(
            "measurement wrapper polluted Docker streams for {}: stdout={} stderr={}",
            request.case.id,
            String::from_utf8_lossy(&docker.stdout),
            String::from_utf8_lossy(&docker.stderr)
        )
        .into());
    }
    let shim: ShimMetrics = serde_json::from_slice(&fs::read(&metrics_path)?)?;
    validate_shim_metrics(&shim)?;
    let outcome = Outcome {
        exit_code: shim.exit_code,
        signal: shim.signal,
    };
    let expected = Outcome {
        exit_code: Some(request.case.expected_exit_code),
        signal: None,
    };
    let expected_wrapper_code = outcome
        .exit_code
        .or_else(|| outcome.signal.map(|signal| (128 + signal).min(255)));
    if docker.status.code() != expected_wrapper_code {
        return Err(format!(
            "measurement wrapper status mismatch for {}",
            request.case.id
        )
        .into());
    }

    let final_tree = snapshot_tree(work.path())?;
    let changes = output_changes(&initial_tree, &final_tree);
    let (output_bytes, output_files) = output_totals(&changes);
    let output_tree_path = sample_root.join("output-tree.json");
    write_json(&output_tree_path, &changes)?;
    let retained_stdout = sample_root.join("stdout.bin");
    let retained_stderr = sample_root.join("stderr.bin");
    fs::copy(stdout_path, &retained_stdout)?;
    fs::copy(stderr_path, &retained_stderr)?;
    let sample = RawSample {
        schema_version: 1,
        sample_id,
        suite_id: request.suite.suite_id.clone(),
        case_id: request.case.id.clone(),
        family: request.case.family,
        sequence: request.sequence,
        phase: request.phase,
        suite_sha256: request.suite_sha256.to_owned(),
        execution_manifest_sha256: request.manifest_sha256.to_owned(),
        fixture_tree_sha256: request
            .case
            .fixture
            .as_ref()
            .map(|fixture| fixture.tree_sha256.clone()),
        observed_image_sha256: request.image_sha256.to_owned(),
        observed_executable_sha256: request.executable_sha256.to_owned(),
        measurement_tool_sha256: request.suite.measurement_tool.sha256.clone(),
        measurement_backend: shim.measurement_backend,
        clock: shim.clock,
        outcome: outcome.clone(),
        outcome_matches_expected: outcome == expected,
        metrics: SampleMetrics {
            wall_time_ns: shim.wall_time_ns,
            user_cpu_time_ns: shim.user_cpu_time_ns,
            system_cpu_time_ns: shim.system_cpu_time_ns,
            peak_rss_bytes: shim.peak_rss_bytes,
            output_bytes,
            output_files,
        },
        artifacts: SampleArtifacts {
            stdout: artifact_ref(request.output_root, &retained_stdout)?,
            stderr: artifact_ref(request.output_root, &retained_stderr)?,
            output_tree: artifact_ref(request.output_root, &output_tree_path)?,
        },
    };
    let sample_path = sample_root.join("sample.json");
    write_json(&sample_path, &sample)?;
    Ok(CapturedSample {
        sample,
        sample_path,
    })
}

fn validate_shim_metrics(metrics: &ShimMetrics) -> Result<(), Box<dyn Error>> {
    if metrics.schema_version != 1
        || metrics.measurement_backend != MEASUREMENT_BACKEND
        || metrics.clock != CLOCK
        || metrics.wall_time_ns == 0
        || metrics.peak_rss_bytes == 0
        || metrics.exit_code.is_some() == metrics.signal.is_some()
    {
        return Err("container measurement returned invalid metrics".into());
    }
    Ok(())
}

fn case_result(case: &BenchmarkCase, samples: &[RawSample]) -> Result<CaseResult, Box<dyn Error>> {
    let warmup_samples = samples
        .iter()
        .filter(|sample| sample.phase == Phase::Warmup)
        .count();
    let measured = samples
        .iter()
        .filter(|sample| sample.phase == Phase::Measured)
        .collect::<Vec<_>>();
    if warmup_samples != case.warmup_runs || measured.len() != case.measured_runs {
        return Err(format!("sample count mismatch for {}", case.id).into());
    }
    let output_bytes = measured
        .iter()
        .map(|sample| sample.metrics.output_bytes)
        .collect::<BTreeSet<_>>();
    let output_files = measured
        .iter()
        .map(|sample| sample.metrics.output_files)
        .collect::<BTreeSet<_>>();
    if output_bytes.len() != 1 || output_files.len() != 1 {
        return Err(format!("measured output size is unstable for {}", case.id).into());
    }
    let summary = CaseSummary {
        measured_samples: measured.len(),
        wall_time_ns: distribution(&measured, |sample| sample.metrics.wall_time_ns)?,
        user_cpu_time_ns: distribution(&measured, |sample| sample.metrics.user_cpu_time_ns)?,
        system_cpu_time_ns: distribution(&measured, |sample| sample.metrics.system_cpu_time_ns)?,
        peak_rss_bytes: distribution(&measured, |sample| sample.metrics.peak_rss_bytes)?,
        output_bytes: *output_bytes.iter().next().ok_or("no output byte sample")?,
        output_files: *output_files.iter().next().ok_or("no output file sample")?,
    };
    Ok(CaseResult {
        case_id: case.id.clone(),
        family: case.family,
        warmup_samples,
        measured_samples: measured.len(),
        summary,
    })
}

fn distribution(
    samples: &[&RawSample],
    field: impl Fn(&RawSample) -> u64,
) -> Result<Distribution, Box<dyn Error>> {
    if samples.len() % 2 == 0 {
        return Err("measured sample count must be odd".into());
    }
    let mut values = samples
        .iter()
        .map(|sample| field(sample))
        .collect::<Vec<_>>();
    values.sort_unstable();
    Ok(Distribution {
        minimum: values[0],
        median: values[values.len() / 2],
        maximum: values[values.len() - 1],
    })
}

fn validate_suite_semantics(suite: &BenchmarkSuite) -> Result<(), Box<dyn Error>> {
    if suite.schema_version != 1 || suite.evidence_scope != "oracle_baseline" {
        return Err("unsupported benchmark suite contract".into());
    }
    let families = suite
        .cases
        .iter()
        .map(|case| case.family)
        .collect::<BTreeSet<_>>();
    if families.len() != 4 {
        return Err("benchmark suite must cover all four M0 families".into());
    }
    for case in &suite.cases {
        if !case.approval.representative
            || case.approval.status != "approved"
            || case.approval.basis != "owner-directed-m0-oracle-baseline"
            || case.correctness_requirement.required_evidence_scope != "compatibility"
            || case.correctness_requirement.required_status != "pass"
            || case.inventory_entries.is_empty()
            || case.warmup_runs == 0
            || case.measured_runs == 0
            || case.measured_runs % 2 == 0
        {
            return Err(format!("invalid approved benchmark case: {}", case.id).into());
        }
    }
    Ok(())
}

fn validate_input(
    repository_root: &Path,
    suite_path: &Path,
    manifest_path: &Path,
) -> Result<(), Box<dyn Error>> {
    run_checked(
        Command::new("python3")
            .arg(repository_root.join("compat/benchmarks/validate.py"))
            .arg("--suite")
            .arg(suite_path),
    )?;
    run_checked(
        Command::new("python3")
            .arg(repository_root.join("compat/manifests/validate.py"))
            .arg(manifest_path),
    )?;
    Ok(())
}

fn validate_result(repository_root: &Path, result_path: &Path) -> Result<(), Box<dyn Error>> {
    run_checked(
        Command::new("python3")
            .arg(repository_root.join("compat/benchmarks/validate.py"))
            .arg("--result")
            .arg(result_path),
    )
}

fn run_checked(command: &mut Command) -> Result<(), Box<dyn Error>> {
    let output = command.output()?;
    if !output.status.success() {
        return Err(format!(
            "command failed: stdout={} stderr={}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )
        .into());
    }
    Ok(())
}

fn run_output(command: &mut Command) -> Result<Output, Box<dyn Error>> {
    let output = command.output()?;
    if !output.status.success() {
        return Err(format!(
            "command failed: stdout={} stderr={}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )
        .into());
    }
    Ok(output)
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<(), Box<dyn Error>> {
    let canonical = serde_json::to_value(value)?;
    let mut encoded = serde_json::to_vec_pretty(&canonical)?;
    encoded.push(b'\n');
    fs::write(path, encoded)?;
    Ok(())
}

fn recorded_at() -> Result<String, Box<dyn Error>> {
    let output = run_output(Command::new("date").args(["--utc", "+%Y-%m-%dT%H:%M:%SZ"]))?;
    Ok(String::from_utf8(output.stdout)?.trim().to_owned())
}

fn require_empty_output_root(path: &Path) -> Result<(), Box<dyn Error>> {
    if path.exists() && fs::read_dir(path)?.next().is_some() {
        return Err(format!(
            "benchmark output directory is not empty: {}",
            path.display()
        )
        .into());
    }
    Ok(())
}

fn repository_file(root: &Path, path: &Path) -> Result<PathBuf, Box<dyn Error>> {
    let candidate = if path.is_absolute() {
        path.to_owned()
    } else {
        root.join(path)
    };
    let canonical = candidate.canonicalize()?;
    if !canonical.starts_with(root) || !canonical.is_file() {
        return Err(format!("path is not a repository file: {}", path.display()).into());
    }
    Ok(canonical)
}

#[cfg(target_os = "linux")]
fn require_linux() -> Result<(), Box<dyn Error>> {
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn require_linux() -> Result<(), Box<dyn Error>> {
    Err("Oracle baseline collection requires Linux".into())
}

#[cfg(unix)]
fn host_user() -> Result<String, Box<dyn Error>> {
    use std::os::unix::fs::MetadataExt;
    let metadata = fs::metadata(".")?;
    Ok(format!("{}:{}", metadata.uid(), metadata.gid()))
}

#[cfg(not(unix))]
fn host_user() -> Result<String, Box<dyn Error>> {
    Err("Oracle baseline collection requires Unix UID/GID semantics".into())
}

#[cfg(test)]
mod tests {
    use super::super::contract::{ArtifactRef, Family, SampleArtifacts};
    use super::*;

    #[test]
    fn accepts_tag_that_resolves_to_manifest_image() {
        let image = format!("sha256:{}", "a".repeat(64));

        assert!(require_image_identity("ferricov/oracle:tag", &image, &image).is_ok());
    }

    #[test]
    fn rejects_tag_that_resolves_to_another_image() {
        let expected = format!("sha256:{}", "a".repeat(64));
        let actual = format!("sha256:{}", "b".repeat(64));

        let error = require_image_identity("ferricov/oracle:tag", &actual, &expected)
            .unwrap_err()
            .to_string();

        assert!(error.contains("Oracle image identity mismatch"));
        assert!(error.contains(&expected));
        assert!(error.contains(&actual));
    }

    fn sample(value: u64, phase: Phase) -> RawSample {
        let empty = ArtifactRef {
            path: "artifact".to_owned(),
            sha256: format!("sha256:{}", "0".repeat(64)),
            bytes: 0,
        };
        RawSample {
            schema_version: 1,
            sample_id: format!("sample-{value}"),
            suite_id: "suite".to_owned(),
            case_id: "case".to_owned(),
            family: Family::Startup,
            sequence: value as usize,
            phase,
            suite_sha256: empty.sha256.clone(),
            execution_manifest_sha256: empty.sha256.clone(),
            fixture_tree_sha256: None,
            observed_image_sha256: empty.sha256.clone(),
            observed_executable_sha256: empty.sha256.clone(),
            measurement_tool_sha256: empty.sha256.clone(),
            measurement_backend: MEASUREMENT_BACKEND.to_owned(),
            clock: CLOCK.to_owned(),
            outcome: Outcome {
                exit_code: Some(0),
                signal: None,
            },
            outcome_matches_expected: true,
            metrics: SampleMetrics {
                wall_time_ns: value,
                user_cpu_time_ns: value,
                system_cpu_time_ns: value,
                peak_rss_bytes: value,
                output_bytes: 0,
                output_files: 0,
            },
            artifacts: SampleArtifacts {
                stdout: empty.clone(),
                stderr: empty.clone(),
                output_tree: empty,
            },
        }
    }

    #[test]
    fn median_uses_only_measured_samples() {
        let samples = [
            sample(1_000, Phase::Warmup),
            sample(30, Phase::Measured),
            sample(10, Phase::Measured),
            sample(20, Phase::Measured),
        ];
        let measured = samples
            .iter()
            .filter(|sample| sample.phase == Phase::Measured)
            .collect::<Vec<_>>();

        assert_eq!(
            distribution(&measured, |sample| sample.metrics.wall_time_ns).unwrap(),
            Distribution {
                minimum: 10,
                median: 20,
                maximum: 30,
            }
        );
    }
}
