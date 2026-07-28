use super::{
    Classification, ObservedAcceptance, OptionEntry, SourceKind, SourceReference, extend_unique,
    option_id, push_source, unreviewed_metadata,
};
use std::collections::{BTreeMap, BTreeSet};

pub(super) fn merge_help_candidates(
    command: &str,
    source_path: &str,
    input: &str,
    options: &mut Vec<OptionEntry>,
) {
    for mut candidate in extract_help_options(command, source_path, input) {
        let candidate_forms = std::iter::once(&candidate.canonical_name)
            .chain(&candidate.aliases)
            .cloned()
            .collect::<Vec<_>>();
        let existing = options.iter_mut().find(|entry| {
            std::iter::once(&entry.canonical_name)
                .chain(&entry.aliases)
                .any(|form| candidate_forms.contains(form))
        });
        if let Some(entry) = existing {
            // Extend aliases and source references from help; the review
            // overlay is the single source of truth for classification.
            extend_unique(&mut entry.aliases, candidate_forms);
            entry.aliases.retain(|alias| alias != &entry.canonical_name);
            for source in candidate.review.source_references {
                push_source(&mut entry.review.source_references, source);
            }
        } else {
            candidate.review.classification = Classification::Unreviewed;
            options.push(candidate);
        }
    }
}

/// Exact identity-bound default-profile observations from the pinned Oracle.
/// The review overlay owns output; this map only rejects review drift.
pub(super) fn expected_generated_token_resolutions()
-> BTreeMap<String, (ObservedAcceptance, Option<String>)> {
    let mut expected = BTreeMap::new();
    for command in [
        "lcov",
        "genhtml",
        "geninfo",
        "perl2lcov",
        "py2lcov",
        "llvm2lcov",
    ] {
        for option in known_generated_tokens(command) {
            let (acceptance, target) = match (command, *option) {
                ("lcov", "--build-dir") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("lcov", "--build-directory")),
                ),
                ("lcov", "--history") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("lcov", "--history-script")),
                ),
                ("genhtml", "--diff") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("genhtml", "--diff-file")),
                ),
                ("genhtml", "--erase-function") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("genhtml", "--erase-functions")),
                ),
                ("genhtml", "--no-source") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("genhtml", "--no-sourceview")),
                ),
                ("geninfo", "--mcdc") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("geninfo", "--mcdc-coverage")),
                ),
                ("perl2lcov", "--ignore-error") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("perl2lcov", "--ignore-errors")),
                ),
                ("llvm2lcov", "--ignore-error") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("llvm2lcov", "--ignore-errors")),
                ),
                ("llvm2lcov", "--output") => (
                    ObservedAcceptance::AcceptedUniqueAbbreviation,
                    Some(option_id("llvm2lcov", "--output-filename")),
                ),
                ("genhtml", "--fail" | "--sort") => (ObservedAcceptance::RejectedAmbiguous, None),
                _ => (ObservedAcceptance::RejectedUnknown, None),
            };
            expected.insert(option_id(command, option), (acceptance, target));
        }
    }
    expected
}

fn known_generated_tokens(command: &str) -> &'static [&'static str] {
    match command {
        "lcov" => &[
            "--annotate-script",
            "--build-dir",
            "--coverage",
            "--diff",
            "--diff-file",
            "--history",
            "--output-filename",
            "--path",
            "--substitution",
        ],
        "genhtml" => &[
            "--add-tracefile",
            "--baseline-file-pattern",
            "--capture",
            "--compare",
            "--diff",
            "--erase-function",
            "--fail",
            "--highlight",
            "--line",
            "--no-source",
            "--show-proportions",
            "--sort",
        ],
        "geninfo" => &[
            "--add-tracefile",
            "--annotate-script",
            "--capture",
            "--coverage",
            "--directory",
            "--mcdc",
            "--show-proportions",
        ],
        "perl2lcov" => &["--ignore-error"],
        "py2lcov" => &[
            "--append",
            "--baseline-file",
            "--branch",
            "--data-file",
            "--filter",
        ],
        "llvm2lcov" => &[
            "--capture",
            "--coverage",
            "--gcov-tool",
            "--ignore-error",
            "--output",
            "--sparse",
            "--testname",
        ],
        _ => &[],
    }
}

pub(super) fn extract_help_options(
    command: &str,
    source_path: &str,
    input: &str,
) -> Vec<OptionEntry> {
    let mut entries: BTreeMap<String, OptionEntry> = BTreeMap::new();
    for (offset, line) in input.lines().enumerate() {
        let Some(groups) = option_definition_groups(line) else {
            continue;
        };
        for forms in groups {
            let canonical_name = forms
                .iter()
                .find(|form| form.starts_with("--"))
                .unwrap_or(&forms[0])
                .clone();
            let aliases = forms
                .into_iter()
                .filter(|form| form != &canonical_name)
                .collect::<Vec<_>>();
            let source = SourceReference {
                kind: SourceKind::HelpDefinition,
                path: source_path.to_owned(),
                line: offset + 1,
            };

            match entries.get_mut(&canonical_name) {
                Some(entry) => {
                    extend_unique(&mut entry.aliases, aliases);
                    push_source(&mut entry.review.source_references, source);
                }
                None => {
                    entries.insert(
                        canonical_name.clone(),
                        OptionEntry {
                            id: option_id(command, &canonical_name),
                            canonical_name,
                            aliases,
                            profile_parser_resolution: None,
                            review: unreviewed_metadata(Classification::Public, vec![source]),
                        },
                    );
                }
            }
        }
    }
    entries.into_values().collect()
}

pub(super) fn merge_manual_candidates(
    command: &str,
    source_path: &str,
    input: &str,
    options: &mut Vec<OptionEntry>,
) {
    for (name, lines) in extract_long_option_occurrences(input) {
        let references = lines
            .into_iter()
            .map(|line| SourceReference {
                kind: SourceKind::ManualCandidate,
                path: source_path.to_owned(),
                line,
            })
            .collect::<Vec<_>>();

        if let Some(entry) = options.iter_mut().find(|entry| {
            entry.canonical_name == name || entry.aliases.iter().any(|alias| alias == &name)
        }) {
            for reference in references {
                push_source(&mut entry.review.source_references, reference);
            }
        } else {
            options.push(OptionEntry {
                id: option_id(command, &name),
                canonical_name: name,
                aliases: Vec::new(),
                profile_parser_resolution: None,
                review: unreviewed_metadata(Classification::Unreviewed, references),
            });
        }
    }
}

fn option_definition_groups(line: &str) -> Option<Vec<Vec<String>>> {
    let trimmed = line.trim_start();
    let indentation = line.len() - trimmed.len();
    if !(2..=6).contains(&indentation) || !starts_with_option_form(trimmed) {
        return None;
    }
    let specification = split_help_columns(trimmed).0;
    let mut forms = extract_option_forms(specification);
    if forms.is_empty() {
        return None;
    }

    let mut inverse_forms = Vec::new();
    forms.retain(|form| {
        let Some(suffix) = form.strip_prefix("--no-") else {
            return true;
        };
        if specification.contains(&format!("--(no-){suffix}")) {
            inverse_forms.push(form.clone());
            false
        } else {
            true
        }
    });

    let mut groups = vec![forms];
    groups.extend(inverse_forms.into_iter().map(|form| vec![form]));
    Some(groups)
}

pub(super) fn starts_with_option_form(input: &str) -> bool {
    let bytes = input.as_bytes();
    if bytes.first() != Some(&b'-') {
        return false;
    }
    match bytes.get(1) {
        Some(b'-') => bytes
            .get(2)
            .is_some_and(|byte| byte.is_ascii_alphabetic() || *byte == b'('),
        Some(byte) => byte.is_ascii_alphanumeric(),
        None => false,
    }
}

fn split_help_columns(input: &str) -> (&str, &str) {
    let bytes = input.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index].is_ascii_whitespace() {
            let start = index;
            while index < bytes.len() && bytes[index].is_ascii_whitespace() {
                index += 1;
            }
            if index - start >= 2 {
                return (&input[..start], &input[index..]);
            }
        } else {
            index += 1;
        }
    }
    (input, "")
}

fn extract_option_forms(input: &str) -> Vec<String> {
    let bytes = input.as_bytes();
    let mut forms = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] != b'-' || (index > 0 && !is_option_separator(bytes[index - 1])) {
            index += 1;
            continue;
        }

        if bytes.get(index + 1) == Some(&b'-') {
            if input[index..].starts_with("--(no-)") {
                let name_start = index + "--(no-)".len();
                let end = option_name_end(bytes, name_start);
                if end > name_start {
                    let suffix = &input[name_start..end];
                    forms.push(format!("--{suffix}"));
                    forms.push(format!("--no-{suffix}"));
                    index = end;
                    continue;
                }
            } else if bytes.get(index + 2).is_some_and(u8::is_ascii_alphabetic) {
                let end = option_name_end(bytes, index + 2);
                forms.push(input[index..end].to_owned());
                index = end;
                continue;
            }
        } else if bytes.get(index + 1).is_some_and(u8::is_ascii_alphanumeric) {
            forms.push(input[index..index + 2].to_owned());
            index += 2;
            continue;
        }
        index += 1;
    }
    forms
}

fn option_name_end(bytes: &[u8], start: usize) -> usize {
    let mut end = start;
    while end < bytes.len() && (bytes[end].is_ascii_alphanumeric() || bytes[end] == b'-') {
        end += 1;
    }
    end
}

fn is_option_separator(byte: u8) -> bool {
    byte.is_ascii_whitespace() || byte == b',' || byte == b'[' || byte == b'('
}

fn extract_long_option_occurrences(input: &str) -> BTreeMap<String, BTreeSet<usize>> {
    let mut occurrences: BTreeMap<String, BTreeSet<usize>> = BTreeMap::new();
    for (offset, line) in input.lines().enumerate() {
        let bytes = line.as_bytes();
        let mut index = 0;
        while index + 2 < bytes.len() {
            if bytes[index] != b'-'
                || bytes[index + 1] != b'-'
                || (index > 0 && bytes[index - 1] == b'-')
            {
                index += 1;
                continue;
            }

            if line[index..].starts_with("--(no-)") {
                let name_start = index + "--(no-)".len();
                let end = option_name_end(bytes, name_start);
                if end > name_start {
                    let suffix = &line[name_start..end];
                    occurrences
                        .entry(format!("--{suffix}"))
                        .or_default()
                        .insert(offset + 1);
                    occurrences
                        .entry(format!("--no-{suffix}"))
                        .or_default()
                        .insert(offset + 1);
                    index = end;
                    continue;
                }
            } else if bytes[2 + index].is_ascii_alphabetic() {
                let end = option_name_end(bytes, index + 2);
                occurrences
                    .entry(line[index..end].to_owned())
                    .or_default()
                    .insert(offset + 1);
                index = end;
                continue;
            }
            index += 1;
        }
    }
    occurrences
}

/// Extract every syntactically valid long-option candidate from arbitrary text.
pub fn extract_long_options(input: &str) -> BTreeSet<String> {
    extract_long_option_occurrences(input).into_keys().collect()
}
