//! Review overlay: separates human review decisions from mechanical extraction.
//!
//! Two independent fields:
//! * `review_status` — reviewed / unreviewed
//! * `classification` — public / internal / duplicate_alias / generated_token / not_applicable
//!
//! Behavior groups, interaction groups, planned cases, product evidence are NOT here.

use serde::{Deserialize, Deserializer, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs;
use std::path::Path;

// ── Shard types ────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ReviewShard {
    pub schema_version: u32,
    pub upstream_release: String,
    pub upstream_commit: String,
    pub domain: ReviewDomain,
    pub shard_index: usize,
    pub shard_count: usize,
    pub content_hash: String,
    pub reviewed_entries: Vec<ReviewedEntry>,
    #[serde(skip)]
    file_name: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
pub(crate) enum ReviewDomain {
    #[serde(rename = "option_entries")]
    Options,
    #[serde(rename = "config_entries")]
    Config,
    #[serde(rename = "support_script_entries")]
    SupportScripts,
    #[serde(rename = "positional_argument_entries")]
    PositionalArguments,
}

impl ReviewDomain {
    fn file_name(self, shard_index: usize) -> String {
        let stem = match self {
            Self::Options => "option-entries",
            Self::Config => "config-entries",
            Self::SupportScripts => "support-script-entries",
            Self::PositionalArguments => "positional-argument-entries",
        };
        format!("{stem}-{shard_index:02}.json")
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ReviewedEntry {
    pub id: String,
    pub review_status: ReviewStatus,
    pub classification: EntryClassification,
    pub applicability: EntryApplicability,
    pub dependencies: Vec<String>,
    pub generated_id_assertion: String,
    pub generated_source_assertions: Vec<SourceAssertion>,
    pub generated_canonical_name_assertion: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub aliases: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub profile_parser_resolution: Option<ProfileParserResolutionEntry>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null_string",
        skip_serializing_if = "Option::is_none"
    )]
    pub note: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ReviewStatus {
    Reviewed,
    Unreviewed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum EntryClassification {
    Public,
    Internal,
    DuplicateAlias,
    GeneratedToken,
    NotApplicable,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum EntryApplicability {
    Unreviewed,
    AllSupportedEnvironments,
    Conditional,
    NotApplicable,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SourceAssertion {
    pub kind: String,
    pub path: String,
    pub line: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProfileParserResolutionEntry {
    pub default_profile: ProfileResolution,
    pub posix_profile: ProfileResolution,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProfileResolution {
    pub acceptance: ObservedAcceptance,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ObservedAcceptance {
    AcceptedExact,
    AcceptedUniqueAbbreviation,
    RejectedAmbiguous,
    RejectedUnknown,
}

fn deserialize_optional_non_null_string<'de, D>(deserializer: D) -> Result<Option<String>, D::Error>
where
    D: Deserializer<'de>,
{
    String::deserialize(deserializer).map(Some)
}

// ── Overlay ─────────────────────────────────────────────────────────────────

#[derive(Debug)]
pub(crate) struct ReviewOverlay {
    pub option_entries: BTreeMap<String, ReviewedEntry>,
    pub config_entries: BTreeMap<String, ReviewedEntry>,
    pub support_script_entries: BTreeMap<String, ReviewedEntry>,
    pub positional_argument_entries: BTreeMap<String, ReviewedEntry>,
}

impl ReviewOverlay {
    pub(crate) fn load(
        review_dir: &Path,
        upstream_release: &str,
        upstream_commit: &str,
    ) -> Result<Self, Box<dyn Error>> {
        let shards = Self::read_all_shards(review_dir)?;
        if shards.is_empty() {
            return Err("review directory contains no shard files".into());
        }
        for s in &shards {
            if s.schema_version != 1 {
                return Err(format!(
                    "shard {:?}/{} bad schema_version {}",
                    s.domain, s.shard_index, s.schema_version
                )
                .into());
            }
            if s.upstream_release != upstream_release {
                return Err(format!(
                    "shard {:?}/{} release mismatch: {} != {upstream_release}",
                    s.domain, s.shard_index, s.upstream_release
                )
                .into());
            }
            if s.upstream_commit != upstream_commit {
                return Err(format!(
                    "shard {:?}/{} commit mismatch: {} != {upstream_commit}",
                    s.domain, s.shard_index, s.upstream_commit
                )
                .into());
            }
            s.validate()?;
            let actual = Self::compute_content_hash(&s.reviewed_entries);
            if actual != s.content_hash {
                return Err(format!(
                    "shard {:?}/{} hash mismatch: expected {}, computed {actual}",
                    s.domain, s.shard_index, s.content_hash
                )
                .into());
            }
        }
        let groups = Self::group_by_domain(&shards)?;
        Ok(Self {
            option_entries: Self::merge(&groups, ReviewDomain::Options, "option_entries")?,
            config_entries: Self::merge(&groups, ReviewDomain::Config, "config_entries")?,
            support_script_entries: Self::merge(
                &groups,
                ReviewDomain::SupportScripts,
                "support_script_entries",
            )?,
            positional_argument_entries: Self::merge(
                &groups,
                ReviewDomain::PositionalArguments,
                "positional_argument_entries",
            )?,
        })
    }

    fn read_all_shards(dir: &Path) -> Result<Vec<ReviewShard>, Box<dyn Error>> {
        let mut out = Vec::new();
        for e in fs::read_dir(dir)? {
            let e = e?;
            if !e.file_type()?.is_file() {
                continue;
            }
            let n = e.file_name();
            if !n.to_str().is_some_and(|s| s.ends_with(".json")) {
                return Err(
                    format!("unlisted file in review directory: {}", e.path().display()).into(),
                );
            }
            let raw = fs::read_to_string(e.path())?;
            let line_count = raw.lines().count();
            if line_count > 1_800 {
                return Err(format!(
                    "review shard {} has {line_count} lines; limit is 1800",
                    e.path().display()
                )
                .into());
            }
            let mut s: ReviewShard = serde_json::from_str(&raw)
                .map_err(|err| format!("{}: {err}", e.path().display()))?;
            s.file_name = n
                .into_string()
                .map_err(|_| "review shard filename is not valid UTF-8")?;
            out.push(s);
        }
        Ok(out)
    }

    pub(crate) fn compute_content_hash(entries: &[ReviewedEntry]) -> String {
        let v: serde_json::Value = serde_json::to_value(entries).unwrap();
        let canonical = serde_json::to_string(&v).unwrap();
        let mut h = Sha256::new();
        h.update(canonical.as_bytes());
        format!("sha256:{:x}", h.finalize())
    }

    fn group_by_domain(
        shards: &[ReviewShard],
    ) -> Result<BTreeMap<ReviewDomain, Vec<&ReviewShard>>, Box<dyn Error>> {
        let mut m: BTreeMap<ReviewDomain, Vec<&ReviewShard>> = BTreeMap::new();
        for s in shards {
            m.entry(s.domain).or_default().push(s);
        }
        for (d, g) in &m {
            let n = g[0].shard_count;
            if n == 0 {
                return Err(format!("{d:?} shard_count=0").into());
            }
            for s in g {
                if s.shard_count != n {
                    return Err(format!(
                        "{d:?}/{} reports shard_count {} != {n}",
                        s.shard_index, s.shard_count
                    )
                    .into());
                }
            }
            if g.len() != n {
                return Err(format!("{d:?} expects {n} shards, found {}", g.len()).into());
            }
            let idx: BTreeSet<usize> = g.iter().map(|s| s.shard_index).collect();
            let want: BTreeSet<usize> = (0..n).collect();
            if idx != want {
                return Err(format!("{d:?} indices {idx:?} != {want:?}").into());
            }
            let mut ordered = g.clone();
            ordered.sort_by_key(|shard| shard.shard_index);
            let ids = ordered
                .iter()
                .flat_map(|shard| shard.reviewed_entries.iter())
                .map(|entry| entry.id.as_str())
                .collect::<Vec<_>>();
            if !strictly_sorted_unique(&ids) {
                return Err(format!(
                    "{d:?} entries are not globally sorted and unique across shards"
                )
                .into());
            }
        }
        Ok(m)
    }

    fn merge(
        groups: &BTreeMap<ReviewDomain, Vec<&ReviewShard>>,
        d: ReviewDomain,
        name: &str,
    ) -> Result<BTreeMap<String, ReviewedEntry>, Box<dyn Error>> {
        let Some(g) = groups.get(&d) else {
            return Err(format!("no shards for {name}").into());
        };
        let mut out = BTreeMap::new();
        for s in g {
            for e in &s.reviewed_entries {
                if out.contains_key(&e.id) {
                    return Err(format!("duplicate id {} in {name}", e.id).into());
                }
                out.insert(e.id.clone(), e.clone());
            }
        }
        Ok(out)
    }
}

impl ReviewShard {
    fn validate(&self) -> Result<(), Box<dyn Error>> {
        if self.shard_index >= self.shard_count {
            return Err(format!(
                "shard {:?}/{} index is outside shard_count {}",
                self.domain, self.shard_index, self.shard_count
            )
            .into());
        }
        let expected_file_name = self.domain.file_name(self.shard_index);
        if self.file_name != expected_file_name {
            return Err(format!(
                "review shard filename {} does not match {expected_file_name}",
                self.file_name
            )
            .into());
        }
        if self.reviewed_entries.is_empty() {
            return Err(format!(
                "shard {:?}/{} contains no reviewed entries",
                self.domain, self.shard_index
            )
            .into());
        }
        let ids = self
            .reviewed_entries
            .iter()
            .map(|entry| entry.id.as_str())
            .collect::<Vec<_>>();
        if !strictly_sorted_unique(&ids) {
            return Err(format!(
                "shard {:?}/{} entry ids are not strictly sorted and unique",
                self.domain, self.shard_index
            )
            .into());
        }
        for entry in &self.reviewed_entries {
            entry.validate(self.domain)?;
        }
        Ok(())
    }
}

impl ReviewedEntry {
    fn validate(&self, domain: ReviewDomain) -> Result<(), Box<dyn Error>> {
        for (field, value) in [
            ("id", self.id.as_str()),
            (
                "generated_id_assertion",
                self.generated_id_assertion.as_str(),
            ),
            (
                "generated_canonical_name_assertion",
                self.generated_canonical_name_assertion.as_str(),
            ),
        ] {
            if value.is_empty() {
                return Err(format!("{} has empty {field}", self.id).into());
            }
        }
        if self.generated_source_assertions.is_empty()
            || !strictly_sorted_unique(&self.generated_source_assertions)
        {
            return Err(format!(
                "{} source assertions must be non-empty, sorted, and unique",
                self.id
            )
            .into());
        }
        if self.dependencies.iter().any(String::is_empty)
            || !strictly_sorted_unique(&self.dependencies)
        {
            return Err(format!(
                "{} dependencies must be sorted, unique, non-empty strings",
                self.id
            )
            .into());
        }
        if self.note.as_ref().is_some_and(String::is_empty) {
            return Err(format!("{} has an empty note", self.id).into());
        }
        match self.review_status {
            ReviewStatus::Reviewed if self.applicability == EntryApplicability::Unreviewed => {
                return Err(
                    format!("{} is reviewed but applicability is unreviewed", self.id).into(),
                );
            }
            ReviewStatus::Unreviewed if self.applicability != EntryApplicability::Unreviewed => {
                return Err(
                    format!("{} is unreviewed but has reviewed applicability", self.id).into(),
                );
            }
            _ => {}
        }
        let not_applicable = self.classification == EntryClassification::NotApplicable;
        if not_applicable != (self.applicability == EntryApplicability::NotApplicable) {
            return Err(format!(
                "{} classification and applicability disagree on not_applicable",
                self.id
            )
            .into());
        }
        if (not_applicable
            || self.classification == EntryClassification::DuplicateAlias
            || self.applicability == EntryApplicability::Conditional)
            && self.note.is_none()
        {
            return Err(format!("{} requires a review note", self.id).into());
        }

        match domain {
            ReviewDomain::Options => {
                let aliases = self
                    .aliases
                    .as_ref()
                    .ok_or_else(|| format!("{} option entry is missing aliases", self.id))?;
                if aliases.iter().any(String::is_empty) || !strictly_sorted_unique(aliases) {
                    return Err(format!(
                        "{} aliases must be sorted, unique, non-empty strings",
                        self.id
                    )
                    .into());
                }
            }
            _ if self.aliases.is_some() => {
                return Err(format!("{} named entry must not define aliases", self.id).into());
            }
            _ => {}
        }

        let generated = self.classification == EntryClassification::GeneratedToken;
        if generated != self.profile_parser_resolution.is_some() {
            return Err(format!(
                "{} generated_token classification and profile resolution disagree",
                self.id
            )
            .into());
        }
        if domain != ReviewDomain::Options && self.profile_parser_resolution.is_some() {
            return Err(
                format!("{} named entry must not define parser resolution", self.id).into(),
            );
        }
        if let Some(resolution) = &self.profile_parser_resolution {
            resolution
                .default_profile
                .validate(&self.id, "default_profile")?;
            resolution
                .posix_profile
                .validate(&self.id, "posix_profile")?;
        }
        Ok(())
    }
}

impl ProfileResolution {
    fn validate(&self, id: &str, profile: &str) -> Result<(), Box<dyn Error>> {
        let accepted = matches!(
            self.acceptance,
            ObservedAcceptance::AcceptedExact | ObservedAcceptance::AcceptedUniqueAbbreviation
        );
        if accepted != self.target.is_some() {
            return Err(format!("{id} {profile} target presence does not match acceptance").into());
        }
        if self.target.as_ref().is_some_and(String::is_empty) {
            return Err(format!("{id} {profile} has an empty target").into());
        }
        Ok(())
    }
}

fn strictly_sorted_unique<T: Ord>(values: &[T]) -> bool {
    values.windows(2).all(|pair| pair[0] < pair[1])
}

// ── Application helpers ─────────────────────────────────────────────────────

/// Verify option entry match. Source assertions are EXACT set match.
pub(crate) fn verify_option_entry_match(
    extracted_id: &str,
    extracted_canonical_name: &str,
    extracted_sources: &BTreeSet<(String, String, usize)>,
    extracted_aliases: &[String],
    overlay: Option<&ReviewedEntry>,
) -> Vec<String> {
    let mut f = Vec::new();
    let Some(r) = overlay else {
        f.push(format!(
            "no overlay entry for extracted option {extracted_id}"
        ));
        return f;
    };
    if r.id != extracted_id {
        f.push(format!("overlay id {} != extracted {extracted_id}", r.id));
    }
    if r.generated_id_assertion != extracted_id {
        f.push(format!(
            "id assertion {} != {extracted_id}",
            r.generated_id_assertion
        ));
    }
    if r.generated_canonical_name_assertion != extracted_canonical_name {
        f.push(format!(
            "name assertion {} != {extracted_canonical_name}",
            r.generated_canonical_name_assertion
        ));
    }
    let ov_src: BTreeSet<(String, String, usize)> = r
        .generated_source_assertions
        .iter()
        .map(|s| (s.kind.clone(), s.path.clone(), s.line))
        .collect();
    if ov_src != *extracted_sources {
        let a: Vec<_> = ov_src.difference(extracted_sources).collect();
        let b: Vec<_> = extracted_sources.difference(&ov_src).collect();
        f.push(format!(
            "source set mismatch: only_overlay={a:?} only_extracted={b:?}"
        ));
    }
    let ov_alias: BTreeSet<&str> = r
        .aliases
        .as_deref()
        .unwrap_or_default()
        .iter()
        .map(String::as_str)
        .collect();
    let ex_alias: BTreeSet<&str> = extracted_aliases.iter().map(|s| s.as_str()).collect();
    if ov_alias != ex_alias {
        f.push(format!(
            "alias mismatch: overlay={ov_alias:?} extracted={ex_alias:?}"
        ));
    }
    f
}

/// Verify named entry match. Source assertions are EXACT set match.
pub(crate) fn verify_named_entry_match(
    extracted_id: &str,
    extracted_name: &str,
    extracted_sources: &BTreeSet<(String, String, usize)>,
    overlay: Option<&ReviewedEntry>,
) -> Vec<String> {
    let mut f = Vec::new();
    let Some(r) = overlay else {
        f.push(format!("no overlay entry for extracted {extracted_id}"));
        return f;
    };
    if r.id != extracted_id {
        f.push(format!("overlay id {} != extracted {extracted_id}", r.id));
    }
    if r.generated_id_assertion != extracted_id {
        f.push(format!(
            "id assertion {} != {extracted_id}",
            r.generated_id_assertion
        ));
    }
    if r.generated_canonical_name_assertion != extracted_name {
        f.push(format!(
            "name assertion {} != {extracted_name}",
            r.generated_canonical_name_assertion
        ));
    }
    let ov_src: BTreeSet<(String, String, usize)> = r
        .generated_source_assertions
        .iter()
        .map(|s| (s.kind.clone(), s.path.clone(), s.line))
        .collect();
    if ov_src != *extracted_sources {
        let a: Vec<_> = ov_src.difference(extracted_sources).collect();
        let b: Vec<_> = extracted_sources.difference(&ov_src).collect();
        f.push(format!(
            "source set mismatch: only_overlay={a:?} only_extracted={b:?}"
        ));
    }
    f
}

pub(crate) fn unmatched_overlay_entries(
    extracted_ids: &BTreeSet<String>,
    overlay: &BTreeMap<String, ReviewedEntry>,
) -> Vec<String> {
    overlay
        .keys()
        .filter(|id| !extracted_ids.contains(*id))
        .cloned()
        .collect()
}

pub(crate) fn unmatched_extracted_entries(
    extracted_ids: &BTreeSet<String>,
    overlay: &BTreeMap<String, ReviewedEntry>,
) -> Vec<String> {
    extracted_ids
        .iter()
        .filter(|id| !overlay.contains_key(*id))
        .cloned()
        .collect()
}

#[cfg(test)]
mod tests;
