use crate::UPSTREAM_COMMIT;
use crate::normalizer::{NormalizerId, normalize};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus};
use std::time::Instant;
use tempfile::TempDir;

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
    #[serde(default)]
    pub environment_variables: BTreeMap<String, String>,
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

#[derive(Debug, Serialize)]
struct DifferentialResult<'a> {
    schema_version: u32,
    case_id: &'a str,
    evidence_scope: EvidenceScope,
    upstream_commit: &'static str,
    surface: Surface,
    command: &'a str,
    arguments: &'a [String],
    fixture: Option<&'a str>,
    environment: &'a Environment,
    implementation_identities: ImplementationIdentities,
    runs: Runs,
    comparisons: Vec<ComparisonResult>,
    overall_status: Status,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ImplementationIdentity {
    kind: IdentityKind,
    executable_sha256: String,
    container_image_sha256: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum IdentityKind {
    LocalExecutable,
    DockerImage,
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
struct RunResult {
    exit_code: Option<i32>,
    signal: Option<i32>,
    stdout_artifact: String,
    stderr_artifact: String,
    file_tree_artifact: String,
    metrics: Metrics,
}

#[derive(Debug, Serialize)]
struct Metrics {
    wall_seconds: f64,
    user_cpu_seconds: Option<f64>,
    system_cpu_seconds: Option<f64>,
    peak_rss_bytes: Option<u64>,
    output_bytes: u64,
    output_files: u64,
}

#[derive(Debug, Serialize)]
struct ComparisonResult {
    dimension: Dimension,
    status: Status,
    normalizer: String,
    evidence: Vec<String>,
    details: Option<String>,
}

struct ComparedArtifacts {
    matches: bool,
    details: Option<String>,
    evidence: Vec<String>,
}

#[derive(Debug, Serialize, Eq, PartialEq)]
struct FileEntry {
    path: String,
    path_bytes_hex: String,
    kind: FileKind,
    bytes: u64,
    sha256: Option<String>,
    mode: Option<u32>,
    uid: Option<u32>,
    gid: Option<u32>,
    hardlink_count: Option<u64>,
    hardlink_group: Option<String>,
}

struct SnapshotEntry {
    file: FileEntry,
    hardlink_identity: Option<(u64, u64)>,
}

struct EntryMetadata {
    mode: Option<u32>,
    uid: Option<u32>,
    gid: Option<u32>,
    hardlink_count: Option<u64>,
    hardlink_identity: Option<(u64, u64)>,
}

#[derive(Debug, Serialize, Eq, PartialEq)]
#[serde(rename_all = "snake_case")]
enum FileKind {
    File,
    Directory,
    Symlink,
}

struct CapturedRun {
    exit_status: ExitStatus,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    file_tree: Vec<FileEntry>,
    wall_seconds: f64,
}

pub struct DifferentialRunner {
    repository_root: PathBuf,
    reference: Launcher,
    candidate: Launcher,
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
        })
    }

    pub fn run(&self, suite: &Suite, output_root: &Path) -> Result<SuiteOutcome, Box<dyn Error>> {
        validate_suite(suite, &self.reference, &self.candidate)?;
        fs::create_dir_all(output_root)?;

        let mut summary = BTreeMap::new();
        for case in &suite.cases {
            let status = self.run_case(suite, case, output_root)?;
            let previous = summary.insert(case.id.clone(), status);
            debug_assert!(
                previous.is_none(),
                "suite validation enforces unique case IDs"
            );
        }
        write_json(&output_root.join("summary.json"), &summary)?;
        Ok(SuiteOutcome {
            passed: summary
                .values()
                .filter(|status| **status == Status::Pass)
                .count(),
            failed: summary
                .values()
                .filter(|status| **status == Status::Fail)
                .count(),
        })
    }

    fn run_case(
        &self,
        suite: &Suite,
        case: &Case,
        output_root: &Path,
    ) -> Result<Status, Box<dyn Error>> {
        let reference_identity = self.resolve_identity(&self.reference, case)?;
        let candidate_identity = self.resolve_identity(&self.candidate, case)?;
        if suite.evidence_scope == EvidenceScope::Compatibility
            && reference_identity.executable_sha256 == candidate_identity.executable_sha256
        {
            return Err(format!(
                "compatibility evidence cannot compare identical runtime identity {}",
                reference_identity.executable_sha256
            )
            .into());
        }

        let case_root = output_root.join(&case.id);
        if case_root.exists() {
            fs::remove_dir_all(&case_root)?;
        }
        fs::create_dir_all(&case_root)?;

        let reference = self.capture(&self.reference, case)?;
        let candidate = self.capture(&self.candidate, case)?;
        let reference_result = persist_run(&case_root, "reference", &reference)?;
        let candidate_result = persist_run(&case_root, "candidate", &candidate)?;

        let comparisons = compare_runs(case, &case_root, &reference, &candidate)?;
        let overall_status = if comparisons
            .iter()
            .all(|comparison| comparison.status == Status::Pass)
        {
            Status::Pass
        } else {
            Status::Fail
        };

        let result = DifferentialResult {
            schema_version: 1,
            case_id: &case.id,
            evidence_scope: suite.evidence_scope,
            upstream_commit: UPSTREAM_COMMIT,
            surface: case.surface,
            command: &case.command,
            arguments: &case.arguments,
            fixture: case.fixture.as_deref(),
            environment: &self.reference.environment,
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
        write_json(&case_root.join("result.json"), &result)?;
        Ok(overall_status)
    }

    fn capture(&self, launcher: &Launcher, case: &Case) -> Result<CapturedRun, Box<dyn Error>> {
        let working_directory = TempDir::new()?;
        if let Some(fixture) = &case.fixture {
            let fixture_root = self.repository_root.join(fixture);
            if !fixture_root.is_dir() {
                return Err(format!(
                    "case {} fixture is not a directory: {}",
                    case.id,
                    fixture_root.display()
                )
                .into());
            }
            copy_directory_contents(&fixture_root, working_directory.path())?;
        }
        let program = substitute(&launcher.program, case);
        let arguments = launcher
            .arguments
            .iter()
            .map(|argument| substitute(argument, case))
            .collect::<Vec<_>>();

        let started = Instant::now();
        let output = match &launcher.runtime {
            Runtime::Local => Command::new(resolve_program(&self.repository_root, &program))
                .args(arguments)
                .args(&case.arguments)
                .envs(&launcher.environment_variables)
                .current_dir(working_directory.path())
                .output()?,
            Runtime::DockerImage { image } => {
                let mut command = Command::new("docker");
                command.args(["run", "--rm", "--network", "none"]);
                add_docker_user(&mut command);
                command
                    .arg("--volume")
                    .arg(format!("{}:/work", working_directory.path().display()))
                    .args(["--workdir", "/work"])
                    .args(["--entrypoint", &program])
                    .arg(image)
                    .args(arguments)
                    .args(&case.arguments)
                    .envs(&launcher.environment_variables)
                    .output()?
            }
        };
        let wall_seconds = started.elapsed().as_secs_f64();
        let file_tree = snapshot_tree(working_directory.path())?;

        Ok(CapturedRun {
            exit_status: output.status,
            stdout: output.stdout,
            stderr: output.stderr,
            file_tree,
            wall_seconds,
        })
    }

    fn resolve_identity(
        &self,
        launcher: &Launcher,
        case: &Case,
    ) -> Result<ImplementationIdentity, Box<dyn Error>> {
        match &launcher.runtime {
            Runtime::Local => {
                let program = substitute(&launcher.program, case);
                let executable = resolve_executable(&self.repository_root, &program)?;
                let content = fs::read(executable)?;
                Ok(ImplementationIdentity {
                    kind: IdentityKind::LocalExecutable,
                    executable_sha256: format!("sha256:{:x}", Sha256::digest(content)),
                    container_image_sha256: None,
                })
            }
            Runtime::DockerImage { image } => {
                if launcher.environment.image != *image {
                    return Err(format!(
                        "launcher {} runtime image must match its declared environment image",
                        launcher.name
                    )
                    .into());
                }
                let output = Command::new("docker")
                    .args(["image", "inspect", "--format", "{{.Id}}", image])
                    .output()?;
                if !output.status.success() {
                    return Err(format!("failed to inspect Docker image {image}").into());
                }
                let image_identity = String::from_utf8(output.stdout)?.trim().to_owned();
                validate_sha256_identity(&image_identity)?;
                let program = substitute(&launcher.program, case);
                let output = Command::new("docker")
                    .args(["run", "--rm", "--network", "none", "--entrypoint", "sh"])
                    .arg(image)
                    .args([
                        "-c",
                        "p=$(command -v -- \"$1\") && test -n \"$p\" && sha256sum \"$p\"",
                        "sh",
                        &program,
                    ])
                    .output()?;
                if !output.status.success() {
                    return Err(format!(
                        "failed to identify executable {program} in Docker image {image}"
                    )
                    .into());
                }
                let executable_hash = String::from_utf8(output.stdout)?
                    .split_ascii_whitespace()
                    .next()
                    .ok_or("Docker executable identity is empty")?
                    .to_owned();
                let executable_identity = format!("sha256:{executable_hash}");
                validate_sha256_identity(&executable_identity)?;
                Ok(ImplementationIdentity {
                    kind: IdentityKind::DockerImage,
                    executable_sha256: executable_identity,
                    container_image_sha256: Some(image_identity),
                })
            }
        }
    }
}

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
        .filter(|argument| argument.contains("{command}"))
        .count();
    if command_placeholders != 1 {
        return Err(format!(
            "launcher {} must contain exactly one {{command}} placeholder",
            launcher.name
        )
        .into());
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

fn validate_suite(
    suite: &Suite,
    reference: &Launcher,
    candidate: &Launcher,
) -> Result<(), Box<dyn Error>> {
    if suite.schema_version != 1 {
        return Err(format!("unsupported suite schema version: {}", suite.schema_version).into());
    }
    if suite.cases.is_empty() {
        return Err("suite must contain at least one case".into());
    }
    if reference.environment != candidate.environment {
        return Err("reference and candidate launchers must declare the same environment".into());
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
            .is_some_and(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
        && value.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'.' | b'_' | b'-')
        });
    if valid {
        Ok(())
    } else {
        Err(format!("invalid {kind} identifier: {value}").into())
    }
}

fn resolve_program(repository_root: &Path, program: &str) -> OsString {
    let path = Path::new(program);
    if path.components().count() > 1 && path.is_relative() {
        repository_root.join(path).into_os_string()
    } else {
        program.into()
    }
}

fn resolve_executable(repository_root: &Path, program: &str) -> Result<PathBuf, Box<dyn Error>> {
    let path = Path::new(program);
    if path.components().count() > 1 {
        let resolved = if path.is_relative() {
            repository_root.join(path)
        } else {
            path.to_owned()
        };
        return Ok(fs::canonicalize(resolved)?);
    }

    let search_path = std::env::var_os("PATH").ok_or("PATH is not defined")?;
    for directory in std::env::split_paths(&search_path) {
        let candidate = directory.join(program);
        if candidate.is_file() {
            return Ok(fs::canonicalize(candidate)?);
        }
    }
    Err(format!("executable not found in PATH: {program}").into())
}

fn validate_sha256_identity(identity: &str) -> Result<(), Box<dyn Error>> {
    let Some(hex) = identity.strip_prefix("sha256:") else {
        return Err(format!("runtime identity is not SHA-256: {identity}").into());
    };
    if hex.len() != 64 || !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!("runtime identity is not SHA-256: {identity}").into());
    }
    Ok(())
}

#[cfg(unix)]
fn add_docker_user(command: &mut Command) {
    use std::os::unix::fs::MetadataExt;
    if let Ok(metadata) = fs::metadata(".") {
        command.args(["--user", &format!("{}:{}", metadata.uid(), metadata.gid())]);
    }
}

#[cfg(not(unix))]
fn add_docker_user(_command: &mut Command) {}

fn substitute(template: &str, case: &Case) -> String {
    template
        .replace("{command}", &case.command)
        .replace("{fixture}", ".")
}

fn copy_directory_contents(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        copy_entry(&entry.path(), &destination.join(entry.file_name()))?;
    }
    Ok(())
}

fn copy_entry(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    let metadata = fs::symlink_metadata(source)?;
    let file_type = metadata.file_type();
    if file_type.is_file() {
        fs::copy(source, destination)?;
    } else if file_type.is_dir() {
        fs::create_dir(destination)?;
        copy_directory_contents(source, destination)?;
    } else if file_type.is_symlink() {
        copy_symlink(source, destination)?;
    } else {
        return Err(format!("unsupported fixture entry: {}", source.display()).into());
    }
    Ok(())
}

#[cfg(unix)]
fn copy_symlink(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    std::os::unix::fs::symlink(fs::read_link(source)?, destination)?;
    Ok(())
}

#[cfg(windows)]
fn copy_symlink(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    let target = fs::read_link(source)?;
    if source.is_dir() {
        std::os::windows::fs::symlink_dir(target, destination)?;
    } else {
        std::os::windows::fs::symlink_file(target, destination)?;
    }
    Ok(())
}

fn persist_run(
    case_root: &Path,
    role: &str,
    captured: &CapturedRun,
) -> Result<RunResult, Box<dyn Error>> {
    let role_root = case_root.join(role);
    fs::create_dir_all(&role_root)?;
    fs::write(role_root.join("stdout.bin"), &captured.stdout)?;
    fs::write(role_root.join("stderr.bin"), &captured.stderr)?;
    write_json(&role_root.join("file-tree.json"), &captured.file_tree)?;

    let (exit_code, signal) = exit_parts(&captured.exit_status);
    let output_bytes = captured
        .file_tree
        .iter()
        .filter(|entry| entry.kind == FileKind::File)
        .map(|entry| entry.bytes)
        .sum();
    let output_files = captured
        .file_tree
        .iter()
        .filter(|entry| entry.kind == FileKind::File)
        .count() as u64;

    Ok(RunResult {
        exit_code,
        signal,
        stdout_artifact: format!("{role}/stdout.bin"),
        stderr_artifact: format!("{role}/stderr.bin"),
        file_tree_artifact: format!("{role}/file-tree.json"),
        metrics: Metrics {
            wall_seconds: captured.wall_seconds,
            user_cpu_seconds: None,
            system_cpu_seconds: None,
            peak_rss_bytes: None,
            output_bytes,
            output_files,
        },
    })
}

fn compare_runs(
    case: &Case,
    case_root: &Path,
    reference: &CapturedRun,
    candidate: &CapturedRun,
) -> Result<Vec<ComparisonResult>, Box<dyn Error>> {
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
    fs::create_dir_all(&normalized_root)?;
    let reference_path = normalized_root.join(format!("reference-{name}.bin"));
    let candidate_path = normalized_root.join(format!("candidate-{name}.bin"));
    fs::write(&reference_path, &reference_normalized)?;
    fs::write(&candidate_path, &candidate_normalized)?;
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
    })
}

fn snapshot_tree(root: &Path) -> Result<Vec<FileEntry>, Box<dyn Error>> {
    let mut snapshots = Vec::new();
    snapshot_directory(root, root, &mut snapshots)?;
    snapshots.sort_by(|left, right| left.file.path_bytes_hex.cmp(&right.file.path_bytes_hex));

    let mut hardlink_groups = BTreeMap::new();
    for snapshot in &snapshots {
        if let Some(identity) = snapshot.hardlink_identity {
            hardlink_groups
                .entry(identity)
                .or_insert_with(|| snapshot.file.path_bytes_hex.clone());
        }
    }
    Ok(snapshots
        .into_iter()
        .map(|mut snapshot| {
            snapshot.file.hardlink_group = snapshot
                .hardlink_identity
                .and_then(|identity| hardlink_groups.get(&identity).cloned());
            snapshot.file
        })
        .collect())
}

fn snapshot_directory(
    root: &Path,
    directory: &Path,
    entries: &mut Vec<SnapshotEntry>,
) -> Result<(), Box<dyn Error>> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)?;
        let file_type = metadata.file_type();
        let (kind, bytes, sha256) = if file_type.is_file() {
            let content = fs::read(&path)?;
            (
                FileKind::File,
                content.len() as u64,
                Some(format!("{:x}", Sha256::digest(&content))),
            )
        } else if file_type.is_dir() {
            snapshot_directory(root, &path, entries)?;
            (FileKind::Directory, 0, None)
        } else if file_type.is_symlink() {
            let target = fs::read_link(&path)?;
            let encoded = os_bytes(target.as_os_str());
            (
                FileKind::Symlink,
                encoded.len() as u64,
                Some(format!("{:x}", Sha256::digest(&encoded))),
            )
        } else {
            return Err(format!("unsupported filesystem entry: {}", path.display()).into());
        };
        let relative = path.strip_prefix(root).unwrap_or(&path);
        let entry_metadata = file_metadata(&metadata);
        entries.push(SnapshotEntry {
            file: FileEntry {
                path: relative_path(root, &path),
                path_bytes_hex: hex_bytes(&os_bytes(relative.as_os_str())),
                kind,
                bytes,
                sha256,
                mode: entry_metadata.mode,
                uid: entry_metadata.uid,
                gid: entry_metadata.gid,
                hardlink_count: entry_metadata.hardlink_count,
                hardlink_group: None,
            },
            hardlink_identity: entry_metadata.hardlink_identity,
        });
    }
    Ok(())
}

#[cfg(unix)]
fn file_metadata(metadata: &fs::Metadata) -> EntryMetadata {
    use std::os::unix::fs::MetadataExt;
    let hardlink_count = metadata.nlink();
    EntryMetadata {
        mode: Some(metadata.mode() & 0o7777),
        uid: Some(metadata.uid()),
        gid: Some(metadata.gid()),
        hardlink_count: Some(hardlink_count),
        hardlink_identity: (metadata.is_file() && hardlink_count > 1)
            .then(|| (metadata.dev(), metadata.ino())),
    }
}

#[cfg(not(unix))]
fn file_metadata(_metadata: &fs::Metadata) -> EntryMetadata {
    EntryMetadata {
        mode: None,
        uid: None,
        gid: None,
        hardlink_count: None,
        hardlink_identity: None,
    }
}

#[cfg(unix)]
fn os_bytes(value: &OsStr) -> Vec<u8> {
    use std::os::unix::ffi::OsStrExt;
    value.as_bytes().to_vec()
}

#[cfg(not(unix))]
fn os_bytes(value: &OsStr) -> Vec<u8> {
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        return value
            .encode_wide()
            .flat_map(u16::to_le_bytes)
            .collect::<Vec<_>>();
    }
    #[cfg(not(windows))]
    value.to_string_lossy().as_bytes().to_vec()
}

fn hex_bytes(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

fn relative_path(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

#[cfg(unix)]
fn exit_parts(status: &ExitStatus) -> (Option<i32>, Option<i32>) {
    use std::os::unix::process::ExitStatusExt;
    (status.code(), status.signal())
}

#[cfg(not(unix))]
fn exit_parts(status: &ExitStatus) -> (Option<i32>, Option<i32>) {
    (status.code(), None)
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<(), Box<dyn Error>> {
    let mut encoded = serde_json::to_vec_pretty(value)?;
    encoded.push(b'\n');
    fs::write(path, encoded)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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
            program: "printf".to_owned(),
            arguments: vec!["{command}".to_owned()],
            environment_variables: BTreeMap::new(),
            runtime: Runtime::Local,
            environment: environment(),
        }
    }

    #[test]
    fn rejects_renamed_compatibility_self_comparison() {
        let reference = launcher("reference");
        let candidate = launcher("renamed-reference");
        let suite = Suite {
            schema_version: 1,
            suite_id: "self-test".to_owned(),
            evidence_scope: EvidenceScope::Compatibility,
            cases: vec![Case {
                id: "lcov-version".to_owned(),
                surface: Surface::Cli,
                command: "lcov".to_owned(),
                arguments: vec!["--version".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };

        let output = TempDir::new().unwrap();
        let runner =
            DifferentialRunner::new(std::env::current_dir().unwrap(), reference, candidate)
                .unwrap();
        let error = runner.run(&suite, output.path()).unwrap_err();
        assert!(
            error
                .to_string()
                .contains("cannot compare identical runtime identity")
        );
    }

    #[test]
    fn rejects_duplicate_case_ids_before_execution() {
        let reference = launcher("reference");
        let candidate = launcher("candidate");
        let case = Case {
            id: "duplicate-case".to_owned(),
            surface: Surface::Cli,
            command: "lcov".to_owned(),
            arguments: Vec::new(),
            fixture: None,
            comparisons: vec![ComparisonRequest {
                dimension: Dimension::Exit,
                normalizer: NormalizerId::ExactV1,
            }],
        };
        let suite = Suite {
            schema_version: 1,
            suite_id: "duplicate-cases".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![
                case,
                Case {
                    id: "duplicate-case".to_owned(),
                    surface: Surface::Cli,
                    command: "lcov".to_owned(),
                    arguments: Vec::new(),
                    fixture: None,
                    comparisons: vec![ComparisonRequest {
                        dimension: Dimension::Exit,
                        normalizer: NormalizerId::ExactV1,
                    }],
                },
            ],
        };

        let error = validate_suite(&suite, &reference, &candidate).unwrap_err();
        assert!(error.to_string().contains("duplicate case ID"));
    }

    #[test]
    fn rejects_duplicate_comparison_dimensions() {
        let reference = launcher("reference");
        let candidate = launcher("candidate");
        let suite = Suite {
            schema_version: 1,
            suite_id: "duplicate-comparisons".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "duplicate-comparison".to_owned(),
                surface: Surface::Cli,
                command: "lcov".to_owned(),
                arguments: Vec::new(),
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

        let error = validate_suite(&suite, &reference, &candidate).unwrap_err();
        assert!(error.to_string().contains("duplicate Exit comparison"));
    }

    #[test]
    fn snapshots_file_content_and_empty_directory() {
        let directory = TempDir::new().unwrap();
        fs::write(directory.path().join("file.txt"), b"content").unwrap();
        fs::create_dir(directory.path().join("empty")).unwrap();

        let snapshot = snapshot_tree(directory.path()).unwrap();

        assert_eq!(snapshot.len(), 2);
        assert_eq!(snapshot[0].path, "empty");
        assert_eq!(snapshot[0].path_bytes_hex, "656d707479");
        assert_eq!(snapshot[0].kind, FileKind::Directory);
        assert_eq!(snapshot[1].path, "file.txt");
        assert_eq!(snapshot[1].bytes, 7);
        assert_eq!(
            snapshot[1].sha256.as_deref(),
            Some("ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73")
        );
        #[cfg(unix)]
        assert!(snapshot[1].mode.is_some());
    }

    #[test]
    fn rejects_meaningless_exit_normalizer() {
        let reference = launcher("reference");
        let candidate = launcher("candidate");
        let suite = Suite {
            schema_version: 1,
            suite_id: "invalid-normalizer".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "lcov-version".to_owned(),
                surface: Surface::Cli,
                command: "lcov".to_owned(),
                arguments: vec!["--version".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::TextCrlfToLfV1,
                }],
            }],
        };

        let error = validate_suite(&suite, &reference, &candidate).unwrap_err();
        assert!(error.to_string().contains("must use exact-v1"));
    }

    #[test]
    fn rejects_different_execution_environments() {
        let reference = launcher("reference");
        let mut candidate = launcher("candidate");
        candidate.environment.architecture = "different".to_owned();
        let suite = Suite {
            schema_version: 1,
            suite_id: "environment-check".to_owned(),
            evidence_scope: EvidenceScope::HarnessSelfTest,
            cases: vec![Case {
                id: "lcov-version".to_owned(),
                surface: Surface::Cli,
                command: "lcov".to_owned(),
                arguments: vec!["--version".to_owned()],
                fixture: None,
                comparisons: vec![ComparisonRequest {
                    dimension: Dimension::Exit,
                    normalizer: NormalizerId::ExactV1,
                }],
            }],
        };

        let error = validate_suite(&suite, &reference, &candidate).unwrap_err();
        assert!(error.to_string().contains("same environment"));
    }

    #[test]
    fn substitutes_case_placeholders_without_shell_interpolation() {
        let case = Case {
            id: "test-case".to_owned(),
            surface: Surface::Cli,
            command: "lcov; echo unsafe".to_owned(),
            arguments: Vec::new(),
            fixture: Some("fixture path".to_owned()),
            comparisons: Vec::new(),
        };

        assert_eq!(
            substitute("tool={command} fixture={fixture}", &case),
            "tool=lcov; echo unsafe fixture=."
        );
    }

    #[test]
    fn copies_fixture_tree_without_following_symlinks() {
        let source = TempDir::new().unwrap();
        let destination = TempDir::new().unwrap();
        fs::create_dir(source.path().join("nested")).unwrap();
        fs::write(source.path().join("nested/file.txt"), b"fixture").unwrap();
        #[cfg(unix)]
        std::os::unix::fs::symlink("nested/file.txt", source.path().join("link.txt")).unwrap();

        copy_directory_contents(source.path(), destination.path()).unwrap();

        assert_eq!(
            fs::read(destination.path().join("nested/file.txt")).unwrap(),
            b"fixture"
        );
        #[cfg(unix)]
        assert_eq!(
            fs::read_link(destination.path().join("link.txt")).unwrap(),
            PathBuf::from("nested/file.txt")
        );
    }
}
