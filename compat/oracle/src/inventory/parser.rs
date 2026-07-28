use super::{
    Applicability, AutoAbbrev, Bundling, Classification, NamedEntry, OptionEntry, OptionOrdering,
    ParserFamily, ParserPolicy, PlusPrefixBehavior, PosixlyCorrectEffect, SourceKind,
    SourceReference, named_entry, option_id, positional_id, unreviewed_metadata,
};
// Classification::Internal is no longer used after removing hardcoded parser
// classifications; the review overlay is the single source of truth.
use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::path::Path;

pub(super) fn parser_policy(
    upstream_root: &Path,
    command: &str,
) -> Result<ParserPolicy, Box<dyn Error>> {
    let parser_source = |path: &str, marker: &str| -> Result<SourceReference, Box<dyn Error>> {
        let input = fs::read_to_string(upstream_root.join(path))?;
        Ok(SourceReference {
            kind: SourceKind::ParserPolicy,
            path: path.to_owned(),
            line: find_line_containing(&input, marker)?,
        })
    };

    let policy = match command {
        "lcov" | "genhtml" | "geninfo" | "perl2lcov" | "llvm2lcov" => {
            let command_marker = match command {
                "lcov" => "!lcovutil::parseOptions",
                "genhtml" => "!lcovutil::parseOptions",
                "geninfo" => "if (!lcovutil::parseOptions",
                "perl2lcov" => "if (!lcovutil::parseOptions",
                "llvm2lcov" => "if (!lcovutil::parseOptions",
                _ => unreachable!(),
            };
            let mut source_references = vec![
                parser_source(&format!("bin/{command}"), command_marker)?,
                parser_source(
                    "lib/lcovutil.pm",
                    "Getopt::Long::Configure(\"pass_through\", \"no_auto_abbrev\")",
                )?,
                parser_source("lib/lcovutil.pm", "Getopt::Long::Configure(\"default\")")?,
                parser_source("lib/lcovutil.pm", "if (!GetOptions(%options))")?,
                parser_source(
                    "lib/lcovutil.pm",
                    "foreach my $d (['--config-file', scalar(@unsupported_config)]",
                )?,
            ];
            source_references.sort();
            ParserPolicy {
                family: ParserFamily::SharedGetoptLong,
                auto_abbrev: AutoAbbrev::UniquePrefix,
                case_sensitive: Some(false),
                accepted_long_prefixes: vec!["--", "-"],
                plus_prefix_behavior: PlusPrefixBehavior::Option,
                option_ordering: OptionOrdering::Permute,
                bundling: Bundling::Disabled,
                posixly_correct_effect: PosixlyCorrectEffect::DisableAutoAbbrevAndPlusRequireOrder,
                exact_only_options: vec!["--config-file", "--rc"],
                source_references,
            }
        }
        "genpng" | "gendesc" => {
            let marker = if command == "genpng" {
                "if (!GetOptions(\"tab-size=i\""
            } else {
                "if (!GetOptions(\"output-filename=s\""
            };
            ParserPolicy {
                family: ParserFamily::DirectGetoptLong,
                auto_abbrev: AutoAbbrev::UniquePrefix,
                case_sensitive: Some(false),
                accepted_long_prefixes: vec!["--", "-"],
                plus_prefix_behavior: PlusPrefixBehavior::Option,
                option_ordering: OptionOrdering::Permute,
                bundling: Bundling::Disabled,
                posixly_correct_effect: PosixlyCorrectEffect::DisableAutoAbbrevAndPlusRequireOrder,
                exact_only_options: Vec::new(),
                source_references: vec![parser_source(&format!("bin/{command}"), marker)?],
            }
        }
        "py2lcov" | "xml2lcov" => ParserPolicy {
            family: ParserFamily::Argparse,
            auto_abbrev: AutoAbbrev::UniquePrefix,
            case_sensitive: Some(true),
            accepted_long_prefixes: vec!["--"],
            plus_prefix_behavior: PlusPrefixBehavior::Positional,
            option_ordering: OptionOrdering::ArgparseParseArgs,
            bundling: Bundling::ArgparseShortClusters,
            posixly_correct_effect: PosixlyCorrectEffect::None,
            exact_only_options: Vec::new(),
            source_references: vec![
                parser_source(
                    &format!("bin/{command}"),
                    "parser = argparse.ArgumentParser(",
                )?,
                parser_source(&format!("bin/{command}"), "args = parser.parse_args()")?,
            ],
        },
        "xml2lcovutil.py" => ParserPolicy {
            family: ParserFamily::None,
            auto_abbrev: AutoAbbrev::NotApplicable,
            case_sensitive: None,
            accepted_long_prefixes: Vec::new(),
            plus_prefix_behavior: PlusPrefixBehavior::Ignored,
            option_ordering: OptionOrdering::Ignored,
            bundling: Bundling::NotApplicable,
            posixly_correct_effect: PosixlyCorrectEffect::NotApplicable,
            exact_only_options: Vec::new(),
            source_references: vec![SourceReference {
                kind: SourceKind::CommandImplementation,
                path: "bin/xml2lcovutil.py".to_owned(),
                line: 1,
            }],
        },
        _ => return Err(format!("unknown installed command {command}").into()),
    };
    Ok(policy)
}

#[derive(Clone, Copy)]
struct PerlOptionSource {
    path: &'static str,
    start_marker: &'static str,
    end_marker: &'static str,
}

type LocatedOptionForms = (Vec<String>, usize);

const COMMON_PERL_OPTIONS: PerlOptionSource = PerlOptionSource {
    path: "lib/lcovutil.pm",
    start_marker: "our %argCommon = (",
    end_marker: "'sort-input'        => \\$lcovutil::sort_inputs,);",
};

pub(super) fn expected_parser_option_count(command: &str) -> Option<usize> {
    match command {
        "lcov" => Some(77),
        "genhtml" => Some(95),
        "geninfo" => Some(60),
        "genpng" => Some(6),
        "gendesc" => Some(3),
        "perl2lcov" => Some(46),
        "py2lcov" => Some(12),
        "xml2lcov" => Some(8),
        "xml2lcovutil.py" => Some(0),
        "llvm2lcov" => Some(46),
        _ => None,
    }
}

pub(super) fn extract_parser_options(
    upstream_root: &Path,
    command: &str,
) -> Result<Vec<OptionEntry>, Box<dyn Error>> {
    let sources: &[PerlOptionSource] = match command {
        "lcov" => &[
            COMMON_PERL_OPTIONS,
            PerlOptionSource {
                path: "bin/lcov",
                start_marker: "my %lcov_options = (",
                end_marker: "'subtract=s'  => \\@difference,);",
            },
        ],
        "genhtml" => &[
            COMMON_PERL_OPTIONS,
            PerlOptionSource {
                path: "bin/genhtml",
                start_marker: "my %genhtml_options = (",
                end_marker: "'validate'          => \\$validateHTML,);",
            },
        ],
        "geninfo" => &[
            COMMON_PERL_OPTIONS,
            PerlOptionSource {
                path: "bin/geninfo",
                start_marker: "my %geninfo_opts = (",
                end_marker: "'large-file=s'        => \\@large_files);",
            },
        ],
        "perl2lcov" => &[
            COMMON_PERL_OPTIONS,
            PerlOptionSource {
                path: "bin/perl2lcov",
                start_marker: "our %options = (",
                end_marker: "'output|o=s' => \\$output_file,);",
            },
        ],
        "llvm2lcov" => &[
            COMMON_PERL_OPTIONS,
            PerlOptionSource {
                path: "bin/llvm2lcov",
                start_marker: "my %opts = (",
                end_marker: "'output-filename|o=s' => \\$output_filename,);",
            },
        ],
        "genpng" => &[PerlOptionSource {
            path: "bin/genpng",
            start_marker: "if (!GetOptions(",
            end_marker: ")) {",
        }],
        "gendesc" => &[PerlOptionSource {
            path: "bin/gendesc",
            start_marker: "if (!GetOptions(",
            end_marker: ")) {",
        }],
        "py2lcov" | "xml2lcov" | "xml2lcovutil.py" => &[],
        _ => return Err(format!("unknown installed command {command}").into()),
    };

    let mut entries = BTreeMap::new();
    for source in sources {
        let input = fs::read_to_string(upstream_root.join(source.path))?;
        for (specification, line) in
            extract_perl_option_specifications(&input, source.start_marker, source.end_marker)?
        {
            let entry = parser_option_entry(command, specification, source.path, line);
            if entries
                .insert(entry.canonical_name.clone(), entry)
                .is_some()
            {
                return Err(format!("duplicate parser option for {command}").into());
            }
        }
    }

    if matches!(command, "py2lcov" | "xml2lcov") {
        let path = format!("bin/{command}");
        let input = fs::read_to_string(upstream_root.join(&path))?;
        for (forms, line) in extract_argparse_option_definitions(&input)? {
            let canonical_name = forms
                .iter()
                .find(|form| form.starts_with("--"))
                .unwrap_or(&forms[0])
                .clone();
            let aliases = forms
                .into_iter()
                .filter(|form| form != &canonical_name)
                .collect();
            entries.insert(
                canonical_name.clone(),
                OptionEntry {
                    id: option_id(command, &canonical_name),
                    canonical_name,
                    aliases,
                    profile_parser_resolution: None,
                    review: unreviewed_metadata(
                        Classification::Unreviewed,
                        vec![SourceReference {
                            kind: SourceKind::ParserDefinition,
                            path: path.clone(),
                            line,
                        }],
                    ),
                },
            );
        }

        let parser_line = find_line_containing(&input, "parser = argparse.ArgumentParser(")?;
        let canonical_name = "--help".to_owned();
        entries.insert(
            canonical_name.clone(),
            OptionEntry {
                id: option_id(command, &canonical_name),
                canonical_name,
                aliases: vec!["-h".to_owned()],
                profile_parser_resolution: None,
                review: unreviewed_metadata(
                    Classification::Unreviewed,
                    vec![SourceReference {
                        kind: SourceKind::ParserDefinition,
                        path,
                        line: parser_line,
                    }],
                ),
            },
        );
    }

    Ok(entries.into_values().collect())
}

pub(super) fn extract_perl_option_specifications(
    input: &str,
    start_marker: &str,
    end_marker: &str,
) -> Result<Vec<(String, usize)>, Box<dyn Error>> {
    let mut active = false;
    let mut found_end = false;
    let mut specifications = Vec::new();
    for (offset, line) in input.lines().enumerate() {
        if !active {
            if !line.contains(start_marker) {
                continue;
            }
            active = true;
        }

        if let Some(specification) = first_quoted_hash_key(line) {
            specifications.push((specification, offset + 1));
        }
        if line.contains(end_marker) {
            found_end = true;
            break;
        }
    }
    if !active || !found_end {
        return Err(format!(
            "could not isolate parser definitions from {start_marker:?} through {end_marker:?}"
        )
        .into());
    }
    Ok(specifications)
}

fn first_quoted_hash_key(line: &str) -> Option<String> {
    let (quote_index, quote) = line
        .char_indices()
        .find(|(_, character)| matches!(character, '\'' | '"'))?;
    let rest = &line[quote_index + quote.len_utf8()..];
    let end = rest.find(quote)?;
    rest[end + quote.len_utf8()..]
        .contains("=>")
        .then(|| rest[..end].to_owned())
}

pub(super) fn parser_option_entry(
    command: &str,
    specification: String,
    path: &str,
    line: usize,
) -> OptionEntry {
    let forms = perl_option_forms(&specification);
    let canonical_name = forms[0].clone();
    // All options start Unreviewed; the review overlay sets final classification.
    OptionEntry {
        id: option_id(command, &canonical_name),
        canonical_name,
        aliases: forms.into_iter().skip(1).collect(),
        profile_parser_resolution: None,
        review: unreviewed_metadata(
            Classification::Unreviewed,
            vec![SourceReference {
                kind: SourceKind::ParserDefinition,
                path: path.to_owned(),
                line,
            }],
        ),
    }
}

pub(super) fn perl_option_forms(specification: &str) -> Vec<String> {
    let names = specification
        .split_once(['=', ':'])
        .map_or(specification, |(names, _)| names);
    names
        .split('|')
        .map(|name| name.trim_end_matches(['+', '!']))
        .map(|name| {
            if name.len() == 1 {
                format!("-{name}")
            } else {
                format!("--{name}")
            }
        })
        .collect()
}

pub(super) fn extract_argparse_option_definitions(
    input: &str,
) -> Result<Vec<LocatedOptionForms>, Box<dyn Error>> {
    let mut definitions = Vec::new();
    for (offset, line) in input.lines().enumerate() {
        let Some(arguments) = line
            .split_once("parser.add_argument(")
            .map(|(_, rest)| rest)
        else {
            continue;
        };
        let forms = extract_quoted_strings(arguments)
            .into_iter()
            .take_while(|value| value.starts_with('-'))
            .collect::<Vec<_>>();
        if !forms.is_empty() {
            definitions.push((forms, offset + 1));
        }
    }
    if definitions.is_empty() {
        return Err("argparse source contained no option definitions".into());
    }
    Ok(definitions)
}

fn extract_quoted_strings(input: &str) -> Vec<String> {
    let mut values = Vec::new();
    let mut remainder = input;
    while let Some((index, quote)) = remainder
        .char_indices()
        .find(|(_, character)| matches!(character, '\'' | '"'))
    {
        remainder = &remainder[index + quote.len_utf8()..];
        let Some(end) = remainder.find(quote) else {
            break;
        };
        values.push(remainder[..end].to_owned());
        remainder = &remainder[end + quote.len_utf8()..];
    }
    values
}

pub(super) fn reviewed_positional_arguments(
    upstream_root: &Path,
    command: &str,
) -> Result<Vec<NamedEntry>, Box<dyn Error>> {
    let definition = match command {
        "lcov" => Some((
            "operation_operands",
            "bin/lcov",
            "# Mode flags that consume @ARGV as their input list",
            Applicability::Conditional,
        )),
        "genhtml" => Some((
            "tracefile_pattern",
            "bin/genhtml",
            "@info_filenames = AggregateTraces::find_from_glob(@ARGV);",
            Applicability::AllSupportedEnvironments,
        )),
        "geninfo" => Some((
            "directory",
            "bin/geninfo",
            "@data_directory = @ARGV;",
            Applicability::AllSupportedEnvironments,
        )),
        "genpng" => Some((
            "sourcefile",
            "bin/genpng",
            "$filename = $ARGV[0];",
            Applicability::AllSupportedEnvironments,
        )),
        "gendesc" => Some((
            "inputfile",
            "bin/gendesc",
            "$input_filename = $ARGV[0];",
            Applicability::AllSupportedEnvironments,
        )),
        "perl2lcov" => Some((
            "cover_db",
            "bin/perl2lcov",
            "foreach my $db_path (@ARGV) {",
            Applicability::AllSupportedEnvironments,
        )),
        "py2lcov" => Some((
            "inputs",
            "bin/py2lcov",
            "parser.add_argument('inputs', nargs='*',",
            Applicability::AllSupportedEnvironments,
        )),
        "xml2lcov" => Some((
            "inputs",
            "bin/xml2lcov",
            "parser.add_argument('inputs', nargs='*',",
            Applicability::AllSupportedEnvironments,
        )),
        "llvm2lcov" => Some((
            "json_file",
            "bin/llvm2lcov",
            "my $info = parse($testname, @ARGV);",
            Applicability::AllSupportedEnvironments,
        )),
        "xml2lcovutil.py" => None,
        _ => return Err(format!("unknown installed command {command}").into()),
    };

    let Some((name, path, marker, applicability)) = definition else {
        return Ok(Vec::new());
    };
    let input = fs::read_to_string(upstream_root.join(path))?;
    let line = find_line_containing(&input, marker)?;
    let mut entry = named_entry(
        positional_id(command, name),
        name.to_owned(),
        Classification::Public,
        SourceReference {
            kind: SourceKind::ParserDefinition,
            path: path.to_owned(),
            line,
        },
    );
    entry.review.applicability = applicability;
    Ok(vec![entry])
}

fn find_line_containing(input: &str, marker: &str) -> Result<usize, Box<dyn Error>> {
    input
        .lines()
        .position(|line| line.contains(marker))
        .map(|offset| offset + 1)
        .ok_or_else(|| format!("source marker not found: {marker}").into())
}
