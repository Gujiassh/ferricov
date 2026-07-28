use super::{Classification, NamedEntry, SourceKind, SourceReference, slug, unreviewed_metadata};
use crate::UPSTREAM_COMMIT;
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Extract a whitespace-separated Make variable with backslash continuations.
pub fn extract_makefile_words(input: &str, variable: &str) -> Option<Vec<String>> {
    let mut lines = input.lines();
    while let Some(line) = lines.next() {
        let trimmed = line.trim_start();
        let Some(rest) = trimmed.strip_prefix(variable) else {
            continue;
        };
        let Some(mut value) = rest.trim_start().strip_prefix('=') else {
            continue;
        };

        let mut words = Vec::new();
        loop {
            let continues = value.trim_end().ends_with('\\');
            words.extend(
                value
                    .trim_end_matches(|character: char| {
                        character.is_ascii_whitespace() || character == '\\'
                    })
                    .split_ascii_whitespace()
                    .map(str::to_owned),
            );
            if !continues {
                break;
            }
            value = lines.next()?.trim();
        }
        return Some(words);
    }
    None
}

pub(super) fn assignment_line(input: &str, variable: &str) -> Option<usize> {
    input.lines().enumerate().find_map(|(offset, line)| {
        let rest = line.trim_start().strip_prefix(variable)?;
        rest.trim_start().starts_with('=').then_some(offset + 1)
    })
}

pub(super) fn verify_upstream_checkout(upstream_root: &Path) -> Result<(), Box<dyn Error>> {
    let actual = git_stdout(upstream_root, &["rev-parse", "HEAD"])?;
    verify_commit_value(actual.trim())?;
    let status = git_stdout(
        upstream_root,
        &["status", "--porcelain=v1", "--untracked-files=all"],
    )?;
    verify_status_value(&status)
}

fn git_stdout(upstream_root: &Path, arguments: &[&str]) -> Result<String, Box<dyn Error>> {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(upstream_root)
        .output()?;
    if !output.status.success() {
        return Err(format!("upstream git command failed: git {}", arguments.join(" ")).into());
    }
    Ok(String::from_utf8(output.stdout)?)
}

pub(super) fn verify_commit_value(actual: &str) -> Result<(), Box<dyn Error>> {
    if actual != UPSTREAM_COMMIT {
        return Err(format!(
            "upstream commit mismatch: expected {UPSTREAM_COMMIT}, found {actual}"
        )
        .into());
    }
    Ok(())
}

pub(super) fn verify_status_value(status: &str) -> Result<(), Box<dyn Error>> {
    if !status.trim().is_empty() {
        return Err("upstream checkout is dirty; inventory requires the exact pinned tree".into());
    }
    Ok(())
}

pub(super) fn find_manual(upstream_root: &Path, command: &str) -> Option<PathBuf> {
    let manual_dir = upstream_root.join("docs/man");
    let exact = manual_dir.join(format!("{command}.rst"));
    if exact.is_file() {
        return Some(exact);
    }

    let without_extension = command.strip_suffix(".py")?;
    let fallback = manual_dir.join(format!("{without_extension}.rst"));
    fallback.is_file().then_some(fallback)
}

pub(super) fn installed_support_scripts(
    directory: &Path,
    install_manifest_line: usize,
) -> Result<Vec<NamedEntry>, Box<dyn Error>> {
    let mut scripts = Vec::new();
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if !entry.file_type()?.is_file() {
            continue;
        }
        let name = entry
            .file_name()
            .into_string()
            .map_err(|_| "upstream support script name is not valid UTF-8")?;
        if is_backup_name(&name) {
            continue;
        }
        let mut review = unreviewed_metadata(
            Classification::Unreviewed,
            vec![
                SourceReference {
                    kind: SourceKind::SupportScript,
                    path: format!("scripts/{name}"),
                    line: 1,
                },
                SourceReference {
                    kind: SourceKind::InstallManifest,
                    path: "Makefile".to_owned(),
                    line: install_manifest_line,
                },
            ],
        );
        review.source_references.sort();
        scripts.push(NamedEntry {
            id: format!("support-script.{}", slug(&name)),
            name,
            review,
        });
    }
    scripts.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(scripts)
}

pub(super) fn is_backup_name(name: &str) -> bool {
    name.contains('#')
        || name.ends_with('~')
        || name.ends_with(".orig")
        || name.ends_with(".bak")
        || name.ends_with(".BAK")
}
