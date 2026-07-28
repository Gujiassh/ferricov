use super::contract::{ArtifactReference, CorrectnessBaseline, ExecutionPolicy, OracleObservation};
use crate::differential::evidence::{
    self, CleanupEvidence, persist_run, write_json_new, write_new,
};
use crate::differential::process;
use crate::differential::{
    EvidenceScope, ImplementationIdentity, Launcher, Runtime, Suite, validate_launcher,
};
use crate::{UPSTREAM_COMMIT, UPSTREAM_RELEASE};
use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Output};

const BASELINE_ID: &str = "m0-cli-oracle-correctness-v1";
const WORKING_DIRECTORY: &str = "/work";

#[derive(Debug, Deserialize)]
struct CleanEnvironment {
    inherit_parent: bool,
    allowlist: BTreeMap<String, String>,
}

#[derive(Debug, Deserialize)]
struct SuiteInput {
    suite_id: String,
    path: String,
    sha256: String,
    case_count: usize,
    environment_overrides: BTreeMap<String, String>,
}

#[derive(Debug, Deserialize)]
struct CaseContract {
    upstream_commit: String,
    clean_environment: CleanEnvironment,
    suites: Vec<SuiteInput>,
}

struct ManifestIdentity {
    image_id: String,
    executables: BTreeMap<String, String>,
}

pub fn run_baseline(
    repository_root: &Path,
    case_contract_path: &Path,
    manifest_path: &Path,
    launcher_path: &Path,
    output_root: &Path,
) -> Result<PathBuf, Box<dyn Error>> {
    let repository_root = repository_root.canonicalize()?;
    let case_contract_path = repository_file(&repository_root, case_contract_path)?;
    let launcher_path = repository_file(&repository_root, launcher_path)?;
    let manifest_path = input_file(&repository_root, manifest_path)?;
    let output_root = output_path(&repository_root, output_root);

    validate_inputs(&repository_root, &manifest_path)?;
    let case_contract: CaseContract = read_json(&case_contract_path)?;
    validate_case_contract(&case_contract)?;
    let base_environment = resolved_environment(&case_contract.clean_environment)?;

    let base_launcher: Launcher = read_json(&launcher_path)?;
    validate_launcher(&base_launcher)?;
    if base_launcher.environment_variables != base_environment {
        return Err("Oracle launcher environment does not match the M0 case contract".into());
    }
    if !matches!(base_launcher.runtime, Runtime::DockerImage { .. }) {
        return Err("Oracle correctness baseline requires a Docker launcher".into());
    }

    let manifest_document: Value = read_json(&manifest_path)?;
    let manifest_identity = manifest_identity(&manifest_document)?;

    prepare_output_root(&output_root)?;
    fs::create_dir(output_root.join("inputs"))?;
    fs::create_dir(output_root.join("inputs/suites"))?;
    fs::create_dir(output_root.join("cases"))?;

    let case_contract_artifact = copy_input(
        &output_root,
        Path::new("inputs/case-contract.json"),
        &case_contract_path,
    )?;
    let manifest_artifact = copy_input(
        &output_root,
        Path::new("inputs/execution-manifest.json"),
        &manifest_path,
    )?;
    let launcher_artifact = copy_input(
        &output_root,
        Path::new("inputs/launcher.json"),
        &launcher_path,
    )?;

    let mut suite_artifacts = Vec::new();
    let mut case_artifacts = Vec::new();
    let mut image_id_cache = BTreeMap::new();
    let mut case_ids = BTreeSet::new();

    for suite_input in &case_contract.suites {
        require_identifier(&suite_input.suite_id)?;
        let suite_path = repository_file(&repository_root, Path::new(&suite_input.path))?;
        let suite_content = fs::read(&suite_path)?;
        if evidence::sha256_hex(&suite_content) != suite_input.sha256 {
            return Err(format!("suite hash mismatch: {}", suite_input.suite_id).into());
        }
        let suite: Suite = serde_json::from_slice(&suite_content)?;
        validate_suite_input(&suite, suite_input, &mut case_ids)?;

        let suite_output = PathBuf::from(format!("inputs/suites/{}.json", suite_input.suite_id));
        suite_artifacts.push(copy_input(&output_root, &suite_output, &suite_path)?);

        let mut launcher = base_launcher.clone();
        for (key, value) in &suite_input.environment_overrides {
            launcher
                .environment_variables
                .insert(key.clone(), resolved_environment_value(key, value)?);
        }
        match &mut launcher.runtime {
            Runtime::DockerImage { image } => *image = manifest_identity.image_id.clone(),
            Runtime::Local => unreachable!("Docker launcher checked above"),
        }
        launcher.environment.image = manifest_identity.image_id.clone();
        validate_launcher(&launcher)?;

        for case in &suite.cases {
            let expected_executable = manifest_identity
                .executables
                .get(&case.command)
                .ok_or_else(|| {
                    format!(
                        "execution manifest does not identify case command {}",
                        case.command
                    )
                })?;

            let prepared =
                process::prepare(&repository_root, &launcher, case, &mut image_id_cache)?;
            let oracle_identity = prepared.identity().clone();
            validate_runtime_identity(
                &oracle_identity,
                &manifest_identity.image_id,
                expected_executable,
                &case.id,
            )?;
            let execution_user = prepared
                .execution_user()
                .ok_or("Docker baseline did not resolve an execution user")?
                .to_owned();

            let case_root = output_root.join("cases").join(&case.id);
            fs::create_dir(&case_root)?;
            let captured = process::capture(prepared, &launcher, case)?;
            let timeout_expired = captured.timeout.expired;
            let cleanup_valid = cleanup_confirmed(&captured.cleanup);
            let reference_run = persist_run(
                &case_root,
                "reference",
                &captured.captured,
                captured.timeout,
                captured.cleanup,
            )?;

            let observation = OracleObservation {
                schema_version: 1,
                suite_id: suite.suite_id.clone(),
                case_id: case.id.clone(),
                evidence_scope: suite.evidence_scope,
                upstream_commit: UPSTREAM_COMMIT,
                surface: case.surface,
                command: case.command.clone(),
                arguments: case.arguments.clone(),
                fixture: case.fixture.clone(),
                environment: launcher.environment.clone(),
                effective_environment_variables: launcher.environment_variables.clone(),
                execution_manifest_sha256: manifest_artifact.sha256.clone(),
                oracle_identity,
                execution: ExecutionPolicy {
                    network: "none",
                    read_only: true,
                    user: execution_user,
                    working_directory: WORKING_DIRECTORY,
                },
                comparison_contract: case.comparisons.clone(),
                reference_run,
                status: "observed",
                product_compatibility_evidence: false,
            };
            let observation_path = case_root.join("result.json");
            write_canonical_json_new(&observation_path, &observation)?;
            case_artifacts.push(artifact_reference(&output_root, &observation_path)?);

            if timeout_expired || !cleanup_valid {
                return Err(format!(
                    "Oracle case {} did not complete with confirmed cleanup",
                    case.id
                )
                .into());
            }
        }
    }

    let baseline = CorrectnessBaseline {
        schema_version: 1,
        baseline_id: BASELINE_ID,
        status: "complete",
        evidence_scope: "oracle_baseline",
        upstream_release: UPSTREAM_RELEASE,
        upstream_commit: UPSTREAM_COMMIT,
        oracle_qualification_evidence: true,
        product_compatibility_evidence: false,
        case_contract: case_contract_artifact,
        execution_manifest: manifest_artifact,
        launcher: launcher_artifact,
        suites: suite_artifacts,
        case_count: case_artifacts.len(),
        cases: case_artifacts,
    };
    let result_path = output_root.join("result.json");
    write_canonical_json_new(&result_path, &baseline)?;
    validate_output(&repository_root, &result_path)?;
    Ok(result_path)
}

fn validate_inputs(repository_root: &Path, manifest_path: &Path) -> Result<(), Box<dyn Error>> {
    run_checked(
        Command::new("python3")
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .arg(repository_root.join("compat/cases/m0-cli-contract.py")),
    )?;
    run_checked(
        Command::new("python3")
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .arg(repository_root.join("compat/cases/m0_config_contract.py")),
    )?;
    run_checked(
        Command::new("python3")
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .arg(repository_root.join("compat/correctness/m0_contract.py")),
    )?;
    run_checked(
        Command::new("python3")
            .arg(repository_root.join("compat/manifests/validate.py"))
            .arg(manifest_path),
    )?;
    Ok(())
}

fn validate_output(repository_root: &Path, result_path: &Path) -> Result<(), Box<dyn Error>> {
    run_checked(
        Command::new("python3")
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .arg(repository_root.join("compat/correctness/validate.py"))
            .arg(result_path)
            .arg("--skip-status"),
    )
}

fn validate_case_contract(contract: &CaseContract) -> Result<(), Box<dyn Error>> {
    if contract.upstream_commit != UPSTREAM_COMMIT {
        return Err("M0 case contract upstream commit mismatch".into());
    }
    if contract.clean_environment.inherit_parent {
        return Err("M0 correctness baseline cannot inherit the parent environment".into());
    }
    if contract.suites.is_empty() {
        return Err("M0 case contract does not contain suites".into());
    }
    let ids = contract
        .suites
        .iter()
        .map(|suite| suite.suite_id.as_str())
        .collect::<BTreeSet<_>>();
    if ids.len() != contract.suites.len() {
        return Err("M0 case contract contains duplicate suite IDs".into());
    }
    Ok(())
}

fn resolved_environment(
    clean_environment: &CleanEnvironment,
) -> Result<BTreeMap<String, String>, Box<dyn Error>> {
    if clean_environment.inherit_parent {
        return Err("clean environment must not inherit parent variables".into());
    }
    clean_environment
        .allowlist
        .iter()
        .map(|(key, value)| Ok((key.clone(), resolved_environment_value(key, value)?)))
        .collect()
}

fn resolved_environment_value(key: &str, value: &str) -> Result<String, Box<dyn Error>> {
    let resolved = value.replace("{workdir}", WORKING_DIRECTORY);
    if resolved.contains('{') || resolved.contains('}') {
        return Err(format!("unresolved environment placeholder for {key}").into());
    }
    Ok(resolved)
}

fn validate_suite_input(
    suite: &Suite,
    input: &SuiteInput,
    global_case_ids: &mut BTreeSet<String>,
) -> Result<(), Box<dyn Error>> {
    if suite.schema_version != 1
        || suite.suite_id != input.suite_id
        || suite.evidence_scope != EvidenceScope::Compatibility
        || suite.cases.len() != input.case_count
    {
        return Err(format!("suite contract mismatch: {}", input.suite_id).into());
    }
    for case in &suite.cases {
        require_identifier(&case.id)?;
        if case.comparisons.is_empty() {
            return Err(format!("case has no comparison contract: {}", case.id).into());
        }
        if !global_case_ids.insert(case.id.clone()) {
            return Err(format!("duplicate global case ID: {}", case.id).into());
        }
    }
    Ok(())
}

fn manifest_identity(document: &Value) -> Result<ManifestIdentity, Box<dyn Error>> {
    let scope = string_at(document, "/evidence/scope")?;
    if scope == "harness_self_test" {
        return Err("harness self-test manifest cannot identify an Oracle baseline".into());
    }
    let image_id = string_at(document, "/image/docker_image_id")?.to_owned();
    if string_at(document, "/image/reference")? != image_id {
        return Err("execution manifest image reference is not immutable".into());
    }
    let revision = string_at(document, "/image/labels/org.opencontainers.image.revision")?;
    if revision != UPSTREAM_COMMIT {
        return Err("execution manifest upstream revision mismatch".into());
    }

    let values = document
        .pointer("/executables")
        .and_then(Value::as_array)
        .ok_or("execution manifest does not contain executables")?;
    let mut executables = BTreeMap::new();
    for value in values {
        let name = string_at(value, "/name")?.to_owned();
        let sha256 = string_at(value, "/sha256")?.to_owned();
        if executables.insert(name.clone(), sha256).is_some() {
            return Err(format!("duplicate execution manifest executable: {name}").into());
        }
    }
    Ok(ManifestIdentity {
        image_id,
        executables,
    })
}

fn validate_runtime_identity(
    identity: &ImplementationIdentity,
    image_id: &str,
    executable_sha256: &str,
    case_id: &str,
) -> Result<(), Box<dyn Error>> {
    if identity.container_image_sha256.as_deref() != Some(image_id)
        || identity.executable_sha256 != executable_sha256
    {
        return Err(format!("Oracle runtime identity mismatch for case {case_id}").into());
    }
    Ok(())
}

fn cleanup_confirmed(cleanup: &CleanupEvidence) -> bool {
    cleanup.direct_child_reaped
        && matches!(
            (cleanup.process_group_empty, cleanup.container_absent),
            (Some(true), None) | (None, Some(true))
        )
}

fn copy_input(
    output_root: &Path,
    relative: &Path,
    source: &Path,
) -> Result<ArtifactReference, Box<dyn Error>> {
    let destination = output_root.join(relative);
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent)?;
    }
    write_new(&destination, &fs::read(source)?)?;
    artifact_reference(output_root, &destination)
}

fn artifact_reference(root: &Path, path: &Path) -> Result<ArtifactReference, Box<dyn Error>> {
    let content = fs::read(path)?;
    Ok(ArtifactReference {
        path: relative_utf8(root, path)?,
        sha256: format!("sha256:{}", evidence::sha256_hex(&content)),
        bytes: content.len() as u64,
    })
}

fn write_canonical_json_new(
    path: &Path,
    value: &impl serde::Serialize,
) -> Result<(), Box<dyn Error>> {
    let value = serde_json::to_value(value)?;
    write_json_new(path, &value)
}

fn read_json<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T, Box<dyn Error>> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}

fn string_at<'a>(document: &'a Value, pointer: &str) -> Result<&'a str, Box<dyn Error>> {
    document
        .pointer(pointer)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("JSON string is missing: {pointer}").into())
}

fn require_identifier(value: &str) -> Result<(), Box<dyn Error>> {
    if value.is_empty()
        || !value.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"._-".contains(&byte)
        })
        || !value.as_bytes()[0].is_ascii_lowercase() && !value.as_bytes()[0].is_ascii_digit()
    {
        return Err(format!("invalid evidence identifier: {value}").into());
    }
    Ok(())
}

fn repository_file(root: &Path, path: &Path) -> Result<PathBuf, Box<dyn Error>> {
    let canonical = input_file(root, path)?;
    if !canonical.starts_with(root) {
        return Err(format!("path is outside the repository: {}", path.display()).into());
    }
    Ok(canonical)
}

fn input_file(root: &Path, path: &Path) -> Result<PathBuf, Box<dyn Error>> {
    let candidate = if path.is_absolute() {
        path.to_owned()
    } else {
        root.join(path)
    };
    let canonical = candidate.canonicalize()?;
    if !canonical.is_file() {
        return Err(format!("input is not a file: {}", path.display()).into());
    }
    Ok(canonical)
}

fn output_path(root: &Path, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_owned()
    } else {
        root.join(path)
    }
}

fn prepare_output_root(path: &Path) -> Result<(), Box<dyn Error>> {
    match fs::symlink_metadata(path) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() || !metadata.is_dir() {
                return Err(
                    format!("output root must be a real directory: {}", path.display()).into(),
                );
            }
            if fs::read_dir(path)?.next().is_some() {
                return Err(format!("output root is not empty: {}", path.display()).into());
            }
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            fs::create_dir_all(path)?;
        }
        Err(error) => return Err(error.into()),
    }
    Ok(())
}

fn relative_utf8(root: &Path, path: &Path) -> Result<String, Box<dyn Error>> {
    let relative = path.strip_prefix(root)?;
    if relative.components().any(|component| {
        matches!(
            component,
            Component::ParentDir | Component::RootDir | Component::Prefix(_)
        )
    }) {
        return Err("artifact path escapes output root".into());
    }
    Ok(relative
        .to_str()
        .ok_or("artifact path is not valid UTF-8")?
        .replace(std::path::MAIN_SEPARATOR, "/"))
}

fn run_checked(command: &mut Command) -> Result<(), Box<dyn Error>> {
    let output = command.output()?;
    if !output.status.success() {
        return command_error(output);
    }
    Ok(())
}

fn command_error(output: Output) -> Result<(), Box<dyn Error>> {
    Err(format!(
        "command failed: stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    )
    .into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clean_environment_resolves_only_workdir() {
        let environment = CleanEnvironment {
            inherit_parent: false,
            allowlist: BTreeMap::from([
                ("HOME".to_owned(), "{workdir}".to_owned()),
                ("LANG".to_owned(), "C".to_owned()),
            ]),
        };
        assert_eq!(
            resolved_environment(&environment).unwrap(),
            BTreeMap::from([
                ("HOME".to_owned(), "/work".to_owned()),
                ("LANG".to_owned(), "C".to_owned()),
            ])
        );
    }

    #[test]
    fn clean_environment_rejects_parent_inheritance_and_unknown_placeholders() {
        let inherited = CleanEnvironment {
            inherit_parent: true,
            allowlist: BTreeMap::new(),
        };
        assert!(resolved_environment(&inherited).is_err());

        let unresolved = CleanEnvironment {
            inherit_parent: false,
            allowlist: BTreeMap::from([("HOME".to_owned(), "{unknown}".to_owned())]),
        };
        assert!(resolved_environment(&unresolved).is_err());
    }

    #[test]
    fn suite_environment_resolves_workdir_and_rejects_unknown_placeholders() {
        assert_eq!(
            resolved_environment_value("HOME", "{workdir}/home").unwrap(),
            "/work/home"
        );
        assert!(resolved_environment_value("HOME", "{unknown}/home").is_err());
    }

    #[test]
    fn manifest_identity_rejects_harness_and_duplicate_executables() {
        let harness = serde_json::json!({
            "evidence": {"scope": "harness_self_test"},
            "image": {
                "docker_image_id": format!("sha256:{}", "a".repeat(64)),
                "reference": format!("sha256:{}", "a".repeat(64)),
                "labels": {"org.opencontainers.image.revision": UPSTREAM_COMMIT}
            },
            "executables": []
        });
        assert!(manifest_identity(&harness).is_err());

        let duplicate = serde_json::json!({
            "evidence": {"scope": "environment_smoke"},
            "image": {
                "docker_image_id": format!("sha256:{}", "a".repeat(64)),
                "reference": format!("sha256:{}", "a".repeat(64)),
                "labels": {"org.opencontainers.image.revision": UPSTREAM_COMMIT}
            },
            "executables": [
                {"name": "lcov", "sha256": format!("sha256:{}", "b".repeat(64))},
                {"name": "lcov", "sha256": format!("sha256:{}", "b".repeat(64))}
            ]
        });
        assert!(manifest_identity(&duplicate).is_err());
    }

    #[test]
    fn identifiers_reject_paths_and_uppercase() {
        assert!(require_identifier("m0-valid.case").is_ok());
        assert!(require_identifier("../escape").is_err());
        assert!(require_identifier("Uppercase").is_err());
    }

    #[test]
    fn nonempty_output_root_is_rejected() {
        let root = tempfile::TempDir::new().unwrap();
        fs::write(root.path().join("existing"), b"x").unwrap();
        assert!(prepare_output_root(root.path()).is_err());
    }
}
