//! Focused M1-CORE-006 acceptance tests (record apply + section commit).

use ferricov_model::{BranchTaken, CoverageCount, LineKey, SourceLookupKey, TestName};

use crate::diag::DiagKind;
use crate::parser::StreamingParser;
use crate::policy::IgnorePolicy;

fn source_of<'a>(
    db: &'a ferricov_model::CoverageDatabase,
    path: &str,
) -> &'a ferricov_model::SourceCoverage {
    db.get(&SourceLookupKey::from_path_bytes(path))
        .unwrap_or_else(|| panic!("missing source {path}"))
}

#[test]
fn multi_record_section_commits_lines_functions_branches_mcdc() {
    let input = b"\
TN:suite\n\
SF:/src/demo.c\n\
VER:v1\n\
FNL:0,10,20\n\
FNA:0,3,main\n\
BRDA:10,0,edge,1\n\
BRDA:10,0,other,-\n\
MCDC:10,1,t,1,0,cond\n\
MCDC:10,1,f,2,0,cond\n\
DA:10,5,chksum\n\
DA:11,0\n\
LF:99\n\
LH:not-a-number\n\
end_of_record\n";

    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    assert!(!p.stopped());
    let db = p.database();
    assert_eq!(db.len(), 1);

    let src = source_of(db, "/src/demo.c");
    assert_eq!(src.version().map(|v| v.as_bytes()), Some(b"v1".as_slice()));
    assert_eq!(
        src.checksums()
            .get(&LineKey::from_lexeme("10"))
            .map(|b| b.as_bytes()),
        Some(b"chksum".as_slice())
    );

    let tn = TestName::new("suite");
    let tc_lines = src.testcases().lines().get(&tn).expect("testcase lines");
    assert_eq!(
        tc_lines
            .get(&LineKey::from_lexeme("10"))
            .map(CoverageCount::lexeme)
            .map(|b| b.as_bytes()),
        Some(b"5".as_slice())
    );
    assert_eq!(
        tc_lines
            .get(&LineKey::from_lexeme("11"))
            .map(CoverageCount::lexeme)
            .map(|b| b.as_bytes()),
        Some(b"0".as_slice())
    );

    // Aggregate received the same line union.
    assert!(
        src.aggregate()
            .lines()
            .contains_key(&LineKey::from_lexeme("10"))
    );

    let tc_fn = src.testcases().functions().get(&tn).expect("functions");
    assert!(tc_fn.contains_alias(&ferricov_model::ByteString::from_slice(b"main")));
    assert_eq!(tc_fn.group_len(), 1);

    let tc_br = src.testcases().branches().get(&tn).expect("branches");
    let bline = tc_br
        .get_line(&LineKey::from_lexeme("10"))
        .expect("br line");
    assert_eq!(bline.blocks().len(), 1);
    assert_eq!(bline.blocks()[0].edges().len(), 2);
    assert!(bline.blocks()[0].edges()[1].taken().is_never_evaluated());

    let tc_mcdc = src.testcases().mcdc().get(&tn).expect("mcdc");
    let mline = tc_mcdc
        .get_line(&LineKey::from_lexeme("10"))
        .expect("mcdc line");
    let group = mline
        .get_group(&ferricov_model::GroupSizeKey::from_lexeme("1"))
        .expect("group");
    assert_eq!(group.len(), 1);
    assert_eq!(group[0].true_sense().count().lexeme().as_bytes(), b"1");
    assert_eq!(group[0].false_sense().count().lexeme().as_bytes(), b"2");

    // Summary tags must not become trusted observable totals.
    assert!(src.observable_totals().is_empty());
}

#[test]
fn summary_records_do_not_become_trusted_totals() {
    let input = b"\
TN:\n\
SF:a.c\n\
DA:1,1\n\
FNF:100\n\
FNH:50\n\
BRF:20\n\
BRH:10\n\
MCF:4\n\
MCH:2\n\
LF:7\n\
LH:3\n\
end_of_record\n";
    let db = StreamingParser::parse_database(input);
    let src = source_of(&db, "a.c");
    assert!(src.observable_totals().is_empty());
    // Line data still present from DA, not from LF/LH.
    assert_eq!(src.aggregate().lines().len(), 1);
}

#[test]
fn ver_conflict_hard_fails() {
    let input = b"\
TN:t\n\
SF:v.c\n\
VER:one\n\
VER:two\n\
DA:1,1\n\
end_of_record\n";
    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    assert!(p.stopped());
    assert!(p.state().diagnostics().iter().any(|d| {
        matches!(d.kind, DiagKind::VersionConflict) && d.class == crate::diag::DiagClass::HardFail
    }));
}

#[test]
fn ver_identical_repeat_accepted() {
    let input = b"\
TN:t\n\
SF:v.c\n\
VER:same\n\
VER:same\n\
DA:1,1\n\
end_of_record\n";
    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    assert!(!p.stopped());
    assert_eq!(
        source_of(p.database(), "v.c")
            .version()
            .map(|v| v.as_bytes()),
        Some(b"same".as_slice())
    );
}

#[test]
fn late_tn_assigns_mcdc_to_current_name() {
    // Minimal fixture mirroring M0-TF-TN-MCDC idea.
    let input = b"\
TN:A\n\
SF:/m0/late-tn.c\n\
FNL:0,1,1\n\
FNA:0,1,f\n\
BRDA:1,0,edge,1\n\
MCDC:1,1,t,1,0,cond\n\
DA:1,1\n\
TN:B\n\
MCDC:1,1,f,1,0,cond\n\
end_of_record\n";

    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    assert!(!p.stopped());
    let src = source_of(p.database(), "/m0/late-tn.c");

    let a = TestName::new("A");
    let b = TestName::new("B");

    // Line / function / branch frozen on SF-bound A.
    assert!(src.testcases().lines().contains_key(&a));
    assert!(!src.testcases().lines().contains_key(&b));
    assert!(src.testcases().functions().contains_key(&a));
    assert!(!src.testcases().functions().contains_key(&b));
    assert!(src.testcases().branches().contains_key(&a));
    assert!(!src.testcases().branches().contains_key(&b));

    // MC/DC closed onto current name B (U-MCDC-LATE-TN).
    assert!(
        src.testcases().mcdc().contains_key(&b),
        "expected MC/DC under B, keys={:?}",
        src.testcases()
            .mcdc()
            .keys()
            .map(|k| k.as_bytes().to_vec())
            .collect::<Vec<_>>()
    );
    // A may be absent from MC/DC family (empty A is allowed but not required
    // when no MC/DC was closed under A).
    let mcdc_b = src.testcases().mcdc().get(&b).expect("B mcdc");
    let mline = mcdc_b.get_line(&LineKey::from_lexeme("1")).expect("line1");
    let group = mline
        .get_group(&ferricov_model::GroupSizeKey::from_lexeme("1"))
        .expect("group");
    assert_eq!(group.len(), 1);
    assert!(group[0].true_sense().count().is_positive());
    assert!(group[0].false_sense().count().is_positive());

    // Aggregate holds both senses.
    let agg = src
        .aggregate()
        .mcdc()
        .get_line(&LineKey::from_lexeme("1"))
        .expect("agg mcdc");
    let agg_g = agg
        .get_group(&ferricov_model::GroupSizeKey::from_lexeme("1"))
        .expect("agg group");
    assert!(agg_g[0].true_sense().count().is_positive());
    assert!(agg_g[0].false_sense().count().is_positive());
}

#[test]
fn brda_dash_is_never_evaluated() {
    let input = b"\
TN:t\n\
SF:b.c\n\
BRDA:3,0,expr,-\n\
DA:3,1\n\
end_of_record\n";
    let db = StreamingParser::parse_database(input);
    let src = source_of(&db, "b.c");
    let tn = TestName::new("t");
    let edge = src
        .testcases()
        .branches()
        .get(&tn)
        .unwrap()
        .get_line(&LineKey::from_lexeme("3"))
        .unwrap()
        .blocks()[0]
        .edges()[0]
        .taken();
    assert_eq!(edge, &BranchTaken::NeverEvaluated);
    assert!(!edge.contributes_hit());
}

#[test]
fn non_utf8_sf_path_with_da_works() {
    let input = b"TN:t\nSF:p/\xff/q.c\nDA:2,4\nend_of_record\n";
    let db = StreamingParser::parse_database(input);
    let key = SourceLookupKey::from_path_bytes(&b"p/\xff/q.c"[..]);
    let src = db.get(&key).expect("non-utf8 source");
    let tn = TestName::new("t");
    assert_eq!(
        src.testcases()
            .lines()
            .get(&tn)
            .unwrap()
            .get(&LineKey::from_lexeme("2"))
            .unwrap()
            .lexeme()
            .as_bytes(),
        b"4"
    );
}

#[test]
fn unknown_record_is_error_format_continue_by_default() {
    let input = b"\
TN:t\n\
SF:u.c\n\
DA:1,1\n\
TD:nope\n\
DA:2,1\n\
end_of_record\n";
    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    assert!(!p.stopped());
    assert!(
        p.state()
            .diagnostics()
            .iter()
            .any(|d| matches!(d.kind, DiagKind::ErrorFormat))
    );
    let src = source_of(p.database(), "u.c");
    assert_eq!(src.aggregate().lines().len(), 2);
}

#[test]
fn ignore_policy_stop_halts_after_unknown() {
    let input = b"\
TN:t\n\
SF:u.c\n\
TD:nope\n\
DA:1,1\n\
end_of_record\n";
    let mut p = StreamingParser::with_policy(IgnorePolicy::Stop);
    let _ = p.parse_all(input);
    assert!(p.stopped());
    // DA after stop should not commit meaningful line data for this section
    // (open section never successfully committed with DA, or stopped before).
    // Source may exist from SF bind ensure; lines should be empty or absent commit.
    if let Some(src) = p.database().get(&SourceLookupKey::from_path_bytes("u.c")) {
        assert!(src.aggregate().lines().is_empty());
    }
}

#[test]
fn into_database_consumes_parser() {
    let input = b"TN:\nSF:z.c\nDA:1,1\nend_of_record\n";
    let mut p = StreamingParser::new();
    let _ = p.parse_all(input);
    let db = p.into_database();
    assert_eq!(db.len(), 1);
}
