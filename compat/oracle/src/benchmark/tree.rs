use super::contract::{ArtifactRef, OutputChange, OutputStatus, TreeEntry, TreeEntryKind};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};

pub fn sha256_bytes(content: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(content))
}

pub fn sha256_file(path: &Path) -> Result<String, Box<dyn Error>> {
    Ok(sha256_bytes(&fs::read(path)?))
}

pub fn artifact_ref(root: &Path, path: &Path) -> Result<ArtifactRef, Box<dyn Error>> {
    let content = fs::read(path)?;
    Ok(ArtifactRef {
        path: relative_utf8(root, path)?,
        sha256: sha256_bytes(&content),
        bytes: content.len() as u64,
    })
}

pub fn copy_fixture(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
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
        fs::set_permissions(destination, metadata.permissions())?;
    } else if file_type.is_dir() {
        fs::create_dir(destination)?;
        fs::set_permissions(destination, metadata.permissions())?;
        copy_fixture(source, destination)?;
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

#[cfg(not(unix))]
fn copy_symlink(_source: &Path, _destination: &Path) -> Result<(), Box<dyn Error>> {
    Err("Oracle baselines require Linux symlink semantics".into())
}

pub fn snapshot_tree(root: &Path) -> Result<BTreeMap<String, TreeEntry>, Box<dyn Error>> {
    let mut entries = BTreeMap::new();
    snapshot_directory(root, root, &mut entries)?;
    Ok(entries)
}

fn snapshot_directory(
    root: &Path,
    directory: &Path,
    entries: &mut BTreeMap<String, TreeEntry>,
) -> Result<(), Box<dyn Error>> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)?;
        let path_text = relative_utf8(root, &path)?;
        let file_type = metadata.file_type();
        let tree_entry = if file_type.is_file() {
            let content = fs::read(&path)?;
            TreeEntry {
                path: path_text.clone(),
                kind: TreeEntryKind::File,
                bytes: content.len() as u64,
                sha256: Some(sha256_bytes(&content)),
            }
        } else if file_type.is_dir() {
            snapshot_directory(root, &path, entries)?;
            TreeEntry {
                path: path_text.clone(),
                kind: TreeEntryKind::Directory,
                bytes: 0,
                sha256: None,
            }
        } else if file_type.is_symlink() {
            let target = fs::read_link(&path)?;
            let target = target
                .to_str()
                .ok_or("benchmark symlink target is not valid UTF-8")?;
            TreeEntry {
                path: path_text.clone(),
                kind: TreeEntryKind::Symlink,
                bytes: target.len() as u64,
                sha256: Some(sha256_bytes(target.as_bytes())),
            }
        } else {
            return Err(format!("unsupported benchmark output: {}", path.display()).into());
        };
        entries.insert(path_text, tree_entry);
    }
    Ok(())
}

pub fn output_changes(
    before: &BTreeMap<String, TreeEntry>,
    after: &BTreeMap<String, TreeEntry>,
) -> Vec<OutputChange> {
    let paths = before
        .keys()
        .chain(after.keys())
        .cloned()
        .collect::<BTreeSet<_>>();
    paths
        .into_iter()
        .filter_map(|path| match (before.get(&path), after.get(&path)) {
            (None, Some(entry)) => Some(change(entry, OutputStatus::Created)),
            (Some(previous), Some(entry)) if previous != entry => {
                Some(change(entry, OutputStatus::Modified))
            }
            (Some(previous), None) => Some(OutputChange {
                path: previous.path.clone(),
                status: OutputStatus::Removed,
                kind: previous.kind,
                bytes: 0,
                sha256: None,
            }),
            _ => None,
        })
        .collect()
}

fn change(entry: &TreeEntry, status: OutputStatus) -> OutputChange {
    OutputChange {
        path: entry.path.clone(),
        status,
        kind: entry.kind,
        bytes: entry.bytes,
        sha256: entry.sha256.clone(),
    }
}

pub fn output_totals(changes: &[OutputChange]) -> (u64, u64) {
    changes
        .iter()
        .filter(|entry| {
            entry.kind == TreeEntryKind::File && !matches!(entry.status, OutputStatus::Removed)
        })
        .fold((0, 0), |(bytes, files), entry| {
            (bytes + entry.bytes, files + 1)
        })
}

pub fn relative_utf8(root: &Path, path: &Path) -> Result<String, Box<dyn Error>> {
    let relative = path.strip_prefix(root)?;
    let value = relative
        .to_str()
        .ok_or("benchmark evidence path is not valid UTF-8")?;
    Ok(value.replace(std::path::MAIN_SEPARATOR, "/"))
}

pub fn safe_repository_path(root: &Path, value: &str) -> Result<PathBuf, Box<dyn Error>> {
    let candidate = Path::new(value);
    if candidate.is_absolute()
        || candidate.components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir
                    | std::path::Component::CurDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err(format!("unsafe repository-relative path: {value}").into());
    }
    Ok(root.join(candidate))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(path: &str, bytes: u64, digest: &str) -> TreeEntry {
        TreeEntry {
            path: path.to_owned(),
            kind: TreeEntryKind::File,
            bytes,
            sha256: Some(digest.to_owned()),
        }
    }

    #[test]
    fn output_delta_excludes_unchanged_fixture_files() {
        let before = BTreeMap::from([("input.info".to_owned(), entry("input.info", 3, "a"))]);
        let after = BTreeMap::from([
            ("input.info".to_owned(), entry("input.info", 3, "a")),
            ("output.info".to_owned(), entry("output.info", 7, "b")),
        ]);

        let changes = output_changes(&before, &after);

        assert_eq!(changes.len(), 1);
        assert_eq!(changes[0].path, "output.info");
        assert_eq!(output_totals(&changes), (7, 1));
    }

    #[test]
    fn rejects_parent_traversal() {
        let error = safe_repository_path(Path::new("/repo"), "../outside").unwrap_err();
        assert!(error.to_string().contains("unsafe"));
    }
}
