mod candidate;
mod config;
mod install;
mod parser;
pub(crate) mod review;
#[cfg(test)]
mod tests;

pub use candidate::extract_long_options;
pub use config::extract_config_keys;
pub use install::extract_makefile_words;

use crate::{UPSTREAM_COMMIT, UPSTREAM_RELEASE};
use candidate::{merge_help_candidates, merge_manual_candidates};
use config::{extract_config_entries, extract_registered_config_entries};
use install::{assignment_line, find_manual, installed_support_scripts, verify_upstream_checkout};
use parser::{
    expected_parser_option_count, extract_parser_options, parser_policy,
    reviewed_positional_arguments,
};
use review::{
    ReviewOverlay, ReviewedEntry, unmatched_extracted_entries, unmatched_overlay_entries,
};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs;
use std::path::Path;

const INVENTORY_SCHEMA_VERSION: u32 = 2;

/// Generated, reviewable inventory of the pinned upstream surface.
#[derive(Debug, Serialize)]
pub struct Inventory {
    pub schema_version: u32,
    pub upstream_release: &'static str,
    pub upstream_commit: &'static str,
    pub commands: Vec<CommandInventory>,
    pub config_keys: Vec<NamedEntry>,
    pub support_scripts: Vec<NamedEntry>,
    pub totals: InventoryTotals,
}

/// Candidate CLI surface for one installed command.
#[derive(Debug, Serialize)]
pub struct CommandInventory {
    pub name: String,
    pub help_snapshot: Option<String>,
    pub manual: Option<String>,
    pub parser_policy: ParserPolicy,
    pub options: Vec<OptionEntry>,
    pub positional_arguments: Vec<NamedEntry>,
}

/// One option definition. Aliases are forms accepted by the same definition.
#[derive(Debug, Serialize)]
pub struct OptionEntry {
    pub id: String,
    pub canonical_name: String,
    pub aliases: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub profile_parser_resolution: Option<ProfileParserResolution>,
    #[serde(flatten)]
    pub review: ReviewMetadata,
}

/// Effective command-line parser behavior at the pinned upstream revision.
#[derive(Debug, Serialize)]
pub struct ParserPolicy {
    pub family: ParserFamily,
    pub auto_abbrev: AutoAbbrev,
    pub case_sensitive: Option<bool>,
    pub accepted_long_prefixes: Vec<&'static str>,
    pub plus_prefix_behavior: PlusPrefixBehavior,
    pub option_ordering: OptionOrdering,
    pub bundling: Bundling,
    pub posixly_correct_effect: PosixlyCorrectEffect,
    pub exact_only_options: Vec<&'static str>,
    pub source_references: Vec<SourceReference>,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ParserFamily {
    SharedGetoptLong,
    DirectGetoptLong,
    Argparse,
    None,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AutoAbbrev {
    UniquePrefix,
    NotApplicable,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PlusPrefixBehavior {
    Option,
    Positional,
    Ignored,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OptionOrdering {
    Permute,
    ArgparseParseArgs,
    Ignored,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Bundling {
    Disabled,
    ArgparseShortClusters,
    NotApplicable,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PosixlyCorrectEffect {
    DisableAutoAbbrevAndPlusRequireOrder,
    None,
    NotApplicable,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize)]
pub struct ObservedParserResolution {
    pub acceptance: ObservedAcceptance,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,
}

/// Profile-dependent parser resolution for one token.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct ProfileParserResolution {
    /// Default Getopt::Long / argparse profile.
    pub default_profile: ObservedParserResolution,
    /// POSIXLY_CORRECT profile. It is explicit even when unchanged.
    pub posix_profile: ObservedParserResolution,
}

#[derive(Debug, Clone, Copy, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ObservedAcceptance {
    AcceptedExact,
    AcceptedUniqueAbbreviation,
    RejectedAmbiguous,
    RejectedUnknown,
}

/// An inventory entry with a single upstream name.
#[derive(Debug, Serialize)]
pub struct NamedEntry {
    pub id: String,
    pub name: String,
    #[serde(flatten)]
    pub review: ReviewMetadata,
}

/// Review state shared by every candidate surface.
#[derive(Debug, Serialize)]
pub struct ReviewMetadata {
    pub review_status: ReviewDecision,
    pub classification: Classification,
    pub source_references: Vec<SourceReference>,
    pub dependencies: Vec<String>,
    pub applicability: Applicability,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
}

#[derive(Debug, Clone, Copy, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ReviewDecision {
    Reviewed,
    Unreviewed,
}

#[derive(Debug, Clone, Copy, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Classification {
    Public,
    Internal,
    DuplicateAlias,
    GeneratedToken,
    NotApplicable,
    Unreviewed,
}

#[derive(Debug, Clone, Copy, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceKind {
    ParserDefinition,
    ParserPolicy,
    CommandImplementation,
    HelpDefinition,
    HelpUsage,
    ManualCandidate,
    ConfigDefinition,
    SupportScript,
    InstallManifest,
}

#[derive(Debug, Clone, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub struct SourceReference {
    pub kind: SourceKind,
    pub path: String,
    pub line: usize,
}

impl SourceReference {
    /// Return the serialized kind string for cross-module matching.
    pub(crate) fn kind_str(&self) -> &'static str {
        match self.kind {
            SourceKind::ParserDefinition => "parser_definition",
            SourceKind::ParserPolicy => "parser_policy",
            SourceKind::CommandImplementation => "command_implementation",
            SourceKind::HelpDefinition => "help_definition",
            SourceKind::HelpUsage => "help_usage",
            SourceKind::ManualCandidate => "manual_candidate",
            SourceKind::ConfigDefinition => "config_definition",
            SourceKind::SupportScript => "support_script",
            SourceKind::InstallManifest => "install_manifest",
        }
    }
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Applicability {
    Unreviewed,
    AllSupportedEnvironments,
    Conditional,
    NotApplicable,
}

/// Counts used to detect accidental inventory shrinkage without implying review.
#[derive(Debug, Serialize)]
pub struct InventoryTotals {
    pub installed_commands: usize,
    pub command_options: usize,
    pub parser_command_options: usize,
    pub public_command_options: usize,
    pub unreviewed_command_options: usize,
    pub positional_arguments: usize,
    pub config_keys: usize,
    pub support_scripts: usize,
}

/// Generate candidate entries from an exact upstream checkout and captured help,
/// then apply the review overlay to produce the final reviewed inventory.
///
/// The overlay lives in `review_dir` as a set of domain-sharded JSON files.
/// It is applied after mechanical extraction and before totals computation.
/// Every extracted entry must have an overlay match and vice versa; the
/// function fails closed on any mismatch.
pub fn generate_inventory(
    upstream_root: &Path,
    help_dir: &Path,
    review_dir: &Path,
) -> Result<Inventory, Box<dyn Error>> {
    verify_upstream_checkout(upstream_root)?;

    let makefile = fs::read_to_string(upstream_root.join("Makefile"))?;
    let command_names = extract_makefile_words(&makefile, "EXES")
        .ok_or("upstream Makefile does not define EXES")?;
    let install_manifest_line =
        assignment_line(&makefile, "SCRIPTS").ok_or("upstream Makefile does not define SCRIPTS")?;

    // Mechanical extraction — all entries start Unreviewed.
    let mut commands = Vec::with_capacity(command_names.len());
    for name in command_names {
        commands.push(generate_command(upstream_root, help_dir, name)?);
    }

    let config_template = fs::read_to_string(upstream_root.join("lcovrc"))?;
    let mut config_keys = extract_config_entries(&config_template, "lcovrc");

    // Also extract config keys registered in source code but absent from the template.
    // Merge sources from registered entries into template entries so that keys
    // present in both places have all their source references.
    let registered = extract_registered_config_entries(upstream_root)?;
    for reg in registered {
        if let Some(existing) = config_keys.iter_mut().find(|k| k.id == reg.id) {
            // Add registration sources to existing template entry.
            for src in &reg.review.source_references {
                push_source(&mut existing.review.source_references, src.clone());
            }
        } else {
            config_keys.push(reg);
        }
    }
    config_keys.sort_by(|a, b| a.name.cmp(&b.name));

    let mut support_scripts =
        installed_support_scripts(&upstream_root.join("scripts"), install_manifest_line)?;

    // ---- apply review overlay ----
    let overlay = ReviewOverlay::load(review_dir, UPSTREAM_RELEASE, UPSTREAM_COMMIT)?;

    apply_option_overlay(&mut commands, &overlay.option_entries)?;
    apply_named_overlay("config", &mut config_keys, &overlay.config_entries)?;
    apply_named_overlay(
        "support_script",
        &mut support_scripts,
        &overlay.support_script_entries,
    )?;

    // Positional arguments live on commands.
    {
        let mut all_pa = Vec::new();
        for cmd in &mut commands {
            all_pa.append(&mut cmd.positional_arguments);
        }
        apply_named_overlay(
            "positional_argument",
            &mut all_pa,
            &overlay.positional_argument_entries,
        )?;
        // Put them back.
        for cmd in &mut commands {
            // Take the positional args that belong to this command back.
            let prefix = format!("command.{}.positional.", slug(&cmd.name));
            let (mine, rest): (Vec<_>, Vec<_>) = all_pa
                .into_iter()
                .partition(|pa| pa.id.starts_with(&prefix));
            cmd.positional_arguments = mine;
            all_pa = rest;
        }
    }

    // ---- compute totals from reviewed entries ----
    let command_options = commands.iter().map(|command| command.options.len()).sum();
    let parser_command_options = commands
        .iter()
        .flat_map(|command| &command.options)
        .filter(|option| {
            option
                .review
                .source_references
                .iter()
                .any(|source| source.kind == SourceKind::ParserDefinition)
        })
        .count();
    let public_command_options = commands
        .iter()
        .flat_map(|command| &command.options)
        .filter(|option| {
            option.review.review_status == ReviewDecision::Reviewed
                && option.review.classification == Classification::Public
        })
        .count();
    let unreviewed_command_options = commands
        .iter()
        .flat_map(|command| &command.options)
        .filter(|option| option.review.review_status == ReviewDecision::Unreviewed)
        .count();
    let positional_arguments = commands
        .iter()
        .map(|command| command.positional_arguments.len())
        .sum();
    verify_profile_resolution_contract(&commands)?;

    Ok(Inventory {
        schema_version: INVENTORY_SCHEMA_VERSION,
        upstream_release: UPSTREAM_RELEASE,
        upstream_commit: UPSTREAM_COMMIT,
        totals: InventoryTotals {
            installed_commands: commands.len(),
            command_options,
            parser_command_options,
            public_command_options,
            unreviewed_command_options,
            positional_arguments,
            config_keys: config_keys.len(),
            support_scripts: support_scripts.len(),
        },
        commands,
        config_keys,
        support_scripts,
    })
}

/// Apply the review overlay to command option entries.
fn apply_option_overlay(
    commands: &mut [CommandInventory],
    overlay: &BTreeMap<String, ReviewedEntry>,
) -> Result<(), Box<dyn Error>> {
    let mut extracted_ids = BTreeSet::new();
    let mut failures = Vec::new();

    for cmd in commands.iter_mut() {
        for opt in cmd.options.iter_mut() {
            extracted_ids.insert(opt.id.clone());
            let sources: BTreeSet<(String, String, usize)> = opt
                .review
                .source_references
                .iter()
                .map(|s| (s.kind_str().to_owned(), s.path.clone(), s.line))
                .collect();
            let review_entry = overlay.get(&opt.id);
            let fs = review::verify_option_entry_match(
                &opt.id,
                &opt.canonical_name,
                &sources,
                &opt.aliases,
                review_entry,
            );
            failures.extend(fs);

            if let Some(re) = review_entry {
                // Set profile-dependent resolution from overlay.
                if let Some(ref obs) = re.profile_parser_resolution {
                    opt.profile_parser_resolution = Some(ProfileParserResolution {
                        default_profile: convert_profile_resolution(&obs.default_profile),
                        posix_profile: convert_profile_resolution(&obs.posix_profile),
                    });
                }
                apply_review_metadata(&mut opt.review, re);
            }
        }
    }

    if !failures.is_empty() {
        let msg = failures
            .iter()
            .map(|f| format!("  {f}"))
            .collect::<Vec<_>>()
            .join("\n");
        return Err(format!("option overlay assertion failures:\n{msg}").into());
    }

    let unmatched_ext = unmatched_extracted_entries(&extracted_ids, overlay);
    if !unmatched_ext.is_empty() {
        return Err(format!(
            "option overlay: {} entries have no overlay match: {unmatched_ext:?}",
            unmatched_ext.len()
        )
        .into());
    }
    let unmatched_ov = unmatched_overlay_entries(&extracted_ids, overlay);
    if !unmatched_ov.is_empty() {
        return Err(format!(
            "option overlay: {} overlay entries have no extracted match: {unmatched_ov:?}",
            unmatched_ov.len()
        )
        .into());
    }

    Ok(())
}

fn convert_profile_resolution(pr: &review::ProfileResolution) -> ObservedParserResolution {
    ObservedParserResolution {
        acceptance: match pr.acceptance {
            review::ObservedAcceptance::AcceptedExact => ObservedAcceptance::AcceptedExact,
            review::ObservedAcceptance::AcceptedUniqueAbbreviation => {
                ObservedAcceptance::AcceptedUniqueAbbreviation
            }
            review::ObservedAcceptance::RejectedAmbiguous => ObservedAcceptance::RejectedAmbiguous,
            review::ObservedAcceptance::RejectedUnknown => ObservedAcceptance::RejectedUnknown,
        },
        target: pr.target.clone(),
    }
}

fn apply_review_metadata(metadata: &mut ReviewMetadata, entry: &ReviewedEntry) {
    metadata.review_status = map_review_decision(entry.review_status);
    metadata.classification = map_entry_classification(entry.classification);
    metadata.applicability = map_entry_applicability(entry.applicability);
    metadata.dependencies.clone_from(&entry.dependencies);
    metadata.note.clone_from(&entry.note);
}

fn verify_profile_resolution_contract(commands: &[CommandInventory]) -> Result<(), Box<dyn Error>> {
    let expected = candidate::expected_generated_token_resolutions();
    let mut actual = BTreeMap::new();

    for command in commands {
        for option in &command.options {
            let parser_backed = option
                .review
                .source_references
                .iter()
                .any(|source| source.kind == SourceKind::ParserDefinition);
            let generated = option.review.classification == Classification::GeneratedToken;
            if generated == parser_backed {
                return Err(format!(
                    "{} generated-token classification disagrees with parser-definition presence",
                    option.id
                )
                .into());
            }
            if generated != option.profile_parser_resolution.is_some() {
                return Err(format!(
                    "{} generated-token classification disagrees with profile resolution",
                    option.id
                )
                .into());
            }
            let Some(resolution) = &option.profile_parser_resolution else {
                continue;
            };
            if resolution.posix_profile.acceptance != ObservedAcceptance::RejectedUnknown
                || resolution.posix_profile.target.is_some()
            {
                return Err(format!(
                    "{} POSIX profile must be explicitly rejected_unknown",
                    option.id
                )
                .into());
            }
            if let Some(target_id) = &resolution.default_profile.target {
                let target = command
                    .options
                    .iter()
                    .find(|candidate| candidate.id == *target_id)
                    .ok_or_else(|| {
                        format!(
                            "{} parser target {target_id} does not exist in command {}",
                            option.id, command.name
                        )
                    })?;
                if !target
                    .review
                    .source_references
                    .iter()
                    .any(|source| source.kind == SourceKind::ParserDefinition)
                {
                    return Err(format!(
                        "{} parser target {target_id} is not parser-backed",
                        option.id
                    )
                    .into());
                }
            }
            actual.insert(
                option.id.clone(),
                (
                    resolution.default_profile.acceptance,
                    resolution.default_profile.target.clone(),
                ),
            );
        }
    }

    if actual != expected {
        let only_expected = expected
            .keys()
            .filter(|id| !actual.contains_key(*id))
            .collect::<Vec<_>>();
        let only_actual = actual
            .keys()
            .filter(|id| !expected.contains_key(*id))
            .collect::<Vec<_>>();
        let mismatched = expected
            .iter()
            .filter_map(|(id, value)| {
                actual
                    .get(id)
                    .filter(|actual| *actual != value)
                    .map(|actual| (id, value, actual))
            })
            .collect::<Vec<_>>();
        return Err(format!(
            "profile parser resolution drift: only_expected={only_expected:?} only_actual={only_actual:?} mismatched={mismatched:?}"
        )
        .into());
    }
    Ok(())
}

/// Apply the review overlay to named entries (config keys, support scripts, positional args).
fn apply_named_overlay(
    domain: &str,
    entries: &mut [NamedEntry],
    overlay: &BTreeMap<String, ReviewedEntry>,
) -> Result<(), Box<dyn Error>> {
    let mut extracted_ids = BTreeSet::new();
    let mut failures = Vec::new();

    for entry in entries.iter_mut() {
        extracted_ids.insert(entry.id.clone());
        let sources: BTreeSet<(String, String, usize)> = entry
            .review
            .source_references
            .iter()
            .map(|s| (s.kind_str().to_owned(), s.path.clone(), s.line))
            .collect();
        let review_entry = overlay.get(&entry.id);
        let fs = review::verify_named_entry_match(&entry.id, &entry.name, &sources, review_entry);
        failures.extend(fs);

        if let Some(re) = review_entry {
            apply_review_metadata(&mut entry.review, re);
        }
    }

    if !failures.is_empty() {
        let msg = failures
            .iter()
            .map(|f| format!("  {f}"))
            .collect::<Vec<_>>()
            .join("\n");
        return Err(format!("{domain} overlay assertion failures:\n{msg}").into());
    }

    let unmatched_ext = unmatched_extracted_entries(&extracted_ids, overlay);
    if !unmatched_ext.is_empty() {
        return Err(format!(
            "{domain} overlay: {} extracted entries have no overlay match: {:?}",
            unmatched_ext.len(),
            unmatched_ext
        )
        .into());
    }
    let unmatched_ov = unmatched_overlay_entries(&extracted_ids, overlay);
    if !unmatched_ov.is_empty() {
        return Err(format!(
            "{domain} overlay: {} overlay entries have no extracted match: {:?}",
            unmatched_ov.len(),
            unmatched_ov
        )
        .into());
    }

    Ok(())
}

fn map_review_decision(status: review::ReviewStatus) -> ReviewDecision {
    match status {
        review::ReviewStatus::Reviewed => ReviewDecision::Reviewed,
        review::ReviewStatus::Unreviewed => ReviewDecision::Unreviewed,
    }
}

fn map_entry_classification(cls: review::EntryClassification) -> Classification {
    match cls {
        review::EntryClassification::Public => Classification::Public,
        review::EntryClassification::Internal => Classification::Internal,
        review::EntryClassification::DuplicateAlias => Classification::DuplicateAlias,
        review::EntryClassification::GeneratedToken => Classification::GeneratedToken,
        review::EntryClassification::NotApplicable => Classification::NotApplicable,
    }
}

fn map_entry_applicability(applicability: review::EntryApplicability) -> Applicability {
    match applicability {
        review::EntryApplicability::Unreviewed => Applicability::Unreviewed,
        review::EntryApplicability::AllSupportedEnvironments => {
            Applicability::AllSupportedEnvironments
        }
        review::EntryApplicability::Conditional => Applicability::Conditional,
        review::EntryApplicability::NotApplicable => Applicability::NotApplicable,
    }
}

fn generate_command(
    upstream_root: &Path,
    help_dir: &Path,
    name: String,
) -> Result<CommandInventory, Box<dyn Error>> {
    let help_path = help_dir.join(format!("{name}.txt"));
    let help_source = format!("help/{name}.txt");
    let help = help_path
        .is_file()
        .then(|| fs::read_to_string(&help_path))
        .transpose()?;
    let manual_path = find_manual(upstream_root, &name);
    let manual_source = manual_path
        .as_ref()
        .map(|path| relative_display(upstream_root, path));
    let manual = manual_path.as_ref().map(fs::read_to_string).transpose()?;

    let mut options = extract_parser_options(upstream_root, &name)?;
    let expected_parser_options = expected_parser_option_count(&name)
        .ok_or_else(|| format!("missing parser inventory expectation for {name}"))?;
    if options.len() != expected_parser_options {
        return Err(format!(
            "parser option count drift for {name}: expected {expected_parser_options}, found {}",
            options.len()
        )
        .into());
    }
    if let Some(contents) = help.as_deref() {
        merge_help_candidates(&name, &help_source, contents, &mut options);
    }
    if let (Some(source), Some(contents)) = (&manual_source, manual.as_deref()) {
        merge_manual_candidates(&name, source, contents, &mut options);
    }
    options.sort_by(|left, right| left.canonical_name.cmp(&right.canonical_name));

    let positional_arguments = reviewed_positional_arguments(upstream_root, &name)?;
    let parser_policy = parser_policy(upstream_root, &name)?;

    Ok(CommandInventory {
        name,
        help_snapshot: help.map(|_| help_source),
        manual: manual_source,
        parser_policy,
        options,
        positional_arguments,
    })
}

fn option_id(command: &str, name: &str) -> String {
    format!("command.{}.option.{}", slug(command), slug(name))
}

fn positional_id(command: &str, name: &str) -> String {
    format!("command.{}.positional.{}", slug(command), slug(name))
}

fn slug(value: &str) -> String {
    let mut result = String::new();
    let mut separator = false;
    for character in value.chars() {
        if character.is_ascii_alphanumeric() {
            if separator && !result.is_empty() {
                result.push('-');
            }
            result.push(character.to_ascii_lowercase());
            separator = false;
        } else {
            separator = true;
        }
    }
    result
}

fn named_entry(
    id: String,
    name: String,
    classification: Classification,
    source: SourceReference,
) -> NamedEntry {
    NamedEntry {
        id,
        name,
        review: unreviewed_metadata(classification, vec![source]),
    }
}

fn unreviewed_metadata(
    classification: Classification,
    mut source_references: Vec<SourceReference>,
) -> ReviewMetadata {
    source_references.sort();
    ReviewMetadata {
        review_status: ReviewDecision::Unreviewed,
        classification,
        source_references,
        dependencies: Vec::new(),
        applicability: Applicability::Unreviewed,
        note: None,
    }
}

fn push_source(references: &mut Vec<SourceReference>, source: SourceReference) {
    if !references.contains(&source) {
        references.push(source);
        references.sort();
    }
}

fn extend_unique(target: &mut Vec<String>, values: Vec<String>) {
    for value in values {
        if !target.contains(&value) {
            target.push(value);
        }
    }
}

fn relative_display(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .into_owned()
}
