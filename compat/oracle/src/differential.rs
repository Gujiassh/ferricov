//! Differential execution, comparison, and evidence collection.

mod evidence;
mod process;

use crate::UPSTREAM_COMMIT;
use crate::normalizer::{NormalizerId, normalize};
use evidence::{
    CleanupEvidence, RunResult, exit_parts, persist_run, sha256_hex, write_json_new, write_new,
};
use process::CaptureOutcome;
use serde::de::{self, MapAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::fs;
use std::path::{Component, Path, PathBuf};

// ── Public types ─────────────────────────────────────────────────────────

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceScope {
    HarnessSelfTest,
    Compatibility,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Surface {
    Cli,
    Config,
    Tracefile,
    Report,
    Capture,
    Converter,
    Callback,
    Installation,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Dimension {
    Exit,
    Stdout,
    Stderr,
    Filesystem,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Pass,
    Fail,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Suite {
    pub schema_version: u32,
    pub suite_id: String,
    pub evidence_scope: EvidenceScope,
    pub cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub id: String,
    pub surface: Surface,
    pub command: String,
    #[serde(default)]
    pub arguments: Vec<String>,
    pub fixture: Option<String>,
    pub comparisons: Vec<ComparisonRequest>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ComparisonRequest {
    pub dimension: Dimension,
    pub normalizer: NormalizerId,
}

#[derive(Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Launcher {
    pub schema_version: u32,
    pub name: String,
    pub program: String,
    pub arguments: Vec<String>,
    #[serde(deserialize_with = "deserialize_environment_variables")]
    pub environment_variables: BTreeMap<String, String>,
    #[serde(default)]
    pub timeout_seconds: Option<u64>,
    pub runtime: Runtime,
    pub environment: Environment,
}

#[derive(Debug, Deserialize, Eq, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Runtime {
    Local,
    DockerImage { image: String },
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Environment {
    pub image: String,
    pub operating_system: String,
    pub architecture: String,
    pub compiler: Option<String>,
    pub cpu: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ImplementationIdentity {
    pub kind: IdentityKind,
    pub executable_sha256: String,
    pub container_image_sha256: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum IdentityKind {
    LocalExecutable,
    DockerImage,
}

// ── Internal types ───────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
struct DifferentialResult<'a> {
    schema_version: u32,
    suite_id: &'a str,
    case_id: &'a str,
    evidence_scope: EvidenceScope,
    upstream_commit: &'static str,
    surface: Surface,
    command: &'a str,
    arguments: &'a [String],
    fixture: Option<&'a str>,
    environment: &'a Environment,
    effective_environment_variables: &'a BTreeMap<String, String>,
    implementation_identities: ImplementationIdentities,
    runs: Runs,
    comparisons: Vec<ComparisonResult>,
    overall_status: Status,
}

#[derive(Debug, Serialize)]
struct ImplementationIdentities {
    reference: ImplementationIdentity,
    candidate: ImplementationIdentity,
}

#[derive(Debug, Serialize)]
struct Runs {
    reference: RunResult,
    candidate: RunResult,
}

#[derive(Debug, Serialize)]
struct ComparisonResult {
    dimension: Dimension,
    status: Status,
    normalizer: String,
    evidence: Vec<String>,
    artifacts: Vec<ArtifactReference>,
    details: Option<String>,
}

#[derive(Debug, Serialize)]
struct ArtifactReference {
    path: String,
    sha256: String,
    bytes: u64,
}

struct ComparedArtifacts {
    matches: bool,
    details: Option<String>,
    evidence: Vec<String>,
    artifacts: Vec<ArtifactReference>,
}

// ── Runner ───────────────────────────────────────────────────────────────

pub struct DifferentialRunner {
    repository_root: PathBuf,
    reference: Launcher,
    candidate: Launcher,
    image_id_cache: BTreeMap<String, String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SuiteOutcome {
    pub passed: usize,
    pub failed: usize,
}

impl DifferentialRunner {
    pub fn new(
        repository_root: PathBuf,
        reference: Launcher,
        candidate: Launcher,
    ) -> Result<Self, Box<dyn Error>> {
        validate_launcher(&reference)?;
        validate_launcher(&candidate)?;
        Ok(Self {
            repository_root,
            reference,
            candidate,
            image_id_cache: BTreeMap::new(),
        })
    }

    pub fn verify_result_artifacts(case_root: &Path) -> Result<(), Box<dyn Error>> {
        validate_result_artifacts(case_root)
    }

    pub fn run(
        &mut self,
        suite: &Suite,
        output_root: &Path,
    ) -> Result<SuiteOutcome, Box<dyn Error>> {
        validate_suite(suite, &self.reference, &self.candidate)?;
        prepare_output_root(output_root)?;

        let mut summary = BTreeMap::new();
        for case in &suite.cases {
            let status = self.run_case(suite, case, output_root)?;
            let previous = summary.insert(case.id.clone(), status);
            debug_assert!(
                previous.is_none(),
                "suite validation enforces unique case IDs"
            );
        }
        write_json_new(&output_root.join("summary.json"), &summary)?;
        Ok(SuiteOutcome {
            passed: summary.values().filter(|s| **s == Status::Pass).count(),
            failed: summary.values().filter(|s| **s == Status::Fail).count(),
        })
    }

    fn run_case(
        &mut self,
        suite: &Suite,
        case: &Case,
        output_root: &Path,
    ) -> Result<Status, Box<dyn Error>> {
        let case_root = output_root.join(&case.id);
        if fs::symlink_metadata(&case_root).is_ok() {
            return Err(format!(
                "case output path already exists; refusing to overwrite: {}",
                case_root.display()
            )
            .into());
        }
        let reference_prepared = process::prepare(
            &self.repository_root,
            &self.reference,
            case,
            &mut self.image_id_cache,
        )?;
        let reference_identity = reference_prepared.identity().clone();
        let candidate_prepared = process::prepare(
            &self.repository_root,
            &self.candidate,
            case,
            &mut self.image_id_cache,
        )?;
        let candidate_identity = candidate_prepared.identity().clone();

        if suite.evidence_scope == EvidenceScope::Compatibility
            && reference_identity.executable_sha256 == candidate_identity.executable_sha256
        {
            return Err(format!(
                "compatibility evidence cannot compare identical runtime identity {}",
                reference_identity.executable_sha256
            )
            .into());
        }

        fs::create_dir(&case_root)?;

        let CaptureOutcome {
            captured: reference_captured,
            timeout: reference_timeout,
            cleanup: reference_cleanup,
        } = process::capture(reference_prepared, &self.reference, case)?;
        let CaptureOutcome {
            captured: candidate_captured,
            timeout: candidate_timeout,
            cleanup: candidate_cleanup,
        } = process::capture(candidate_prepared, &self.candidate, case)?;

        let reference_timed_out = reference_timeout.expired;
        let candidate_timed_out = candidate_timeout.expired;
        let reference_cleanup_confirmed = cleanup_confirmed(&reference_cleanup);
        let candidate_cleanup_confirmed = cleanup_confirmed(&candidate_cleanup);
        let reference_result = persist_run(
            &case_root,
            "reference",
            &reference_captured,
            reference_timeout,
            reference_cleanup,
        )?;
        let candidate_result = persist_run(
            &case_root,
            "candidate",
            &candidate_captured,
            candidate_timeout,
            candidate_cleanup,
        )?;

        let comparisons = compare_runs(case, &case_root, &reference_captured, &candidate_captured)?;
        let overall_status = if !reference_timed_out
            && !candidate_timed_out
            && reference_cleanup_confirmed
            && candidate_cleanup_confirmed
            && comparisons.iter().all(|c| c.status == Status::Pass)
        {
            Status::Pass
        } else {
            Status::Fail
        };

        let result = DifferentialResult {
            schema_version: 1,
            suite_id: &suite.suite_id,
            case_id: &case.id,
            evidence_scope: suite.evidence_scope,
            upstream_commit: UPSTREAM_COMMIT,
            surface: case.surface,
            command: &case.command,
            arguments: &case.arguments,
            fixture: case.fixture.as_deref(),
            environment: &self.reference.environment,
            effective_environment_variables: &self.reference.environment_variables,
            implementation_identities: ImplementationIdentities {
                reference: reference_identity,
                candidate: candidate_identity,
            },
            runs: Runs {
                reference: reference_result,
                candidate: candidate_result,
            },
            comparisons,
            overall_status,
        };
        write_json_new(&case_root.join("result.json"), &result)?;

        validate_result_artifacts(&case_root).map_err(|e| {
            format!(
                "result artifact integrity check failed for case {}: {e}",
                case.id
            )
        })?;

        Ok(overall_status)
    }
}

fn cleanup_confirmed(cleanup: &CleanupEvidence) -> bool {
    cleanup.direct_child_reaped
        && matches!(
            (cleanup.process_group_empty, cleanup.container_absent),
            (Some(true), None) | (None, Some(true))
        )
}

fn prepare_output_root(output_root: &Path) -> Result<(), Box<dyn Error>> {
    match fs::symlink_metadata(output_root) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() || !metadata.is_dir() {
                return Err(format!(
                    "output root must be a real directory: {}",
                    output_root.display()
                )
                .into());
            }
            if fs::symlink_metadata(output_root.join("summary.json")).is_ok() {
                return Err(format!(
                    "summary output already exists; refusing to overwrite: {}",
                    output_root.join("summary.json").display()
                )
                .into());
            }
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            fs::create_dir_all(output_root)?;
        }
        Err(error) => return Err(error.into()),
    }
    Ok(())
}

// ── Result validation ────────────────────────────────────────────────────

/// Validate that every retained artifact in a case result directory matches
/// its recorded SHA-256 hash and that artifact paths are safe (no escape,
/// no symlinks outside case_root).
pub fn validate_result_artifacts(case_root: &Path) -> Result<(), Box<dyn Error>> {
    let result_path = case_root.join("result.json");
    reject_symlink_components(case_root, Path::new("result.json"))?;
    let result_json = fs::read_to_string(&result_path)?;
    let result: serde_json::Value = serde_json::from_str(&result_json)
        .map_err(|e| format!("failed to parse result.json: {e}"))?;

    let runs = result.get("runs").ok_or("result.json missing 'runs'")?;
    for role in ["reference", "candidate"] {
        let run = runs
            .get(role)
            .ok_or_else(|| format!("result.json missing runs.{role}"))?;
        validate_run_artifacts(case_root, role, run)?;
    }
    let comparisons = result
        .get("comparisons")
        .and_then(serde_json::Value::as_array)
        .ok_or("result.json missing 'comparisons'")?;
    for comparison in comparisons {
        validate_comparison_artifacts(case_root, comparison)?;
    }
    Ok(())
}

fn validate_run_artifacts(
    case_root: &Path,
    role: &str,
    run: &serde_json::Value,
) -> Result<(), Box<dyn Error>> {
    for artifact in ["stdout", "stderr", "file_tree"] {
        let artifact_key = format!("{artifact}_artifact");
        let sha256_key = format!("{artifact}_sha256");
        let bytes_key = format!("{artifact}_bytes");

        let artifact_path = run
            .get(&artifact_key)
            .and_then(|v| v.as_str())
            .ok_or_else(|| format!("{role} missing {artifact_key}"))?;

        let expected_path = format!(
            "{role}/{}",
            match artifact {
                "stdout" => "stdout.bin",
                "stderr" => "stderr.bin",
                "file_tree" => "file-tree.json",
                _ => unreachable!(),
            }
        );
        if artifact_path != expected_path {
            return Err(format!(
                "{role} {artifact}_artifact must be {expected_path}, got {artifact_path}"
            )
            .into());
        }

        let expected_sha256 = run
            .get(&sha256_key)
            .and_then(|v| v.as_str())
            .ok_or_else(|| format!("{role} missing {sha256_key}"))?;
        let expected_bytes = run
            .get(&bytes_key)
            .and_then(|v| v.as_u64())
            .ok_or_else(|| format!("{role} missing {bytes_key}"))?;

        validate_artifact_file(case_root, artifact_path, expected_sha256, expected_bytes)?;
    }
    Ok(())
}

fn validate_comparison_artifacts(
    case_root: &Path,
    comparison: &serde_json::Value,
) -> Result<(), Box<dyn Error>> {
    let dimension = comparison
        .get("dimension")
        .and_then(serde_json::Value::as_str)
        .ok_or("comparison missing dimension")?;
    let artifacts = comparison
        .get("artifacts")
        .and_then(serde_json::Value::as_array)
        .ok_or_else(|| format!("{dimension} comparison missing artifacts"))?;
    let expected_paths: &[&str] = match dimension {
        "exit" => &[],
        "stdout" => &[
            "normalized/reference-stdout.bin",
            "normalized/candidate-stdout.bin",
        ],
        "stderr" => &[
            "normalized/reference-stderr.bin",
            "normalized/candidate-stderr.bin",
        ],
        "filesystem" => &["reference/file-tree.json", "candidate/file-tree.json"],
        other => return Err(format!("unsupported comparison dimension: {other}").into()),
    };
    if artifacts.len() != expected_paths.len() {
        return Err(format!(
            "{dimension} comparison must retain {} artifacts, got {}",
            expected_paths.len(),
            artifacts.len()
        )
        .into());
    }
    for (artifact, expected_path) in artifacts.iter().zip(expected_paths) {
        let path = artifact
            .get("path")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| format!("{dimension} comparison artifact missing path"))?;
        if path != *expected_path {
            return Err(format!(
                "{dimension} comparison artifact must be {expected_path}, got {path}"
            )
            .into());
        }
        let sha256 = artifact
            .get("sha256")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| format!("{dimension} comparison artifact missing sha256"))?;
        let bytes = artifact
            .get("bytes")
            .and_then(serde_json::Value::as_u64)
            .ok_or_else(|| format!("{dimension} comparison artifact missing bytes"))?;
        validate_artifact_file(case_root, path, sha256, bytes)?;
    }
    Ok(())
}

fn validate_artifact_file(
    case_root: &Path,
    artifact_path: &str,
    expected_sha256: &str,
    expected_bytes: u64,
) -> Result<(), Box<dyn Error>> {
    let relative = Path::new(artifact_path);
    reject_symlink_components(case_root, relative)?;
    let full_path = case_root.join(relative);
    let metadata = fs::symlink_metadata(&full_path)?;
    if !metadata.is_file() {
        return Err(format!("artifact is not a regular file: {artifact_path}").into());
    }
    let content = fs::read(&full_path)?;
    let actual_sha256 = sha256_hex(&content);
    if actual_sha256 != expected_sha256 {
        return Err(format!(
            "artifact {artifact_path} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
        .into());
    }
    let actual_bytes = content.len() as u64;
    if actual_bytes != expected_bytes {
        return Err(format!(
            "artifact {artifact_path} size mismatch: expected {expected_bytes}, got {actual_bytes}"
        )
        .into());
    }
    Ok(())
}

fn reject_symlink_components(case_root: &Path, relative: &Path) -> Result<(), Box<dyn Error>> {
    if relative.as_os_str().is_empty()
        || relative
            .components()
            .any(|component| !matches!(component, Component::Normal(_) | Component::CurDir))
    {
        return Err(format!(
            "artifact path must stay relative to case_root: {}",
            relative.display()
        )
        .into());
    }
    let root_metadata = fs::symlink_metadata(case_root)?;
    if root_metadata.file_type().is_symlink() || !root_metadata.is_dir() {
        return Err(format!(
            "case_root must be a real directory: {}",
            case_root.display()
        )
        .into());
    }
    let mut current = case_root.to_path_buf();
    for component in relative.components() {
        if let Component::Normal(segment) = component {
            current.push(segment);
            let metadata = fs::symlink_metadata(&current).map_err(|error| {
                format!(
                    "cannot inspect artifact component {}: {error}",
                    current.display()
                )
            })?;
            if metadata.file_type().is_symlink() {
                return Err(
                    format!("artifact path contains a symlink: {}", current.display()).into(),
                );
            }
        }
    }
    Ok(())
}

// ── Launcher validation ──────────────────────────────────────────────────

fn validate_launcher(launcher: &Launcher) -> Result<(), Box<dyn Error>> {
    if launcher.schema_version != 1 {
        return Err(format!(
            "launcher {} uses unsupported schema version {}",
            launcher.name, launcher.schema_version
        )
        .into());
    }
    let command_placeholders = std::iter::once(&launcher.program)
        .chain(launcher.arguments.iter())
        .map(|argument| argument.matches("{command}").count())
        .sum::<usize>();
    if command_placeholders != 1 {
        return Err(format!(
            "launcher {} must contain exactly one {{command}} placeholder",
            launcher.name
        )
        .into());
    }
    validate_environment_variables(&launcher.environment_variables)?;
    if let Some(timeout) = launcher.timeout_seconds {
        if !(1..=process::MAX_TIMEOUT_SECONDS).contains(&timeout) {
            return Err(format!(
                "launcher {} timeout_seconds must be between 1 and {}",
                launcher.name,
                process::MAX_TIMEOUT_SECONDS
            )
            .into());
        }
    }
    if let Runtime::DockerImage { image } = &launcher.runtime {
        if launcher.environment.image != *image {
            return Err(format!(
                "launcher {} runtime image must match its declared environment image",
                launcher.name
            )
            .into());
        }
    }
    Ok(())
}

fn deserialize_environment_variables<'de, D>(
    deserializer: D,
) -> Result<BTreeMap<String, String>, D::Error>
where
    D: Deserializer<'de>,
{
    struct EnvironmentVariablesVisitor;
    impl<'de> Visitor<'de> for EnvironmentVariablesVisitor {
        type Value = BTreeMap<String, String>;
        fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            f.write_str("an object with unique environment variable keys")
        }
        fn visit_map<M>(self, mut map: M) -> Result<Self::Value, M::Error>
        where
            M: MapAccess<'de>,
        {
            let mut vars = BTreeMap::new();
            while let Some((k, v)) = map.next_entry::<String, String>()? {
                if vars.insert(k.clone(), v).is_some() {
                    return Err(de::Error::custom(format!(
                        "duplicate environment variable key: {k}"
                    )));
                }
            }
            Ok(vars)
        }
    }
    deserializer.deserialize_map(EnvironmentVariablesVisitor)
}

fn validate_environment_variables(vars: &BTreeMap<String, String>) -> Result<(), Box<dyn Error>> {
    for (key, value) in vars {
        let mut bytes = key.bytes();
        let valid_first = bytes
            .next()
            .is_some_and(|b| b.is_ascii_alphabetic() || b == b'_');
        if !valid_first || !bytes.all(|b| b.is_ascii_alphanumeric() || b == b'_') {
            return Err(format!("invalid environment variable key: {key:?}").into());
        }
        if value.contains('\0') {
            return Err(format!("environment variable {key} contains a NUL byte").into());
        }
    }
    Ok(())
}

// ── Suite validation ─────────────────────────────────────────────────────

fn validate_suite(
    suite: &Suite,
    reference: &Launcher,
    candidate: &Launcher,
) -> Result<(), Box<dyn Error>> {
    if suite.schema_version != 1 {
        return Err(format!("unsupported suite schema version: {}", suite.schema_version).into());
    }
    validate_identifier("suite", &suite.suite_id)?;
    if suite.cases.is_empty() {
        return Err("suite must contain at least one case".into());
    }
    if reference.environment != candidate.environment {
        return Err("reference and candidate launchers must declare the same environment".into());
    }
    if reference.environment_variables != candidate.environment_variables {
        return Err(
            "reference and candidate launchers must declare the same environment variables".into(),
        );
    }
    let mut case_ids = BTreeSet::new();
    for case in &suite.cases {
        validate_identifier("case", &case.id)?;
        if !case_ids.insert(&case.id) {
            return Err(format!("duplicate case ID: {}", case.id).into());
        }
        if case.comparisons.is_empty() {
            return Err(format!("case {} has no comparisons", case.id).into());
        }
        let mut dimensions = BTreeSet::new();
        for comparison in &case.comparisons {
            if !dimensions.insert(comparison.dimension) {
                return Err(format!(
                    "case {} has duplicate {:?} comparison",
                    case.id, comparison.dimension
                )
                .into());
            }
            if matches!(
                comparison.dimension,
                Dimension::Exit | Dimension::Filesystem
            ) && comparison.normalizer != NormalizerId::ExactV1
            {
                return Err(format!(
                    "case {} must use exact-v1 for {:?} comparison",
                    case.id, comparison.dimension
                )
                .into());
            }
        }
    }
    Ok(())
}

fn validate_identifier(kind: &str, value: &str) -> Result<(), Box<dyn Error>> {
    let valid = value.len() >= 2
        && value
            .bytes()
            .next()
            .is_some_and(|b| b.is_ascii_lowercase() || b.is_ascii_digit())
        && value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
        });
    if valid {
        Ok(())
    } else {
        Err(format!("invalid {kind} identifier: {value}").into())
    }
}

// ── Comparison logic ─────────────────────────────────────────────────────

fn compare_runs(
    case: &Case,
    case_root: &Path,
    reference: &evidence::CapturedRun,
    candidate: &evidence::CapturedRun,
) -> Result<Vec<ComparisonResult>, Box<dyn Error>> {
    if case
        .comparisons
        .iter()
        .any(|request| matches!(request.dimension, Dimension::Stdout | Dimension::Stderr))
    {
        fs::create_dir(case_root.join("normalized"))?;
    }
    let mut results = Vec::with_capacity(case.comparisons.len());
    for request in &case.comparisons {
        let compared = match request.dimension {
            Dimension::Exit => ComparedArtifacts {
                matches: exit_parts(&reference.exit_status) == exit_parts(&candidate.exit_status),
                details: None,
                evidence: vec![
                    "reference exit status".to_owned(),
                    "candidate exit status".to_owned(),
                ],
                artifacts: Vec::new(),
            },
            Dimension::Stdout => compare_bytes(
                case_root,
                "stdout",
                request.normalizer,
                &reference.stdout,
                &candidate.stdout,
            )?,
            Dimension::Stderr => compare_bytes(
                case_root,
                "stderr",
                request.normalizer,
                &reference.stderr,
                &candidate.stderr,
            )?,
            Dimension::Filesystem => {
                let matches = reference.file_tree == candidate.file_tree;
                ComparedArtifacts {
                    matches,
                    details: (!matches).then(|| "file tree entries differ".to_owned()),
                    evidence: vec![
                        "reference/file-tree.json".to_owned(),
                        "candidate/file-tree.json".to_owned(),
                    ],
                    artifacts: vec![
                        artifact_reference(
                            "reference/file-tree.json".to_owned(),
                            &serde_json::to_vec_pretty(&reference.file_tree)?,
                        ),
                        artifact_reference(
                            "candidate/file-tree.json".to_owned(),
                            &serde_json::to_vec_pretty(&candidate.file_tree)?,
                        ),
                    ],
                }
            }
        };
        results.push(ComparisonResult {
            dimension: request.dimension,
            status: if compared.matches {
                Status::Pass
            } else {
                Status::Fail
            },
            normalizer: request.normalizer.to_string(),
            evidence: compared.evidence,
            artifacts: compared.artifacts,
            details: compared.details,
        });
    }
    Ok(results)
}

fn compare_bytes(
    case_root: &Path,
    name: &str,
    normalizer: NormalizerId,
    reference: &[u8],
    candidate: &[u8],
) -> Result<ComparedArtifacts, Box<dyn Error>> {
    let reference_normalized = normalize(normalizer, reference);
    let candidate_normalized = normalize(normalizer, candidate);
    let normalized_root = case_root.join("normalized");
    let reference_path = normalized_root.join(format!("reference-{name}.bin"));
    let candidate_path = normalized_root.join(format!("candidate-{name}.bin"));
    write_new(&reference_path, &reference_normalized)?;
    write_new(&candidate_path, &candidate_normalized)?;
    let matches = reference_normalized == candidate_normalized;
    Ok(ComparedArtifacts {
        matches,
        details: (!matches).then(|| {
            format!(
                "normalized {name} differs: reference={} bytes candidate={} bytes",
                reference_normalized.len(),
                candidate_normalized.len()
            )
        }),
        evidence: vec![
            relative_path(case_root, &reference_path),
            relative_path(case_root, &candidate_path),
        ],
        artifacts: vec![
            artifact_reference(
                relative_path(case_root, &reference_path),
                &reference_normalized,
            ),
            artifact_reference(
                relative_path(case_root, &candidate_path),
                &candidate_normalized,
            ),
        ],
    })
}

fn artifact_reference(path: String, bytes: &[u8]) -> ArtifactReference {
    ArtifactReference {
        path,
        sha256: sha256_hex(bytes),
        bytes: bytes.len() as u64,
    }
}

fn relative_path(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

// ── Tests ────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn environment() -> Environment {
        Environment {
            image: "test".to_owned(),
            operating_system: "test".to_owned(),
            architecture: "test".to_owned(),
            compiler: None,
            cpu: None,
        }
    }

    fn launcher(name: &str) -> Launcher {
        Launcher {
            schema_version: 1,
            name: name.to_owned(),
            program: "{command}".to_owned(),
            arguments: vec![],
            environment_variables: BTreeMap::new(),
            timeout_seconds: None,
            runtime: Runtime::Local,
            environment: environment(),
        }
    }

    // ── Environment evidence tests ─────────────────────────────────────

    fn run_env_evidence_case(env_vars: BTreeMap<String, String>) -> serde_json::Value {
        let mut ref_l = launcher("reference");
        ref_l.environment_variables = env_vars.clone();
        let mut cand_l = launcher("candidate");
        cand_l.environment_variables = env_vars;
        let suite = Suite {
            schema_version: 1,
            suite_id: "env-evidence".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "effective-env".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["env-ok".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Stdout,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        let output = TempDir::new().unwrap();
        let mut runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), ref_l, cand_l).unwrap();
        let outcome = runner.run(&suite, output.path()).unwrap();
        assert_eq!(outcome.failed, 0);
        serde_json::from_slice(&fs::read(output.path().join("effective-env/result.json")).unwrap())
            .unwrap()
    }

    #[test]
    fn result_evidence_records_default_empty_environment_variables() {
        let result = run_env_evidence_case(BTreeMap::new());
        assert_eq!(result["suite_id"], "env-evidence");
        assert_eq!(
            result["effective_environment_variables"],
            serde_json::json!({})
        );
    }

    #[test]
    fn result_evidence_records_effective_posix_environment_variables() {
        let result = run_env_evidence_case(BTreeMap::from([(
            "POSIXLY_CORRECT".to_owned(),
            "1".to_owned(),
        )]));
        assert_eq!(result["suite_id"], "env-evidence");
        assert_eq!(
            result["effective_environment_variables"],
            serde_json::json!({"POSIXLY_CORRECT": "1"})
        );
    }

    // ── Validation tests ───────────────────────────────────────────────

    #[test]
    fn rejects_invalid_environment_variable_keys_and_nul_values() {
        for key in [
            "",
            "9INVALID",
            "INVALID-NAME",
            "INVALID=NAME",
            "NON_ASCII_\u{e9}",
        ] {
            let mut inv = launcher("inv");
            inv.environment_variables
                .insert(key.to_owned(), "v".to_owned());
            assert!(
                validate_launcher(&inv)
                    .unwrap_err()
                    .to_string()
                    .contains("invalid environment variable key")
            );
        }
        let mut inv = launcher("inv");
        inv.environment_variables
            .insert("OK".to_owned(), "before\0after".to_owned());
        assert!(
            validate_launcher(&inv)
                .unwrap_err()
                .to_string()
                .contains("contains a NUL byte")
        );
    }

    #[test]
    fn rejects_duplicate_environment_variable_keys_during_deserialization() {
        let doc = r#"{
            "schema_version":1,"name":"dup","program":"{command}","arguments":[],
            "environment_variables":{"POSIXLY_CORRECT":"1","POSIXLY_CORRECT":"0"},
            "runtime":{"kind":"local"},
            "environment":{"image":"t","operating_system":"t","architecture":"t","compiler":null,"cpu":null}
        }"#;
        assert!(
            serde_json::from_str::<Launcher>(doc)
                .unwrap_err()
                .to_string()
                .contains("duplicate environment variable key: POSIXLY_CORRECT")
        );
    }

    #[test]
    fn rejects_renamed_compatibility_self_comparison() {
        let ref_l = launcher("reference");
        let cand_l = launcher("renamed-reference");
        let suite = Suite {
            schema_version: 1,
            suite_id: "self-test".to_owned(),
            evidence_scope: EvidenceScope::Compatibility,
            cases: vec![Case {
                id: "lcov-version".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["v".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        let output = TempDir::new().unwrap();
        let mut runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), ref_l, cand_l).unwrap();
        let err = runner.run(&suite, output.path()).unwrap_err();
        assert!(
            err.to_string()
                .contains("cannot compare identical runtime identity")
        );
    }

    #[test]
    fn rejects_duplicate_case_ids_before_execution() {
        let ref_l = launcher("ref");
        let cand_l = launcher("cand");
        let suite = Suite {
            schema_version: 1,
            suite_id: "dup".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![
                Case {
                    id: "dup-case".to_owned(),
                    surface: Surface::Cli,
                    command: "printf".to_owned(),
                    arguments: vec!["x".to_owned()],
                    fixture: None,
                    comparisons: vec![ComparisonRequest {
                        dimension: Dimension::Exit,
                        normalizer: NormalizerId::ExactV1,
                    }],
                },
                Case {
                    id: "dup-case".to_owned(),
                    surface: Surface::Cli,
                    command: "printf".to_owned(),
                    arguments: vec!["x".to_owned()],
                    fixture: None,
                    comparisons: vec![ComparisonRequest {
                        dimension: Dimension::Exit,
                        normalizer: NormalizerId::ExactV1,
                    }],
                },
            ],
        };
        assert!(
            validate_suite(&suite, &ref_l, &cand_l)
                .unwrap_err()
                .to_string()
                .contains("duplicate case ID")
        );
    }

    #[test]
    fn rejects_duplicate_comparison_dimensions() {
        let ref_l = launcher("ref");
        let cand_l = launcher("cand");
        let suite = Suite {
            schema_version: 1,
            suite_id: "dup-comp".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "dup-comp".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["x".to_owned()],
                fixture: None,
                comparisons: vec![
                    ComparisonRequest {
                        dimension: Dimension::Exit,
                        normalizer: NormalizerId::ExactV1,
                    },
                    ComparisonRequest {
                        dimension: Dimension::Exit,
                        normalizer: NormalizerId::ExactV1,
                    },
                ],
            }],
        };
        assert!(
            validate_suite(&suite, &ref_l, &cand_l)
                .unwrap_err()
                .to_string()
                .contains("duplicate Exit")
        );
    }

    #[test]
    fn rejects_meaningless_exit_normalizer() {
        let ref_l = launcher("ref");
        let cand_l = launcher("cand");
        let suite = Suite {
            schema_version: 1,
            suite_id: "bad-norm".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "bad-norm".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["x".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::TextCrlfToLfV1,
                }],
            }],
        };
        assert!(
            validate_suite(&suite, &ref_l, &cand_l)
                .unwrap_err()
                .to_string()
                .contains("must use exact-v1")
        );
    }

    #[test]
    fn rejects_different_execution_environments() {
        let ref_l = launcher("ref");
        let mut cand_l = launcher("cand");
        cand_l.environment.architecture = "different".to_owned();
        let suite = Suite {
            schema_version: 1,
            suite_id: "env".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "e".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["x".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        assert!(
            validate_suite(&suite, &ref_l, &cand_l)
                .unwrap_err()
                .to_string()
                .contains("same environment")
        );
    }

    #[test]
    fn rejects_different_launcher_environment_variables() {
        let ref_l = launcher("ref");
        let mut cand_l = launcher("cand");
        cand_l
            .environment_variables
            .insert("POSIXLY_CORRECT".to_owned(), "1".to_owned());
        let suite = Suite {
            schema_version: 1,
            suite_id: "env-var".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "e".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["x".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        assert!(
            validate_suite(&suite, &ref_l, &cand_l)
                .unwrap_err()
                .to_string()
                .contains("same environment variables")
        );
    }

    #[test]
    fn rejects_invalid_suite_id() {
        let suite = Suite {
            schema_version: 1,
            suite_id: "../invalid".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "valid-case".to_owned(),
                surface: Surface::Cli,
                command: "true".to_owned(),
                arguments: Vec::new(),
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        let error = validate_suite(&suite, &launcher("ref"), &launcher("candidate")).unwrap_err();
        assert!(error.to_string().contains("invalid suite identifier"));
    }

    #[test]
    fn local_execution_does_not_inherit_ambient_environment() {
        let suite = Suite {
            schema_version: 1,
            suite_id: "hermetic-env".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "ambient-home".to_owned(),
                surface: Surface::Cli,
                command: "sh".to_owned(),
                arguments: vec!["-c".to_owned(), "printf '%s' \"${HOME-unset}\"".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Stdout,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        let output = TempDir::new().unwrap();
        let mut runner = DifferentialRunner::new(
            std::env::current_dir().unwrap(),
            launcher("ref"),
            launcher("candidate"),
        )
        .unwrap();
        assert_eq!(runner.run(&suite, output.path()).unwrap().failed, 0);
        assert_eq!(
            fs::read(output.path().join("ambient-home/reference/stdout.bin")).unwrap(),
            b"unset"
        );
    }

    // ── Artifact validation tests ──────────────────────────────────────

    fn make_artifact_result(
        case_root: &Path,
        stdout_bytes: &[u8],
        declared_stdout_bytes: u64,
        stdout_hash_override: Option<&str>,
    ) {
        fs::create_dir_all(case_root.join("reference")).unwrap();
        fs::create_dir_all(case_root.join("candidate")).unwrap();
        fs::create_dir_all(case_root.join("normalized")).unwrap();
        fs::write(case_root.join("reference/stdout.bin"), stdout_bytes).unwrap();
        fs::write(case_root.join("candidate/stdout.bin"), stdout_bytes).unwrap();
        fs::write(case_root.join("reference/stderr.bin"), b"").unwrap();
        fs::write(case_root.join("candidate/stderr.bin"), b"").unwrap();
        let tree: Vec<serde_json::Value> = vec![];
        let tree_json = serde_json::to_vec_pretty(&tree).unwrap();
        let tree_hash = sha256_hex(&tree_json);
        fs::write(case_root.join("reference/file-tree.json"), &tree_json).unwrap();
        fs::write(case_root.join("candidate/file-tree.json"), &tree_json).unwrap();
        fs::write(
            case_root.join("normalized/reference-stdout.bin"),
            stdout_bytes,
        )
        .unwrap();
        fs::write(
            case_root.join("normalized/candidate-stdout.bin"),
            stdout_bytes,
        )
        .unwrap();

        let actual_stdout_hash = sha256_hex(stdout_bytes);
        let used_hash = stdout_hash_override.unwrap_or(&actual_stdout_hash);

        let result = serde_json::json!({
            "schema_version":1,"suite_id":"vt","case_id":"vt",
            "evidence_scope":"harness_self_test",
            "upstream_commit":"74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
            "surface":"cli","command":"true","arguments":[],"fixture":null,
            "environment":{"image":"t","operating_system":"t","architecture":"t","compiler":null,"cpu":null},
            "effective_environment_variables":{},
            "implementation_identities":{
                "reference":{"kind":"local_executable","executable_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","container_image_sha256":null},
                "candidate":{"kind":"local_executable","executable_sha256":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","container_image_sha256":null}
            },
            "runs":{
                "reference":{"exit_code":0,"signal":null,
                    "stdout_artifact":"reference/stdout.bin","stderr_artifact":"reference/stderr.bin","file_tree_artifact":"reference/file-tree.json",
                    "stdout_sha256":used_hash,"stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","file_tree_sha256":tree_hash,
                    "stdout_bytes":declared_stdout_bytes,"stderr_bytes":0,"file_tree_bytes":tree_json.len() as u64,
                    "timeout":{"applied_seconds":20,"expired":false,"termination_signal_sent":null,"escalation_signal_sent":null},
                    "cleanup":{"direct_child_reaped":true,"process_group_empty":true,"container_absent":null},
                    "metrics":{"wall_seconds":0.0,"user_cpu_seconds":null,"system_cpu_seconds":null,"peak_rss_bytes":null,"output_bytes":0,"output_files":0}},
                "candidate":{"exit_code":0,"signal":null,
                    "stdout_artifact":"candidate/stdout.bin","stderr_artifact":"candidate/stderr.bin","file_tree_artifact":"candidate/file-tree.json",
                    "stdout_sha256":used_hash,"stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","file_tree_sha256":tree_hash,
                    "stdout_bytes":declared_stdout_bytes,"stderr_bytes":0,"file_tree_bytes":tree_json.len() as u64,
                    "timeout":{"applied_seconds":20,"expired":false,"termination_signal_sent":null,"escalation_signal_sent":null},
                    "cleanup":{"direct_child_reaped":true,"process_group_empty":true,"container_absent":null},
                    "metrics":{"wall_seconds":0.0,"user_cpu_seconds":null,"system_cpu_seconds":null,"peak_rss_bytes":null,"output_bytes":0,"output_files":0}}
            },
            "comparisons":[{"dimension":"stdout","status":"pass","normalizer":"exact-v1","evidence":["a","b"],
                "artifacts":[
                    {"path":"normalized/reference-stdout.bin","sha256":actual_stdout_hash,"bytes":stdout_bytes.len() as u64},
                    {"path":"normalized/candidate-stdout.bin","sha256":actual_stdout_hash,"bytes":stdout_bytes.len() as u64}
                ],"details":null}],
            "overall_status":"pass"
        });
        evidence::write_json(&case_root.join("result.json"), &result).unwrap();
    }

    #[test]
    fn validates_artifact_hashes_rejects_mutation() {
        let dir = TempDir::new().unwrap();
        make_artifact_result(dir.path(), b"original", 8, None);
        let bad_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";
        make_artifact_result(dir.path(), b"original", 8, Some(bad_hash));
        assert!(
            validate_result_artifacts(dir.path())
                .unwrap_err()
                .to_string()
                .contains("hash mismatch")
        );
    }

    #[test]
    fn validates_artifact_sizes_reject_truncation() {
        let dir = TempDir::new().unwrap();
        make_artifact_result(dir.path(), b"ten bytes!", 999, None);
        assert!(
            validate_result_artifacts(dir.path())
                .unwrap_err()
                .to_string()
                .contains("size mismatch")
        );
    }

    #[test]
    fn rejects_artifact_path_outside_fixed_role_location() {
        let dir = TempDir::new().unwrap();
        fs::create_dir_all(dir.path().join("reference")).unwrap();
        fs::create_dir_all(dir.path().join("candidate")).unwrap();
        fs::write(dir.path().join("reference/stdout.bin"), b"ok").unwrap();
        fs::write(dir.path().join("candidate/stdout.bin"), b"ok").unwrap();
        fs::write(dir.path().join("reference/stderr.bin"), b"").unwrap();
        fs::write(dir.path().join("candidate/stderr.bin"), b"").unwrap();
        let tree: Vec<serde_json::Value> = vec![];
        let tj = serde_json::to_vec_pretty(&tree).unwrap();
        let th = sha256_hex(&tj);
        fs::write(dir.path().join("reference/file-tree.json"), &tj).unwrap();
        fs::write(dir.path().join("candidate/file-tree.json"), &tj).unwrap();
        let h = sha256_hex(b"ok");
        let result = serde_json::json!({
            "schema_version":1,"suite_id":"s","case_id":"c",
            "evidence_scope":"harness_self_test",
            "upstream_commit":"74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
            "surface":"cli","command":"true","arguments":[],"fixture":null,
            "environment":{"image":"t","operating_system":"t","architecture":"t","compiler":null,"cpu":null},
            "effective_environment_variables":{},
            "implementation_identities":{
                "reference":{"kind":"local_executable","executable_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","container_image_sha256":null},
                "candidate":{"kind":"local_executable","executable_sha256":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","container_image_sha256":null}
            },
            "runs":{
                "reference":{"exit_code":0,"signal":null,
                    "stdout_artifact":"../etc/passwd","stderr_artifact":"reference/stderr.bin","file_tree_artifact":"reference/file-tree.json",
                    "stdout_sha256":h,"stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","file_tree_sha256":th,
                    "stdout_bytes":2,"stderr_bytes":0,"file_tree_bytes":tj.len() as u64,
                    "timeout":null,"cleanup":null,
                    "metrics":{"wall_seconds":0.0,"user_cpu_seconds":null,"system_cpu_seconds":null,"peak_rss_bytes":null}},
                "candidate":{"exit_code":0,"signal":null,
                    "stdout_artifact":"candidate/stdout.bin","stderr_artifact":"candidate/stderr.bin","file_tree_artifact":"candidate/file-tree.json",
                    "stdout_sha256":h,"stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","file_tree_sha256":th,
                    "stdout_bytes":2,"stderr_bytes":0,"file_tree_bytes":tj.len() as u64,
                    "timeout":null,"cleanup":null,
                    "metrics":{"wall_seconds":0.0,"user_cpu_seconds":null,"system_cpu_seconds":null,"peak_rss_bytes":null}}
            },
            "comparisons":[{"dimension":"stdout","status":"pass","normalizer":"exact-v1","evidence":["a","b"],"details":null}],
            "overall_status":"pass"
        });
        evidence::write_json(&dir.path().join("result.json"), &result).unwrap();
        assert!(
            validate_result_artifacts(dir.path())
                .unwrap_err()
                .to_string()
                .contains("must be reference/stdout.bin")
        );
    }

    #[test]
    fn rejects_mutated_normalized_artifact() {
        let dir = TempDir::new().unwrap();
        make_artifact_result(dir.path(), b"original", 8, None);
        fs::write(
            dir.path().join("normalized/reference-stdout.bin"),
            b"mutated",
        )
        .unwrap();
        assert!(
            validate_result_artifacts(dir.path())
                .unwrap_err()
                .to_string()
                .contains("normalized/reference-stdout.bin hash mismatch")
        );
    }

    #[cfg(unix)]
    #[test]
    fn rejects_intermediate_and_final_artifact_symlinks() {
        let intermediate = TempDir::new().unwrap();
        make_artifact_result(intermediate.path(), b"original", 8, None);
        fs::rename(
            intermediate.path().join("normalized"),
            intermediate.path().join("normalized-real"),
        )
        .unwrap();
        std::os::unix::fs::symlink("normalized-real", intermediate.path().join("normalized"))
            .unwrap();
        assert!(
            validate_result_artifacts(intermediate.path())
                .unwrap_err()
                .to_string()
                .contains("contains a symlink")
        );

        let final_link = TempDir::new().unwrap();
        make_artifact_result(final_link.path(), b"original", 8, None);
        fs::remove_file(final_link.path().join("reference/stdout.bin")).unwrap();
        std::os::unix::fs::symlink(
            "../candidate/stdout.bin",
            final_link.path().join("reference/stdout.bin"),
        )
        .unwrap();
        assert!(
            validate_result_artifacts(final_link.path())
                .unwrap_err()
                .to_string()
                .contains("contains a symlink")
        );
    }

    #[cfg(unix)]
    #[test]
    fn refuses_preexisting_summary_symlink() {
        let output = TempDir::new().unwrap();
        let outside = output.path().join("outside.json");
        fs::write(&outside, b"unchanged").unwrap();
        std::os::unix::fs::symlink(&outside, output.path().join("summary.json")).unwrap();
        let suite = Suite {
            schema_version: 1,
            suite_id: "summary-link".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "summary-case".to_owned(),
                surface: Surface::Cli,
                command: "true".to_owned(),
                arguments: Vec::new(),
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };
        let mut runner = DifferentialRunner::new(
            std::env::current_dir().unwrap(),
            launcher("ref"),
            launcher("candidate"),
        )
        .unwrap();
        let error = runner.run(&suite, output.path()).unwrap_err();
        assert!(error.to_string().contains("summary output already exists"));
        assert_eq!(fs::read(outside).unwrap(), b"unchanged");
    }

    // ── Timeout tests ──────────────────────────────────────────────────

    #[test]
    fn timeout_with_child_descendant_is_reaped() {
        let mut reference = launcher("reference");
        reference.timeout_seconds = Some(2);
        let mut candidate = launcher("candidate");
        candidate.timeout_seconds = Some(2);

        let suite = Suite {
            schema_version: 1,
            suite_id: "timeout-test".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "timeout-cleanup".to_owned(),
                surface: Surface::Cli,
                command: "sh".to_owned(),
                arguments: vec!["-c".to_owned(), "(sleep 8 &); sleep 10".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };

        let output = TempDir::new().unwrap();
        let mut runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), reference, candidate)
                .unwrap();
        let started = std::time::Instant::now();
        let outcome = runner.run(&suite, output.path()).unwrap();
        assert!(started.elapsed() < std::time::Duration::from_secs(7));
        assert_eq!(outcome.failed, 1);

        let result: serde_json::Value = serde_json::from_slice(
            &fs::read(output.path().join("timeout-cleanup/result.json")).unwrap(),
        )
        .unwrap();

        let ref_to = &result["runs"]["reference"]["timeout"];
        assert!(ref_to["expired"].as_bool().unwrap());
        assert_eq!(ref_to["applied_seconds"].as_u64().unwrap(), 2);

        let ref_cl = &result["runs"]["reference"]["cleanup"];
        assert!(ref_cl["direct_child_reaped"].as_bool().unwrap());
        assert!(ref_cl["process_group_empty"].as_bool().unwrap());
        assert_eq!(result["overall_status"], "fail");
    }

    #[test]
    fn timeout_results_include_artifact_hashes() {
        let mut reference = launcher("reference");
        reference.timeout_seconds = Some(5);
        let mut candidate = launcher("candidate");
        candidate.timeout_seconds = Some(5);

        let suite = Suite {
            schema_version: 1,
            suite_id: "ta".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "th".to_owned(),
                surface: Surface::Cli,
                command: "printf".to_owned(),
                arguments: vec!["hello".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Stdout,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };

        let output = TempDir::new().unwrap();
        let mut runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), reference, candidate)
                .unwrap();
        assert_eq!(runner.run(&suite, output.path()).unwrap().failed, 0);

        let result: serde_json::Value =
            serde_json::from_slice(&fs::read(output.path().join("th/result.json")).unwrap())
                .unwrap();
        let ref_run = &result["runs"]["reference"];
        assert_eq!(ref_run["stdout_sha256"].as_str().unwrap().len(), 64);
        assert_eq!(ref_run["stdout_bytes"].as_u64().unwrap(), 5);
        assert!(!ref_run["timeout"]["expired"].as_bool().unwrap());
    }

    #[test]
    fn timeout_large_output_no_deadlock() {
        let mut reference = launcher("reference");
        reference.timeout_seconds = Some(10);
        let mut candidate = launcher("candidate");
        candidate.timeout_seconds = Some(10);

        let suite = Suite {
            schema_version: 1,
            suite_id: "large".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "large-out".to_owned(),
                surface: Surface::Cli,
                command: "sh".to_owned(),
                arguments: vec![
                    "-c".to_owned(),
                    "head -c 2000000 /dev/zero | tr '\\0' 'x'; echo DONE".to_owned(),
                ],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Stdout,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };

        let output = TempDir::new().unwrap();
        let mut runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), reference, candidate)
                .unwrap();
        assert_eq!(runner.run(&suite, output.path()).unwrap().failed, 0);

        let stdout = fs::read(output.path().join("large-out/reference/stdout.bin")).unwrap();
        assert!(stdout.len() > 1_000_000);
        assert!(stdout.ends_with(b"DONE\n"));
    }

    // ── Launcher timeout validation ────────────────────────────────────

    #[test]
    fn rejects_zero_timeout() {
        let mut inv = launcher("z");
        inv.timeout_seconds = Some(0);
        assert!(
            validate_launcher(&inv)
                .unwrap_err()
                .to_string()
                .contains("timeout_seconds must be between 1 and 3600")
        );
    }

    #[test]
    fn accepts_reasonable_timeout() {
        let mut v = launcher("v");
        v.timeout_seconds = Some(30);
        assert!(validate_launcher(&v).is_ok());
    }

    #[test]
    fn timeout_not_required_for_valid_launcher() {
        assert!(validate_launcher(&launcher("no-timeout")).is_ok());
    }

    // ── Docker E2E test ────────────────────────────────────────────────

    /// This test requires the Oracle Docker image and Docker daemon.
    /// When either is unavailable, the test fails rather than skipping
    /// silently — M0 verification demands that the environment switch
    /// surfaces the absence.
    ///
    /// Set `FERRICOV_SKIP_DOCKER_E2E=1` to skip explicitly in ordinary CI
    /// jobs that do not build the Oracle image.
    #[test]
    fn docker_clean_environment_and_posixly_correct_change_behavior() {
        if std::env::var("FERRICOV_SKIP_DOCKER_E2E").is_ok() {
            eprintln!("FERRICOV_SKIP_DOCKER_E2E set — skipping Docker E2E");
            return;
        }

        let image = "ferricov/lcov-oracle:v2.5";
        let mut image_cache = BTreeMap::new();
        let resolved_image =
            process::resolve_image_id(image, &mut image_cache).unwrap_or_else(|error| {
                panic!(
                    "Docker E2E test requires image {image}; build it from compat/upstream; error={error}"
                )
            });
        let clean_environment = BTreeMap::from([
            ("HOME".to_owned(), "/work".to_owned()),
            ("LANG".to_owned(), "C".to_owned()),
            ("LC_ALL".to_owned(), "C".to_owned()),
            (
                "PATH".to_owned(),
                "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin".to_owned(),
            ),
            ("TZ".to_owned(), "UTC".to_owned()),
        ]);

        let environment_launcher = Launcher {
            schema_version: 1,
            name: "docker-clean-environment".to_owned(),
            program: "{command}".to_owned(),
            arguments: Vec::new(),
            environment_variables: clean_environment.clone(),
            timeout_seconds: Some(30),
            runtime: Runtime::DockerImage {
                image: image.to_owned(),
            },
            environment: Environment {
                image: image.to_owned(),
                operating_system: "Debian 12".to_owned(),
                architecture: "x86_64".to_owned(),
                compiler: Some("GCC 12.2.0".to_owned()),
                cpu: None,
            },
        };
        let environment_case = Case {
            id: "docker-clean-environment".to_owned(),
            surface: Surface::Cli,
            command: "env".to_owned(),
            arguments: Vec::new(),
            fixture: None,
            comparisons: vec![ComparisonRequest {
                dimension: Dimension::Stdout,
                normalizer: NormalizerId::ExactV1,
            }],
        };
        let prepared = process::prepare(
            &std::env::current_dir().unwrap(),
            &environment_launcher,
            &environment_case,
            &mut image_cache,
        )
        .unwrap();
        let captured =
            process::capture(prepared, &environment_launcher, &environment_case).unwrap();
        assert_eq!(exit_parts(&captured.captured.exit_status), (Some(0), None));
        assert_eq!(
            captured.captured.stdout,
            b"HOME=/work
LANG=C
LC_ALL=C
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=UTC
"
        );
        assert!(captured.captured.stderr.is_empty());
        assert!(!captured.timeout.expired);
        assert_eq!(captured.cleanup.container_absent, Some(true));

        let run_parser_case =
            |suite_id: &str, case_id: &str, environment_variables: BTreeMap<String, String>| {
                let make_launcher = |name: &str| Launcher {
                    schema_version: 1,
                    name: name.to_owned(),
                    program: "{command}".to_owned(),
                    arguments: Vec::new(),
                    environment_variables: environment_variables.clone(),
                    timeout_seconds: Some(30),
                    runtime: Runtime::DockerImage {
                        image: image.to_owned(),
                    },
                    environment: Environment {
                        image: image.to_owned(),
                        operating_system: "Debian 12".to_owned(),
                        architecture: "x86_64".to_owned(),
                        compiler: Some("GCC 12.2.0".to_owned()),
                        cpu: None,
                    },
                };
                let suite = Suite {
                    schema_version: 1,
                    suite_id: suite_id.to_owned(),
                    evidence_scope: EvidenceScope::HarnessSelfTest,
                    cases: vec![Case {
                        id: case_id.to_owned(),
                        surface: Surface::Cli,
                        command: "lcov".to_owned(),
                        arguments: vec!["--hel".to_owned()],
                        fixture: None,
                        comparisons: vec![
                            ComparisonRequest {
                                dimension: Dimension::Exit,
                                normalizer: NormalizerId::ExactV1,
                            },
                            ComparisonRequest {
                                dimension: Dimension::Stdout,
                                normalizer: NormalizerId::ExactV1,
                            },
                            ComparisonRequest {
                                dimension: Dimension::Stderr,
                                normalizer: NormalizerId::ExactV1,
                            },
                            ComparisonRequest {
                                dimension: Dimension::Filesystem,
                                normalizer: NormalizerId::ExactV1,
                            },
                        ],
                    }],
                };
                let output = TempDir::new().unwrap();
                let mut runner = DifferentialRunner::new(
                    std::env::current_dir().unwrap(),
                    make_launcher("docker-reference"),
                    make_launcher("docker-candidate"),
                )
                .unwrap();
                let outcome = runner.run(&suite, output.path()).unwrap();
                assert_eq!(outcome.failed, 0);
                let case_root = output.path().join(case_id);
                let result: serde_json::Value =
                    serde_json::from_slice(&fs::read(case_root.join("result.json")).unwrap())
                        .unwrap();
                validate_result_artifacts(&case_root).unwrap();
                let stdout = fs::read(case_root.join("reference/stdout.bin")).unwrap();
                let stderr = fs::read(case_root.join("reference/stderr.bin")).unwrap();
                (output, result, stdout, stderr)
            };

        let (_default_output, default, default_stdout, default_stderr) = run_parser_case(
            "docker-parser-default",
            "lcov-help-prefix",
            clean_environment.clone(),
        );
        let mut posix_environment = clean_environment.clone();
        posix_environment.insert("POSIXLY_CORRECT".to_owned(), "1".to_owned());
        let (_posix_output, posix, posix_stdout, posix_stderr) = run_parser_case(
            "docker-parser-posix",
            "lcov-help-prefix-posix",
            posix_environment.clone(),
        );

        assert_eq!(default["runs"]["reference"]["exit_code"], 0);
        assert!(default_stdout.starts_with(b"Usage: lcov [OPTIONS]"));
        assert!(default_stderr.is_empty());
        assert_eq!(
            default["effective_environment_variables"],
            serde_json::to_value(&clean_environment).unwrap()
        );

        assert_eq!(posix["runs"]["reference"]["exit_code"], 1);
        assert!(posix_stdout.is_empty());
        assert!(posix_stderr.starts_with(b"lcov: WARNING: Unknown option: hel"));
        assert_eq!(
            posix["effective_environment_variables"],
            serde_json::to_value(&posix_environment).unwrap()
        );

        for result in [&default, &posix] {
            assert_eq!(
                result["implementation_identities"]["reference"],
                result["implementation_identities"]["candidate"]
            );
            assert_eq!(result["runs"]["reference"]["timeout"]["expired"], false);
            assert_eq!(
                result["runs"]["reference"]["cleanup"]["container_absent"],
                true
            );
        }
        assert_eq!(
            default["implementation_identities"]["reference"],
            posix["implementation_identities"]["reference"]
        );
        assert_eq!(
            default["implementation_identities"]["reference"]["container_image_sha256"],
            resolved_image
        );
    }
}
