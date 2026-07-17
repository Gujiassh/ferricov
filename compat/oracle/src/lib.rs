//! Differential execution and compatibility comparison support.

mod differential;
mod normalizer;

pub use differential::{DifferentialRunner, Launcher, Suite, SuiteOutcome};
pub use normalizer::{NormalizerId, normalize};

use serde::Serialize;
use std::collections::BTreeSet;
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// LCOV release used as the first compatibility target.
pub const UPSTREAM_RELEASE: &str = "v2.5";

/// Immutable upstream commit used by the Oracle.
pub const UPSTREAM_COMMIT: &str = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5";

/// Machine-readable inventory of the upstream public surface.
#[derive(Debug, Serialize)]
pub struct Inventory {
    pub schema_version: u32,
    pub upstream_release: &'static str,
    pub upstream_commit: &'static str,
    pub commands: Vec<CommandInventory>,
    pub config_keys: Vec<String>,
    pub support_scripts: Vec<String>,
    pub totals: InventoryTotals,
}

/// Options discovered for an installed upstream command.
#[derive(Debug, Serialize)]
pub struct CommandInventory {
    pub name: String,
    pub help_snapshot: Option<String>,
    pub manual: Option<String>,
    pub help_options: Vec<String>,
    pub manual_options: Vec<String>,
    pub all_options: Vec<String>,
}

/// High-level counts used to detect accidental inventory shrinkage.
#[derive(Debug, Serialize)]
pub struct InventoryTotals {
    pub installed_commands: usize,
    pub distinct_long_options: usize,
    pub config_keys: usize,
    pub support_scripts: usize,
}

/// Generate the candidate inventory from an exact upstream checkout.
pub fn generate_inventory(
    upstream_root: &Path,
    help_dir: &Path,
) -> Result<Inventory, Box<dyn Error>> {
    verify_upstream_commit(upstream_root)?;

    let makefile = fs::read_to_string(upstream_root.join("Makefile"))?;
    let command_names = extract_makefile_words(&makefile, "EXES")
        .ok_or("upstream Makefile does not define EXES")?;

    let mut distinct_options = BTreeSet::new();
    let mut commands = Vec::with_capacity(command_names.len());

    for name in command_names {
        let help_path = help_dir.join(format!("{name}.txt"));
        let manual_path = find_manual(upstream_root, &name);

        let help_options = read_options_if_present(&help_path)?;
        let manual_options = match &manual_path {
            Some(path) => read_options_if_present(path)?,
            None => BTreeSet::new(),
        };
        let all_options = help_options
            .union(&manual_options)
            .cloned()
            .collect::<BTreeSet<_>>();

        distinct_options.extend(all_options.iter().cloned());
        commands.push(CommandInventory {
            name,
            help_snapshot: help_path
                .is_file()
                .then(|| relative_display(help_dir, &help_path)),
            manual: manual_path
                .as_ref()
                .map(|path| relative_display(upstream_root, path)),
            help_options: help_options.into_iter().collect(),
            manual_options: manual_options.into_iter().collect(),
            all_options: all_options.into_iter().collect(),
        });
    }

    let config = fs::read_to_string(upstream_root.join("lcovrc"))?;
    let config_keys = extract_config_keys(&config).into_iter().collect::<Vec<_>>();
    let support_scripts = installed_support_scripts(&upstream_root.join("scripts"))?;

    let totals = InventoryTotals {
        installed_commands: commands.len(),
        distinct_long_options: distinct_options.len(),
        config_keys: config_keys.len(),
        support_scripts: support_scripts.len(),
    };

    Ok(Inventory {
        schema_version: 1,
        upstream_release: UPSTREAM_RELEASE,
        upstream_commit: UPSTREAM_COMMIT,
        commands,
        config_keys,
        support_scripts,
        totals,
    })
}

/// Extract every syntactically valid long option token from text.
pub fn extract_long_options(input: &str) -> BTreeSet<String> {
    let bytes = input.as_bytes();
    let mut options = BTreeSet::new();
    let mut index = 0;

    while index + 2 < bytes.len() {
        let is_start = bytes[index] == b'-'
            && bytes[index + 1] == b'-'
            && bytes[index + 2].is_ascii_alphabetic()
            && (index == 0 || bytes[index - 1] != b'-');
        if !is_start {
            index += 1;
            continue;
        }

        let mut end = index + 3;
        while end < bytes.len() && (bytes[end].is_ascii_alphanumeric() || bytes[end] == b'-') {
            end += 1;
        }
        options.insert(input[index..end].to_owned());
        index = end;
    }

    options
}

/// Extract active and commented default keys from the upstream lcovrc file.
pub fn extract_config_keys(input: &str) -> BTreeSet<String> {
    input
        .lines()
        .filter_map(|line| {
            let candidate = line.trim_start().trim_start_matches('#').trim_start();
            let (key, _) = candidate.split_once('=')?;
            let key = key.trim();
            let mut chars = key.chars();
            if !chars
                .next()
                .is_some_and(|first| first.is_ascii_alphabetic())
            {
                return None;
            }
            chars
                .all(|character| character.is_ascii_alphanumeric() || character == '_')
                .then(|| key.to_owned())
        })
        .collect()
}

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

fn verify_upstream_commit(upstream_root: &Path) -> Result<(), Box<dyn Error>> {
    let output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(upstream_root)
        .output()?;
    if !output.status.success() {
        return Err("failed to resolve upstream git commit".into());
    }
    let actual = String::from_utf8(output.stdout)?;
    if actual.trim() != UPSTREAM_COMMIT {
        return Err(format!(
            "upstream commit mismatch: expected {UPSTREAM_COMMIT}, found {}",
            actual.trim()
        )
        .into());
    }
    Ok(())
}

fn find_manual(upstream_root: &Path, command: &str) -> Option<PathBuf> {
    let manual_dir = upstream_root.join("docs/man");
    let exact = manual_dir.join(format!("{command}.rst"));
    if exact.is_file() {
        return Some(exact);
    }

    let without_extension = command.strip_suffix(".py")?;
    let fallback = manual_dir.join(format!("{without_extension}.rst"));
    fallback.is_file().then_some(fallback)
}

fn read_options_if_present(path: &Path) -> Result<BTreeSet<String>, Box<dyn Error>> {
    if !path.is_file() {
        return Ok(BTreeSet::new());
    }
    Ok(extract_long_options(&fs::read_to_string(path)?))
}

fn installed_support_scripts(directory: &Path) -> Result<Vec<String>, Box<dyn Error>> {
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
        if !is_backup_name(&name) {
            scripts.push(name);
        }
    }
    scripts.sort_unstable();
    Ok(scripts)
}

fn is_backup_name(name: &str) -> bool {
    name.contains('#')
        || name.ends_with('~')
        || name.ends_with(".orig")
        || name.ends_with(".bak")
        || name.ends_with(".BAK")
}

fn relative_display(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_unique_long_options() {
        let input = "-a, --add-tracefile FILE\n--branch-coverage, --rc key=value\n---bad";

        assert_eq!(
            extract_long_options(input),
            BTreeSet::from([
                "--add-tracefile".to_owned(),
                "--branch-coverage".to_owned(),
                "--rc".to_owned(),
            ])
        );
    }

    #[test]
    fn extracts_syntactic_config_key_candidates() {
        let input =
            "branch_coverage = 1\n# mcdc_coverage = 0\n# prose = not a key!\n# 9invalid = 1";

        assert_eq!(
            extract_config_keys(input),
            BTreeSet::from([
                "branch_coverage".to_owned(),
                "mcdc_coverage".to_owned(),
                "prose".to_owned(),
            ])
        );
    }

    #[test]
    fn extracts_continued_makefile_words() {
        let input = "OTHER = ignored\nEXES = \\\n  lcov genhtml \\\n  geninfo\nNEXT = value\n";

        assert_eq!(
            extract_makefile_words(input, "EXES"),
            Some(vec![
                "lcov".to_owned(),
                "genhtml".to_owned(),
                "geninfo".to_owned()
            ])
        );
    }

    #[test]
    fn recognizes_upstream_backup_names() {
        assert!(is_backup_name("gitdiff.bak"));
        assert!(is_backup_name("#gitdiff#"));
        assert!(!is_backup_name("gitdiff.pm"));
    }
}
