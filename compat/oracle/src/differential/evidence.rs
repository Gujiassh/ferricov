//! Filesystem snapshot, artifact hashing, and evidence persistence.
//!
//! Owns the file-tree snapshot format, artifact persistence with content hashes,
//! and exit-status decomposition. Kept separate from process execution so that
//! snapshot semantics can evolve independently of the runner.

use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::OsStr;
use std::fs;
use std::path::Path;
use std::process::ExitStatus;

#[derive(Debug, Serialize, Eq, PartialEq)]
pub(crate) struct FileEntry {
    pub(crate) path: String,
    pub(crate) path_bytes_hex: String,
    pub(crate) kind: FileKind,
    pub(crate) bytes: u64,
    pub(crate) sha256: Option<String>,
    pub(crate) mode: Option<u32>,
    pub(crate) uid: Option<u32>,
    pub(crate) gid: Option<u32>,
    pub(crate) hardlink_count: Option<u64>,
    pub(crate) hardlink_group: Option<String>,
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
pub(crate) enum FileKind {
    File,
    Directory,
    Symlink,
}

pub(crate) struct CapturedRun {
    pub(crate) exit_status: ExitStatus,
    pub(crate) stdout: Vec<u8>,
    pub(crate) stderr: Vec<u8>,
    pub(crate) file_tree: Vec<FileEntry>,
    pub(crate) wall_seconds: f64,
}

/// Persisted run metadata including content-addressed artifact references.
///
#[derive(Debug, Serialize)]
pub(crate) struct RunResult {
    pub(crate) exit_code: Option<i32>,
    pub(crate) signal: Option<i32>,
    pub(crate) stdout_artifact: String,
    pub(crate) stderr_artifact: String,
    pub(crate) file_tree_artifact: String,
    pub(crate) stdout_sha256: String,
    pub(crate) stderr_sha256: String,
    pub(crate) file_tree_sha256: String,
    pub(crate) stdout_bytes: u64,
    pub(crate) stderr_bytes: u64,
    pub(crate) file_tree_bytes: u64,
    pub(crate) timeout: TimeoutEvidence,
    pub(crate) cleanup: CleanupEvidence,
    pub(crate) metrics: Metrics,
}

/// Evidence about the timeout that was applied to this run.
///
/// `termination_signal_sent` records the signal number actually delivered to
/// the process/group (None when delivery could not be confirmed).
/// `escalation_signal_sent` records a second, harder signal when the first
/// did not suffice (for example SIGKILL after SIGTERM).
#[derive(Debug, Serialize)]
pub(crate) struct TimeoutEvidence {
    pub(crate) applied_seconds: u64,
    pub(crate) expired: bool,
    pub(crate) termination_signal_sent: Option<i32>,
    pub(crate) escalation_signal_sent: Option<i32>,
}

/// Evidence about process/container cleanup after a timeout.
///
/// `direct_child_reaped` is true when the runner's immediate child exited
/// and its exit status was collected.
///
/// `process_group_empty` is Some(true) when the runner verified that no
/// processes remain in the setsid group after termination.
///
/// `container_absent` is Some(true) when the runner verified that the
/// Docker container no longer exists.
///
/// Fields are `None` when verification could not be performed
/// (e.g. observer tool failure) — this is a deliberate fail-closed design.
#[derive(Debug, Serialize)]
pub(crate) struct CleanupEvidence {
    pub(crate) direct_child_reaped: bool,
    pub(crate) process_group_empty: Option<bool>,
    pub(crate) container_absent: Option<bool>,
}

#[derive(Debug, Serialize)]
pub(crate) struct Metrics {
    pub(crate) wall_seconds: f64,
    pub(crate) user_cpu_seconds: Option<f64>,
    pub(crate) system_cpu_seconds: Option<f64>,
    pub(crate) peak_rss_bytes: Option<u64>,
    pub(crate) output_bytes: u64,
    pub(crate) output_files: u64,
}

/// Compute a SHA-256 content hash and return it as a hex string.
pub(crate) fn sha256_hex(data: &[u8]) -> String {
    format!("{:x}", Sha256::digest(data))
}

/// Snapshot the entire directory tree rooted at `root`.
pub(crate) fn snapshot_tree(root: &Path) -> Result<Vec<FileEntry>, Box<dyn Error>> {
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
                Some(sha256_hex(&content)),
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
                Some(sha256_hex(&encoded)),
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

/// Persist captured run artifacts to disk and return content-addressed metadata.
///
pub(crate) fn persist_run(
    case_root: &Path,
    role: &str,
    captured: &CapturedRun,
    timeout: TimeoutEvidence,
    cleanup: CleanupEvidence,
) -> Result<RunResult, Box<dyn Error>> {
    let role_root = case_root.join(role);
    fs::create_dir(&role_root)?;

    let stdout_path = role_root.join("stdout.bin");
    let stderr_path = role_root.join("stderr.bin");
    let file_tree_path = role_root.join("file-tree.json");

    write_new(&stdout_path, &captured.stdout)?;
    write_new(&stderr_path, &captured.stderr)?;

    let file_tree_json = serde_json::to_vec_pretty(&captured.file_tree)?;
    write_new(&file_tree_path, &file_tree_json)?;

    let stdout_sha256 = sha256_hex(&captured.stdout);
    let stderr_sha256 = sha256_hex(&captured.stderr);
    let file_tree_sha256 = sha256_hex(&file_tree_json);

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
        stdout_sha256,
        stderr_sha256,
        file_tree_sha256,
        stdout_bytes: captured.stdout.len() as u64,
        stderr_bytes: captured.stderr.len() as u64,
        file_tree_bytes: file_tree_json.len() as u64,
        timeout,
        cleanup,
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
pub(crate) fn exit_parts(status: &ExitStatus) -> (Option<i32>, Option<i32>) {
    use std::os::unix::process::ExitStatusExt;
    (status.code(), status.signal())
}

#[cfg(not(unix))]
pub(crate) fn exit_parts(status: &ExitStatus) -> (Option<i32>, Option<i32>) {
    (status.code(), None)
}

#[cfg(test)]
pub(crate) fn write_json(path: &Path, value: &impl Serialize) -> Result<(), Box<dyn Error>> {
    let mut encoded = serde_json::to_vec_pretty(value)?;
    encoded.push(b'\n');
    fs::write(path, encoded)?;
    Ok(())
}

pub(crate) fn write_json_new(path: &Path, value: &impl Serialize) -> Result<(), Box<dyn Error>> {
    let mut encoded = serde_json::to_vec_pretty(value)?;
    encoded.push(b'\n');
    write_new(path, &encoded)
}

pub(crate) fn write_new(path: &Path, bytes: &[u8]) -> Result<(), Box<dyn Error>> {
    use std::io::Write;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn timeout_evidence() -> TimeoutEvidence {
        TimeoutEvidence {
            applied_seconds: 20,
            expired: false,
            termination_signal_sent: None,
            escalation_signal_sent: None,
        }
    }

    fn cleanup_evidence() -> CleanupEvidence {
        CleanupEvidence {
            direct_child_reaped: true,
            process_group_empty: Some(true),
            container_absent: None,
        }
    }

    fn fake_exit_status() -> ExitStatus {
        std::process::Command::new("true").status().unwrap()
    }

    #[test]
    fn snapshot_file_content_and_empty_directory() {
        let directory = tempfile::TempDir::new().unwrap();
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
    fn artifact_hashes_are_stable() {
        let directory = tempfile::TempDir::new().unwrap();
        let captured = CapturedRun {
            exit_status: fake_exit_status(),
            stdout: b"hello stdout".to_vec(),
            stderr: b"hello stderr".to_vec(),
            file_tree: vec![],
            wall_seconds: 0.0,
        };

        let result1 = persist_run(
            directory.path(),
            "reference",
            &captured,
            timeout_evidence(),
            cleanup_evidence(),
        )
        .unwrap();
        let second = tempfile::TempDir::new().unwrap();
        let result2 = persist_run(
            second.path(),
            "reference",
            &captured,
            timeout_evidence(),
            cleanup_evidence(),
        )
        .unwrap();

        assert_eq!(result1.stdout_sha256, result2.stdout_sha256);
        assert_eq!(result1.stderr_sha256, result2.stderr_sha256);
        assert_eq!(result1.stdout_bytes, 12);
        assert_eq!(result1.stderr_bytes, 12);
    }

    #[test]
    fn mutated_artifact_changes_hash() {
        let directory = tempfile::TempDir::new().unwrap();
        let case_root = directory.path();

        let captured1 = CapturedRun {
            exit_status: fake_exit_status(),
            stdout: b"original".to_vec(),
            stderr: vec![],
            file_tree: vec![],
            wall_seconds: 0.0,
        };
        let captured2 = CapturedRun {
            exit_status: fake_exit_status(),
            stdout: b"modified".to_vec(),
            stderr: vec![],
            file_tree: vec![],
            wall_seconds: 0.0,
        };

        let r1 = persist_run(
            case_root,
            "a",
            &captured1,
            timeout_evidence(),
            cleanup_evidence(),
        )
        .unwrap();
        let r2 = persist_run(
            case_root,
            "b",
            &captured2,
            timeout_evidence(),
            cleanup_evidence(),
        )
        .unwrap();

        assert_ne!(r1.stdout_sha256, r2.stdout_sha256);
        assert_eq!(r1.stdout_bytes, 8);
        assert_eq!(r2.stdout_bytes, 8);
    }

    #[test]
    fn timeout_and_cleanup_are_always_retained() {
        let directory = tempfile::TempDir::new().unwrap();
        let captured = CapturedRun {
            exit_status: fake_exit_status(),
            stdout: vec![],
            stderr: vec![],
            file_tree: vec![],
            wall_seconds: 0.0,
        };

        let result = persist_run(
            directory.path(),
            "reference",
            &captured,
            timeout_evidence(),
            cleanup_evidence(),
        )
        .unwrap();
        assert_eq!(result.timeout.applied_seconds, 20);
        assert!(!result.timeout.expired);
        assert!(result.cleanup.direct_child_reaped);
    }

    #[test]
    fn file_tree_content_hash_is_stable() {
        let directory = tempfile::TempDir::new().unwrap();
        fs::write(directory.path().join("a.txt"), b"alpha").unwrap();
        let file_tree = snapshot_tree(directory.path()).unwrap();
        let json1 = serde_json::to_vec_pretty(&file_tree).unwrap();
        let json2 = serde_json::to_vec_pretty(&file_tree).unwrap();
        assert_eq!(sha256_hex(&json1), sha256_hex(&json2));
    }

    #[test]
    fn mutated_file_tree_changes_file_tree_sha256() {
        let dir1 = tempfile::TempDir::new().unwrap();
        let dir2 = tempfile::TempDir::new().unwrap();
        fs::write(dir1.path().join("a.txt"), b"alpha").unwrap();
        fs::write(dir2.path().join("a.txt"), b"beta").unwrap();

        let tree1 = snapshot_tree(dir1.path()).unwrap();
        let tree2 = snapshot_tree(dir2.path()).unwrap();

        let json1 = serde_json::to_vec_pretty(&tree1).unwrap();
        let json2 = serde_json::to_vec_pretty(&tree2).unwrap();
        assert_ne!(sha256_hex(&json1), sha256_hex(&json2));
    }
}
