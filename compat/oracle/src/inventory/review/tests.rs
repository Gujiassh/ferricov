use super::*;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

fn ss(entries: &[(&str, &str, usize)]) -> BTreeSet<(String, String, usize)> {
    entries
        .iter()
        .map(|(k, p, l)| (k.to_string(), p.to_string(), *l))
        .collect()
}

fn mk_entry(status: ReviewStatus, cls: EntryClassification) -> ReviewedEntry {
    ReviewedEntry {
        id: "cmd.test.option.foo".into(),
        review_status: status,
        classification: cls,
        applicability: EntryApplicability::AllSupportedEnvironments,
        dependencies: vec![],
        generated_id_assertion: "cmd.test.option.foo".into(),
        generated_source_assertions: vec![SourceAssertion {
            kind: "parser_definition".into(),
            path: "bin/test".into(),
            line: 42,
        }],
        generated_canonical_name_assertion: "--foo".into(),
        aliases: Some(vec!["-f".into()]),
        profile_parser_resolution: None,
        note: None,
    }
}

// ── content hash ────────────────────────────────────────────────────────────

#[test]
fn content_hash_is_deterministic() {
    let e = vec![mk_entry(
        ReviewStatus::Reviewed,
        EntryClassification::Public,
    )];
    let h1 = ReviewOverlay::compute_content_hash(&e);
    let h2 = ReviewOverlay::compute_content_hash(&e);
    assert_eq!(h1, h2);
    assert!(h1.starts_with("sha256:"));
    assert_eq!(h1.len(), 71);
}

#[test]
fn content_hash_changes_with_classification() {
    let h_pub = ReviewOverlay::compute_content_hash(&[mk_entry(
        ReviewStatus::Reviewed,
        EntryClassification::Public,
    )]);
    let h_int = ReviewOverlay::compute_content_hash(&[mk_entry(
        ReviewStatus::Reviewed,
        EntryClassification::Internal,
    )]);
    assert_ne!(h_pub, h_int);
}

#[test]
fn content_hash_changes_with_review_status() {
    let h_r = ReviewOverlay::compute_content_hash(&[mk_entry(
        ReviewStatus::Reviewed,
        EntryClassification::Public,
    )]);
    let h_u = ReviewOverlay::compute_content_hash(&[mk_entry(
        ReviewStatus::Unreviewed,
        EntryClassification::Public,
    )]);
    assert_ne!(h_r, h_u);
}

// ── option match ────────────────────────────────────────────────────────────

#[test]
fn option_match_passes_exact_set() {
    let ov = ReviewedEntry {
        id: "cmd.a.option.x".into(),
        review_status: ReviewStatus::Reviewed,
        classification: EntryClassification::Public,
        applicability: EntryApplicability::AllSupportedEnvironments,
        dependencies: vec![],
        generated_id_assertion: "cmd.a.option.x".into(),
        generated_source_assertions: vec![SourceAssertion {
            kind: "parser_definition".into(),
            path: "bin/a".into(),
            line: 10,
        }],
        generated_canonical_name_assertion: "--x".into(),
        aliases: Some(vec!["-x".into()]),
        profile_parser_resolution: None,
        note: None,
    };
    let f = verify_option_entry_match(
        "cmd.a.option.x",
        "--x",
        &ss(&[("parser_definition", "bin/a", 10)]),
        &["-x".to_string()],
        Some(&ov),
    );
    assert!(f.is_empty(), "{f:?}");
}

#[test]
fn option_match_fails_missing_overlay() {
    let f = verify_option_entry_match("cmd.a.option.x", "--x", &ss(&[]), &[], None);
    assert_eq!(f.len(), 1);
    assert!(f[0].contains("no overlay"));
}

#[test]
fn option_match_fails_id_mismatch() {
    let ov = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    let f = verify_option_entry_match(
        "cmd.a.option.wrong",
        "--foo",
        &ss(&[("parser_definition", "bin/test", 42)]),
        &["-f".to_string()],
        Some(&ov),
    );
    assert!(!f.is_empty());
}

#[test]
fn option_match_fails_stale_source() {
    let mut ov = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    ov.generated_source_assertions = vec![SourceAssertion {
        kind: "parser_definition".into(),
        path: "bin/test".into(),
        line: 999,
    }];
    let f = verify_option_entry_match(
        "cmd.test.option.foo",
        "--foo",
        &ss(&[("parser_definition", "bin/test", 42)]),
        &["-f".to_string()],
        Some(&ov),
    );
    assert_eq!(f.len(), 1);
    assert!(f[0].contains("source set mismatch"));
}

#[test]
fn option_match_fails_extra_extracted_source() {
    // Exact set: extracted has an extra source not in overlay → mismatch.
    let ov = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    let f = verify_option_entry_match(
        "cmd.test.option.foo",
        "--foo",
        &ss(&[
            ("parser_definition", "bin/test", 42),
            ("manual_candidate", "docs/test.rst", 99),
        ]),
        &["-f".to_string()],
        Some(&ov),
    );
    assert_eq!(f.len(), 1);
    assert!(f[0].contains("source set mismatch"));
}

#[test]
fn option_match_fails_alias_mismatch() {
    let ov = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    let f = verify_option_entry_match(
        "cmd.test.option.foo",
        "--foo",
        &ss(&[("parser_definition", "bin/test", 42)]),
        &["-z".to_string()],
        Some(&ov),
    );
    assert_eq!(f.len(), 1);
}

#[test]
fn option_match_fails_name_mismatch() {
    let mut ov = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    ov.generated_canonical_name_assertion = "--wrong".into();
    let f = verify_option_entry_match(
        "cmd.test.option.foo",
        "--foo",
        &ss(&[("parser_definition", "bin/test", 42)]),
        &["-f".to_string()],
        Some(&ov),
    );
    assert_eq!(f.len(), 1);
}

// ── named match ─────────────────────────────────────────────────────────────

#[test]
fn named_entry_match_passes() {
    let ov = ReviewedEntry {
        id: "lcovrc.key".into(),
        review_status: ReviewStatus::Reviewed,
        classification: EntryClassification::Public,
        applicability: EntryApplicability::AllSupportedEnvironments,
        dependencies: vec![],
        generated_id_assertion: "lcovrc.key".into(),
        generated_source_assertions: vec![SourceAssertion {
            kind: "config_definition".into(),
            path: "lcovrc".into(),
            line: 10,
        }],
        generated_canonical_name_assertion: "key".into(),
        aliases: None,
        profile_parser_resolution: None,
        note: None,
    };
    let f = verify_named_entry_match(
        "lcovrc.key",
        "key",
        &ss(&[("config_definition", "lcovrc", 10)]),
        Some(&ov),
    );
    assert!(f.is_empty(), "{f:?}");
}

#[test]
fn named_entry_fails_stale_source() {
    let ov = ReviewedEntry {
        id: "lcovrc.key".into(),
        review_status: ReviewStatus::Reviewed,
        classification: EntryClassification::Public,
        applicability: EntryApplicability::AllSupportedEnvironments,
        dependencies: vec![],
        generated_id_assertion: "lcovrc.key".into(),
        generated_source_assertions: vec![SourceAssertion {
            kind: "config_definition".into(),
            path: "lcovrc".into(),
            line: 999,
        }],
        generated_canonical_name_assertion: "key".into(),
        aliases: None,
        profile_parser_resolution: None,
        note: None,
    };
    let f = verify_named_entry_match(
        "lcovrc.key",
        "key",
        &ss(&[("config_definition", "lcovrc", 10)]),
        Some(&ov),
    );
    assert_eq!(f.len(), 1);
    assert!(f[0].contains("source set mismatch"));
}

// ── set completeness ────────────────────────────────────────────────────────

#[test]
fn unmatched_detection() {
    let mut ov = BTreeMap::new();
    ov.insert(
        "a".into(),
        mk_entry(ReviewStatus::Reviewed, EntryClassification::Public),
    );
    let ex: BTreeSet<String> = BTreeSet::new();
    assert_eq!(unmatched_overlay_entries(&ex, &ov), vec!["a"]);
    let mut ex2 = BTreeSet::new();
    ex2.insert("b".into());
    assert_eq!(
        unmatched_extracted_entries(&ex2, &BTreeMap::new()),
        vec!["b"]
    );
}

// ── deserialization ────────────────────────────────────────────────────────

#[test]
fn duplicate_alias_deserializes() {
    let j = r#"{"id":"a","review_status":"reviewed","classification":"duplicate_alias","applicability":"all_supported_environments","dependencies":[],"generated_id_assertion":"a","generated_source_assertions":[],"generated_canonical_name_assertion":"a","note":"->b"}"#;
    let e: ReviewedEntry = serde_json::from_str(j).unwrap();
    assert_eq!(e.review_status, ReviewStatus::Reviewed);
    assert_eq!(e.classification, EntryClassification::DuplicateAlias);
    assert_eq!(e.note.as_deref(), Some("->b"));
}

#[test]
fn deny_unknown_fields() {
    let j = r#"{"id":"x","review_status":"reviewed","classification":"public","applicability":"all_supported_environments","dependencies":[],"generated_id_assertion":"x","generated_source_assertions":[],"generated_canonical_name_assertion":"x","bad":1}"#;
    assert!(serde_json::from_str::<ReviewedEntry>(j).is_err());
}

// ── profile-dependent resolution ────────────────────────────────────────────

#[test]
fn profile_resolution_deserializes() {
    let j = r#"{"id":"a","review_status":"reviewed","classification":"generated_token","applicability":"all_supported_environments","dependencies":[],"generated_id_assertion":"a","generated_source_assertions":[],"generated_canonical_name_assertion":"a","profile_parser_resolution":{"default_profile":{"acceptance":"accepted_unique_abbreviation","target":"cmd.x"},"posix_profile":{"acceptance":"rejected_unknown"}}}"#;
    let e: ReviewedEntry = serde_json::from_str(j).unwrap();
    let obs = e.profile_parser_resolution.unwrap();
    assert_eq!(
        obs.default_profile.acceptance,
        ObservedAcceptance::AcceptedUniqueAbbreviation
    );
    assert_eq!(obs.default_profile.target.as_deref(), Some("cmd.x"));
    let px = obs.posix_profile;
    assert_eq!(px.acceptance, ObservedAcceptance::RejectedUnknown);
    assert!(px.target.is_none());
}

#[test]
fn profile_resolution_requires_posix_profile() {
    let j = r#"{"id":"a","review_status":"reviewed","classification":"generated_token","applicability":"all_supported_environments","dependencies":[],"generated_id_assertion":"a","generated_source_assertions":[],"generated_canonical_name_assertion":"a","profile_parser_resolution":{"default_profile":{"acceptance":"rejected_unknown"}}}"#;
    assert!(serde_json::from_str::<ReviewedEntry>(j).is_err());
}

#[test]
fn null_note_is_rejected_instead_of_becoming_absent() {
    let j = r#"{"id":"a","review_status":"reviewed","classification":"public","applicability":"all_supported_environments","dependencies":[],"generated_id_assertion":"a","generated_source_assertions":[],"generated_canonical_name_assertion":"a","note":null}"#;
    assert!(serde_json::from_str::<ReviewedEntry>(j).is_err());
}

#[test]
fn entry_semantics_reject_duplicate_assertions_and_aliases() {
    let mut entry = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    entry
        .generated_source_assertions
        .push(entry.generated_source_assertions[0].clone());
    assert!(entry.validate(ReviewDomain::Options).is_err());

    let mut entry = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    entry.aliases = Some(vec!["-f".into(), "-f".into()]);
    assert!(entry.validate(ReviewDomain::Options).is_err());
}

#[test]
fn entry_semantics_keep_review_status_and_applicability_coherent() {
    let mut reviewed = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    reviewed.applicability = EntryApplicability::Unreviewed;
    assert!(reviewed.validate(ReviewDomain::Options).is_err());

    let mut unreviewed = mk_entry(ReviewStatus::Unreviewed, EntryClassification::Public);
    unreviewed.applicability = EntryApplicability::Unreviewed;
    assert!(unreviewed.validate(ReviewDomain::Options).is_ok());
}

#[test]
fn entry_semantics_reject_named_option_fields_and_missing_profile() {
    let mut named = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    assert!(named.validate(ReviewDomain::Config).is_err());
    named.aliases = None;
    assert!(named.validate(ReviewDomain::Config).is_ok());

    let generated = mk_entry(ReviewStatus::Reviewed, EntryClassification::GeneratedToken);
    assert!(generated.validate(ReviewDomain::Options).is_err());
}

#[test]
fn profile_target_presence_matches_acceptance_and_preserves_exact() {
    let accepted = ProfileResolution {
        acceptance: ObservedAcceptance::AcceptedExact,
        target: Some("command.test.option.target".into()),
    };
    assert!(
        accepted
            .validate("command.test.option.token", "default")
            .is_ok()
    );
    let encoded = serde_json::to_value(&accepted).unwrap();
    assert_eq!(encoded["acceptance"], "accepted_exact");

    let rejected_with_target = ProfileResolution {
        acceptance: ObservedAcceptance::RejectedUnknown,
        target: Some("command.test.option.target".into()),
    };
    assert!(
        rejected_with_target
            .validate("command.test.option.token", "default")
            .is_err()
    );
}

fn domain_name(domain: ReviewDomain) -> &'static str {
    match domain {
        ReviewDomain::Options => "option_entries",
        ReviewDomain::Config => "config_entries",
        ReviewDomain::SupportScripts => "support_script_entries",
        ReviewDomain::PositionalArguments => "positional_argument_entries",
    }
}

fn domain_entry(domain: ReviewDomain, id: &str) -> ReviewedEntry {
    let mut entry = mk_entry(ReviewStatus::Reviewed, EntryClassification::Public);
    entry.id = id.into();
    entry.generated_id_assertion = id.into();
    if domain == ReviewDomain::Options {
        entry.generated_canonical_name_assertion = "--foo".into();
    } else {
        entry.generated_canonical_name_assertion = "foo".into();
        entry.aliases = None;
    }
    entry
}

fn write_shard(
    directory: &Path,
    domain: ReviewDomain,
    index: usize,
    count: usize,
    entries: Vec<ReviewedEntry>,
) {
    let document = serde_json::json!({
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        "domain": domain_name(domain),
        "shard_index": index,
        "shard_count": count,
        "content_hash": ReviewOverlay::compute_content_hash(&entries),
        "reviewed_entries": entries,
    });
    fs::write(
        directory.join(domain.file_name(index)),
        format!("{}\n", serde_json::to_string_pretty(&document).unwrap()),
    )
    .unwrap();
}

fn valid_review_directory() -> tempfile::TempDir {
    let directory = tempfile::tempdir().unwrap();
    for (domain, id) in [
        (ReviewDomain::Options, "command.test.option.foo"),
        (ReviewDomain::Config, "lcovrc.foo"),
        (ReviewDomain::SupportScripts, "support-script.foo"),
        (
            ReviewDomain::PositionalArguments,
            "command.test.positional.foo",
        ),
    ] {
        write_shard(
            directory.path(),
            domain,
            0,
            1,
            vec![domain_entry(domain, id)],
        );
    }
    directory
}

#[test]
fn loader_requires_all_domains_and_valid_content_hashes() {
    let directory = valid_review_directory();
    ReviewOverlay::load(
        directory.path(),
        "v2.5",
        "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
    )
    .unwrap();

    fs::remove_file(directory.path().join("config-entries-00.json")).unwrap();
    assert!(
        ReviewOverlay::load(
            directory.path(),
            "v2.5",
            "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        )
        .is_err()
    );
}

#[test]
fn loader_rejects_hash_filename_and_unlisted_file_mutations() {
    let directory = valid_review_directory();
    let path = directory.path().join("option-entries-00.json");
    let mut document: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    document["content_hash"] = serde_json::json!(format!("sha256:{}", "0".repeat(64)));
    fs::write(&path, serde_json::to_string_pretty(&document).unwrap()).unwrap();
    assert!(
        ReviewOverlay::load(
            directory.path(),
            "v2.5",
            "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        )
        .is_err()
    );

    let directory = valid_review_directory();
    fs::write(directory.path().join("README"), "not a shard").unwrap();
    assert!(
        ReviewOverlay::load(
            directory.path(),
            "v2.5",
            "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        )
        .is_err()
    );
}

#[test]
fn loader_rejects_incomplete_and_noncanonical_shard_sets() {
    let directory = valid_review_directory();
    fs::remove_file(directory.path().join("option-entries-00.json")).unwrap();
    write_shard(
        directory.path(),
        ReviewDomain::Options,
        0,
        2,
        vec![domain_entry(ReviewDomain::Options, "command.test.option.z")],
    );
    write_shard(
        directory.path(),
        ReviewDomain::Options,
        1,
        2,
        vec![domain_entry(ReviewDomain::Options, "command.test.option.a")],
    );
    assert!(
        ReviewOverlay::load(
            directory.path(),
            "v2.5",
            "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        )
        .is_err()
    );
}
