use super::candidate::{
    expected_generated_token_resolutions, extract_help_options, merge_help_candidates,
    merge_manual_candidates, starts_with_option_form,
};
use super::config::extract_config_entries;
use super::install::{is_backup_name, verify_commit_value, verify_status_value};
use super::parser::{
    extract_argparse_option_definitions, extract_perl_option_specifications, parser_option_entry,
    perl_option_forms,
};
use super::*;
use std::collections::BTreeSet;

fn extract_positional_arguments(command: &str, source_path: &str, input: &str) -> Vec<NamedEntry> {
    let argparse = extract_argparse_positionals(command, source_path, input);
    if argparse.is_empty() {
        extract_usage_positionals(command, source_path, input)
    } else {
        argparse
    }
}

fn extract_argparse_positionals(command: &str, source_path: &str, input: &str) -> Vec<NamedEntry> {
    let mut in_section = false;
    let mut entries = Vec::new();
    for (offset, line) in input.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.eq_ignore_ascii_case("positional arguments:") {
            in_section = true;
            continue;
        }
        if !in_section {
            continue;
        }
        if trimmed.eq_ignore_ascii_case("options:")
            || trimmed.eq_ignore_ascii_case("optional arguments:")
        {
            break;
        }
        if trimmed.is_empty() {
            continue;
        }

        let indentation = line.len() - line.trim_start().len();
        if indentation > 4 || starts_with_option_form(trimmed) {
            continue;
        }
        let Some(name) = trimmed.split_ascii_whitespace().next() else {
            continue;
        };
        entries.push(named_entry(
            positional_id(command, name),
            name.to_owned(),
            Classification::Public,
            SourceReference {
                kind: SourceKind::HelpDefinition,
                path: source_path.to_owned(),
                line: offset + 1,
            },
        ));
    }
    entries
}

#[cfg(test)]
fn extract_usage_positionals(command: &str, source_path: &str, input: &str) -> Vec<NamedEntry> {
    let mut in_usage = false;
    let mut skipped_command = false;
    let mut seen = BTreeSet::new();
    let mut entries = Vec::new();

    for (offset, line) in input.lines().enumerate() {
        let trimmed = line.trim();
        let content = if !in_usage {
            let Some((label, rest)) = trimmed.split_once(':') else {
                continue;
            };
            if !label.eq_ignore_ascii_case("usage") {
                continue;
            }
            in_usage = true;
            rest
        } else {
            if trimmed.is_empty() || !line.starts_with(char::is_whitespace) {
                break;
            }
            trimmed
        };

        for raw in content.split_ascii_whitespace() {
            if !skipped_command {
                skipped_command = true;
                continue;
            }
            let Some(name) = normalize_usage_token(raw) else {
                continue;
            };
            if name.eq_ignore_ascii_case("OPTIONS")
                || name.starts_with('-')
                || name == "..."
                || !is_positional_name(&name)
                || !seen.insert(name.clone())
            {
                continue;
            }
            entries.push(named_entry(
                positional_id(command, &name),
                name,
                Classification::Public,
                SourceReference {
                    kind: SourceKind::HelpUsage,
                    path: source_path.to_owned(),
                    line: offset + 1,
                },
            ));
        }
    }
    entries
}

#[cfg(test)]
fn normalize_usage_token(raw: &str) -> Option<String> {
    let token = raw.trim_matches(|character| matches!(character, '[' | ']' | ','));
    let token = token.trim_end_matches("...").trim_end_matches(']');
    (!token.is_empty()).then(|| token.to_owned())
}

#[cfg(test)]
fn is_positional_name(name: &str) -> bool {
    name.chars().all(|character| {
        character.is_ascii_alphanumeric() || matches!(character, '_' | '-' | '.' | '(' | ')')
    })
}

#[test]
fn extracts_perl_parser_definitions_and_explicit_aliases() {
    let input = concat!(
        "ignored = 'value'\n",
        "our %options = (\"directory|d|di\" => \\$directory,\n",
        "                 'quiet|q+' => \\$quiet,);\n",
    );
    let definitions = extract_perl_option_specifications(input, "our %options = (", "'quiet|q+'")
        .expect("parser block must be extracted");

    assert_eq!(definitions[0], ("directory|d|di".to_owned(), 2));
    assert_eq!(definitions[1], ("quiet|q+".to_owned(), 3));
    assert_eq!(
        perl_option_forms(&definitions[0].0),
        ["--directory", "-d", "--di"]
    );
    assert_eq!(perl_option_forms(&definitions[1].0), ["--quiet", "-q"]);
}

#[test]
fn extracts_argparse_definitions_without_positional_or_keyword_strings() {
    let input = concat!(
        "parser.add_argument('-t', '--test-name', '--testname', dest='testName')\n",
        "parser.add_argument('inputs', nargs='*')\n",
    );

    assert_eq!(
        extract_argparse_option_definitions(input).expect("option must parse"),
        vec![(
            vec![
                "-t".to_owned(),
                "--test-name".to_owned(),
                "--testname".to_owned()
            ],
            1
        )]
    );
}

#[test]
fn parser_presence_gates_help_publicity_and_known_ghosts_are_explicit() {
    let mut options = vec![parser_option_entry(
        "genhtml",
        "no-sort".to_owned(),
        "bin/genhtml",
        10,
    )];
    merge_help_candidates(
        "genhtml",
        "help/genhtml.txt",
        "      --(no-)sort  Toggle sorting\n",
        &mut options,
    );
    options.sort_by(|left, right| left.canonical_name.cmp(&right.canonical_name));

    // Both entries start Unreviewed — the review overlay is the single source
    // of truth for classification.
    assert_eq!(options[0].canonical_name, "--no-sort");
    assert_eq!(options[0].review.classification, Classification::Unreviewed);
    assert_eq!(options[1].canonical_name, "--sort");
    assert_eq!(options[1].review.classification, Classification::Unreviewed);

    // --sort is not parser-defined (only appears in help).
    assert!(
        options[1]
            .review
            .source_references
            .iter()
            .all(|source| source.kind != SourceKind::ParserDefinition)
    );
    // Mechanical extraction does not author review output; the identity-bound
    // Oracle audit map records the expected ambiguous resolution.
    assert!(options[1].profile_parser_resolution.is_none());
    assert_eq!(
        expected_generated_token_resolutions()["command.genhtml.option.sort"],
        (ObservedAcceptance::RejectedAmbiguous, None)
    );
}

#[test]
fn generated_token_observations_distinguish_resolution_outcomes() {
    let expected = expected_generated_token_resolutions();
    let accepted = &expected["command.genhtml.option.diff"];
    assert_eq!(
        accepted,
        &(
            ObservedAcceptance::AcceptedUniqueAbbreviation,
            Some("command.genhtml.option.diff-file".to_owned()),
        )
    );
    assert_eq!(
        expected["command.genhtml.option.fail"].0,
        ObservedAcceptance::RejectedAmbiguous
    );
    assert_eq!(
        expected["command.lcov.option.path"].0,
        ObservedAcceptance::RejectedUnknown
    );
    assert!(!expected.contains_key("command.lcov.option.help"));
    assert_eq!(expected.len(), 41);
}

#[test]
fn parses_definition_aliases_and_expands_no_forms() {
    let entries = extract_help_options(
        "lcov",
        "help/lcov.txt",
        "prose mentions --not-public\n  -h, --help        Show help\n      --(no-)checksum  Toggle\n",
    );

    assert_eq!(entries.len(), 3);
    assert_eq!(entries[0].canonical_name, "--checksum");
    assert!(entries[0].aliases.is_empty());
    assert_eq!(entries[0].review.classification, Classification::Public);
    assert_eq!(entries[0].review.source_references[0].line, 3);
    assert_eq!(entries[1].canonical_name, "--help");
    assert_eq!(entries[1].aliases, ["-h"]);
    assert_eq!(entries[2].canonical_name, "--no-checksum");
    assert!(entries[2].aliases.is_empty());
}

#[test]
fn ignores_deeply_indented_example_continuations_as_help_definitions() {
    let entries = extract_help_options(
        "llvm2lcov",
        "help/llvm2lcov.txt",
        "  --mcdc-coverage:\n       --mcdc-coverage --branch-coverage input.json\n",
    );

    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].canonical_name, "--mcdc-coverage");
    assert!(entries[0].aliases.is_empty());
    assert_eq!(entries[0].review.source_references[0].line, 1);
}

#[test]
fn ignores_unindented_prose_continuations_as_help_definitions() {
    let entries = extract_help_options(
        "perl2lcov",
        "help/perl2lcov.txt",
        "suite supports --substitute,\n--exclude, etc.), the tool options are:\n\n  --output filename:\n",
    );

    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].canonical_name, "--output");
    assert_eq!(entries[0].review.source_references[0].line, 4);
}

#[test]
fn parses_argparse_aliases_without_treating_metavars_as_options() {
    let entries = extract_help_options(
        "xml2lcov",
        "help/xml2lcov.txt",
        "options:\n  -t TEST, --test-name TEST, --testname TEST\n  -e PATTERNS, --exclude PATTERNS\n",
    );

    assert_eq!(entries[0].canonical_name, "--exclude");
    assert_eq!(entries[0].aliases, ["-e"]);
    assert_eq!(entries[1].canonical_name, "--test-name");
    assert_eq!(entries[1].aliases, ["-t", "--testname"]);
}

#[test]
fn retains_manual_only_candidates_as_unreviewed_with_exact_lines() {
    let mut entries = extract_help_options(
        "lcov",
        "help/lcov.txt",
        "  --(no-)checksum  Toggle checksums\n",
    );
    merge_manual_candidates(
        "lcov",
        "docs/man/lcov.rst",
        "Use --checksum here.\nCandidate --manual-only and --manual-only.\n",
        &mut entries,
    );
    entries.sort_by(|left, right| left.canonical_name.cmp(&right.canonical_name));

    let checksum = &entries[0];
    assert_eq!(checksum.review.classification, Classification::Public);
    assert!(
        checksum
            .review
            .source_references
            .iter()
            .any(|source| { source.kind == SourceKind::ManualCandidate && source.line == 1 })
    );

    let manual = &entries[1];
    assert_eq!(manual.canonical_name, "--manual-only");
    assert_eq!(manual.review.classification, Classification::Unreviewed);
    assert_eq!(manual.review.source_references.len(), 1);
    assert_eq!(manual.review.source_references[0].line, 2);
}

#[test]
fn scans_quoted_manual_candidates_and_rejects_triple_dash_tokens() {
    assert_eq!(
        extract_long_options("Use '--quoted' and `--(no-)toggle`; reject ---bad."),
        BTreeSet::from([
            "--no-toggle".to_owned(),
            "--quoted".to_owned(),
            "--toggle".to_owned(),
        ])
    );
}

#[test]
fn parses_argparse_positional_definitions() {
    let input = "usage: py2lcov [-h] [inputs ...]\n\npositional arguments:\n  inputs      input coverage files\n              continued description\n\noptions:\n  -h, --help  show help\n";

    let entries = extract_positional_arguments("py2lcov", "help/py2lcov.txt", input);

    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "inputs");
    assert_eq!(entries[0].review.classification, Classification::Public);
    assert_eq!(
        entries[0].review.source_references[0].kind,
        SourceKind::HelpDefinition
    );
    assert_eq!(entries[0].review.source_references[0].line, 4);
}

#[test]
fn parses_classic_usage_positionals_in_order_and_deduplicates_repeat_notation() {
    let entries = extract_positional_arguments(
        "llvm2lcov",
        "help/llvm2lcov.txt",
        "Usage: llvm2lcov [OPTIONS] json_file [json_file ...]\nDescription\n",
    );

    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "json_file");
    assert_eq!(
        entries[0].review.source_references[0].kind,
        SourceKind::HelpUsage
    );
}

#[test]
fn config_candidates_remain_unreviewed_and_keep_all_source_lines() {
    let entries = extract_config_entries(
        "branch_coverage = 1\n# branch_coverage = 0\n# prose = candidate\n# 9invalid = 1\n",
        "lcovrc",
    );

    assert_eq!(entries.len(), 2);
    assert_eq!(entries[0].name, "branch_coverage");
    assert_eq!(entries[0].review.classification, Classification::Unreviewed);
    assert_eq!(entries[0].review.source_references.len(), 2);
    assert_eq!(entries[1].name, "prose");
}

#[test]
fn serialized_entries_keep_behavior_contract_fields_out_of_inventory() {
    let entries = extract_help_options("lcov", "help/lcov.txt", "  --help  Show help\n");
    let value = serde_json::to_value(&entries[0]).expect("entry must serialize");

    assert_eq!(value["classification"], "public");
    assert_eq!(value["applicability"], "unreviewed");
    for field in [
        "behavior_groups",
        "interaction_groups",
        "planned_cases",
        "implementation_status",
        "evidence",
    ] {
        assert!(
            value.get(field).is_none(),
            "unexpected inventory field {field}"
        );
    }
}

#[test]
fn extracts_continued_makefile_words() {
    let input = concat!(
        "OTHER = ignored\n",
        "EXES = \\",
        "\n",
        "  lcov genhtml \\",
        "\n",
        "  geninfo\n",
        "NEXT = value\n",
    );

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
fn commit_guard_rejects_every_other_revision() {
    let error = verify_commit_value("0000000000000000000000000000000000000000")
        .expect_err("wrong revision must fail");

    assert!(error.to_string().contains(UPSTREAM_COMMIT));
}

#[test]
fn clean_tree_guard_rejects_tracked_and_untracked_changes() {
    verify_status_value("").expect("clean status must pass");
    let error = verify_status_value(" M docs/man/lcov.rst\n?? scripts/untracked\n")
        .expect_err("dirty status must fail");

    assert!(error.to_string().contains("dirty"));
}

#[test]
fn recognizes_upstream_backup_names() {
    assert!(is_backup_name("gitdiff.bak"));
    assert!(is_backup_name("#gitdiff#"));
    assert!(!is_backup_name("gitdiff.pm"));
}
