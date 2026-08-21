//! Focused M1-CORE-007 acceptance tests (canonical writer).

use ferricov_model::{
    BranchEdge, BranchKind, BranchTaken, CoverageCount, CoverageDatabase, GroupSizeKey, LineKey,
    NumericAtom, SourceCoverage, SourceIdentity, SourceLookupKey, TestName,
};

use crate::parser::StreamingParser;
use crate::writer::{write_database, write_info, WriteOptions};

fn parse_db(bytes: &[u8]) -> CoverageDatabase {
    StreamingParser::parse_database(bytes)
}

fn opts_all() -> WriteOptions {
    WriteOptions {
        function_coverage: true,
        branch_coverage: true,
        mcdc_coverage: true,
        checksum_output: false,
        comments: Vec::new(),
    }
}

#[test]
fn writer_order_core_matches_oracle_bytes() {
    let input = b"\
TN:z\n\
SF:src/z.c\n\
VER:v1\n\
FNL:5,10,20\n\
FNA:5,1,zb\n\
FNA:5,2,za\n\
BRDA:2,0,e,1\n\
BRDA:2,0,e2,0\n\
MCDC:3,2,f,0,0,expr\n\
MCDC:3,2,t,1,0,expr\n\
DA:1,1\n\
DA:2,1\n\
DA:3,1\n\
DA:10,1\n\
DA:20,0\n\
FNF:9\n\
FNH:9\n\
BRF:9\n\
BRH:9\n\
MCF:9\n\
MCH:9\n\
LF:9\n\
LH:9\n\
end_of_record\n\
TN:a\n\
SF:src/a.c\n\
FNL:0,1,1\n\
FNA:0,1,f\n\
DA:1,1\n\
end_of_record\n\
TN:m\n\
SF:src/a.c\n\
DA:2,1\n\
end_of_record\n";

    let expected = b"\
TN:a\n\
SF:src/a.c\n\
FNL:0,1,1\n\
FNA:0,1,f\n\
FNF:1\n\
FNH:1\n\
DA:1,1\n\
LF:1\n\
LH:1\n\
end_of_record\n\
TN:m\n\
SF:src/a.c\n\
FNF:0\n\
FNH:0\n\
DA:2,1\n\
LF:1\n\
LH:1\n\
end_of_record\n\
TN:z\n\
SF:src/z.c\n\
VER:v1\n\
FNL:0,10,20\n\
FNA:0,2,za\n\
FNA:0,1,zb\n\
FNF:1\n\
FNH:1\n\
BRDA:2,0,e,1\n\
BRDA:2,0,e2,0\n\
BRF:2\n\
BRH:1\n\
MCDC:3,2,t,1,0,expr\n\
MCDC:3,2,f,0,0,expr\n\
MCF:2\n\
MCH:1\n\
DA:1,1\n\
DA:2,1\n\
DA:3,1\n\
DA:10,1\n\
DA:20,0\n\
LF:5\n\
LH:4\n\
end_of_record\n";

    let db = parse_db(input);
    let out = write_info(&db, &opts_all());
    assert_eq!(
        String::from_utf8_lossy(&out),
        String::from_utf8_lossy(expected)
    );
    assert_eq!(out, expected);
}

#[test]
fn writer_mcdc_groups_lexical_sense_and_totals() {
    let input = b"\
TN:m\n\
SF:src/m.c\n\
MCDC:1,10,t,1,0,big\n\
MCDC:1,10,f,0,0,big\n\
MCDC:1,2,t,1,0,small\n\
MCDC:1,2,f,0,0,small\n\
MCDC:1,U3,t,1,0,ucond\n\
MCDC:1,3,f,0,0,ucond\n\
MCDC:2,1,f,1,0,sense_first\n\
MCDC:2,1,t,2,0,sense_first\n\
MCDC:3,1,t,1,0,a,b,c\n\
MCDC:3,1,f,0,0,a,b,c\n\
DA:1,1\n\
DA:2,1\n\
DA:3,1\n\
end_of_record\n";

    let expected = b"\
TN:m\n\
SF:src/m.c\n\
MCDC:1,10,t,1,0,big\n\
MCDC:1,10,f,0,0,big\n\
MCDC:1,2,t,1,0,small\n\
MCDC:1,2,f,0,0,small\n\
MCDC:1,U3,t,1,0,ucond\n\
MCDC:1,3,f,0,0,ucond\n\
MCDC:2,1,t,2,0,sense_first\n\
MCDC:2,1,f,1,0,sense_first\n\
MCDC:3,1,t,1,0,a,b,c\n\
MCDC:3,1,f,0,0,a,b,c\n\
MCF:10\n\
MCH:6\n\
DA:1,1\n\
DA:2,1\n\
DA:3,1\n\
LF:3\n\
LH:3\n\
end_of_record\n";

    let db = parse_db(input);
    let mut opts = opts_all();
    opts.function_coverage = false;
    opts.branch_coverage = false;
    let out = write_database(&db, &opts);
    assert_eq!(out, expected);
}

#[test]
fn writer_recomputes_summaries_and_drops_input_comments() {
    let input = b"\
# dropme\n\
TN:c\n\
SF:src/c.c\n\
# mid\n\
DA:1,1,chk\n\
LF:999\n\
LH:bad\n\
end_of_record\n";

    let expected = b"\
TN:c\n\
SF:src/c.c\n\
DA:1,1\n\
LF:1\n\
LH:1\n\
end_of_record\n";

    let db = parse_db(input);
    let mut opts = opts_all();
    opts.function_coverage = false;
    opts.branch_coverage = false;
    opts.mcdc_coverage = false;
    let out = write_info(&db, &opts);
    assert_eq!(out, expected);
}

#[test]
fn writer_explicit_add_comments_precede_sections() {
    let mut db = CoverageDatabase::new();
    let mut source = SourceCoverage::new(SourceIdentity::from_display_path("a.c"));
    let tn = TestName::new("t");
    let mut lines = ferricov_model::LineCoverage::new();
    lines.insert(LineKey::from_lexeme("1"), CoverageCount::from_lexeme("1"));
    source.testcases_mut().insert_lines(tn, lines);
    db.insert(source);

    let mut opts = WriteOptions::new();
    opts.function_coverage = false;
    opts.branch_coverage = false;
    opts.mcdc_coverage = false;
    opts.add_comment(b" first");
    opts.add_comment(b" second");

    let out = write_info(&db, &opts);
    assert!(out.starts_with(b"# first\n# second\nTN:t\n"));
}

#[test]
fn repeated_writes_are_byte_identical_and_do_not_mutate_model() {
    let input = b"\
TN:s\n\
SF:src/s.c\n\
FNL:0,1,1\n\
FNA:0,1,f\n\
BRDA:1,0,e,1\n\
BRDA:1,0,e2,0\n\
MCDC:1,1,t,1,0,c\n\
MCDC:1,1,f,0,0,c\n\
DA:1,1\n\
DA:2,0\n\
end_of_record\n";

    let db = parse_db(input);
    let before = db.clone();
    let opts = opts_all();
    let w1 = write_info(&db, &opts);
    let w2 = write_info(&db, &opts);
    assert_eq!(w1, w2);
    assert_eq!(db, before);

    let expected = b"\
TN:s\n\
SF:src/s.c\n\
FNL:0,1,1\n\
FNA:0,1,f\n\
FNF:1\n\
FNH:1\n\
BRDA:1,0,e,1\n\
BRDA:1,0,e2,0\n\
BRF:2\n\
BRH:1\n\
MCDC:1,1,t,1,0,c\n\
MCDC:1,1,f,0,0,c\n\
MCF:2\n\
MCH:1\n\
DA:1,1\n\
DA:2,0\n\
LF:2\n\
LH:1\n\
end_of_record\n";
    assert_eq!(w1, expected);
}

#[test]
fn brda_dash_never_evaluated_round_trip() {
    let input = b"\
TN:t\n\
SF:a.c\n\
BRDA:1,0,edge,-\n\
BRDA:1,0,other,0\n\
DA:1,1\n\
end_of_record\n";

    let db = parse_db(input);
    let opts = WriteOptions {
        function_coverage: false,
        branch_coverage: true,
        mcdc_coverage: false,
        checksum_output: false,
        comments: Vec::new(),
    };
    let out = write_info(&db, &opts);
    assert!(
        out.windows(b"BRDA:1,0,edge,-".len())
            .any(|w| w == b"BRDA:1,0,edge,-"),
        "missing NeverEvaluated emission: {}",
        String::from_utf8_lossy(&out)
    );

    let db2 = parse_db(&out);
    let src = db2
        .get(&SourceLookupKey::from_path_bytes("a.c"))
        .expect("source");
    let tn = TestName::new("t");
    let br = src.testcases().branches().get(&tn).expect("branches");
    let bline = br.get_line(&LineKey::from_lexeme("1")).expect("line");
    assert_eq!(bline.blocks().len(), 1);
    assert!(bline.blocks()[0].edges()[0].taken().is_never_evaluated());
    assert!(!bline.blocks()[0].edges()[1].taken().is_never_evaluated());
}

#[test]
fn non_utf8_sf_path_round_trip() {
    let input = b"TN:x\nSF:src/\xff.c\nDA:1,1\nend_of_record\n";
    let db = parse_db(input);
    let mut opts = opts_all();
    opts.function_coverage = false;
    opts.branch_coverage = false;
    opts.mcdc_coverage = false;
    let out = write_info(&db, &opts);
    let expected = b"TN:x\nSF:src/\xff.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n";
    assert_eq!(out, expected);

    let db2 = parse_db(&out);
    assert!(db2.contains_key(&SourceLookupKey::from_path_bytes(b"src/\xff.c".as_slice())));
}

#[test]
fn branch_signature_sort_and_renumber() {
    // Same shape as fixtures/branches/sort-signatures.info
    let input = b"\
TN:br_sort\n\
SF:src/br-sort.c\n\
BRDA:10,0,a0,1\n\
BRDA:10,0,a1,0\n\
BRDA:10,0,a2,1\n\
BRDA:10,1,b0,1\n\
BRDA:10,1,b1,0\n\
BRDA:10,e2,e0,1\n\
BRDA:10,f3,f0,1\n\
BRDA:10,3,f1,0\n\
DA:10,1\n\
end_of_record\n";

    let expected = b"\
TN:br_sort\n\
SF:src/br-sort.c\n\
BRDA:10,e0,e0,1\n\
BRDA:10,1,b0,1\n\
BRDA:10,1,b1,0\n\
BRDA:10,f2,f0,1\n\
BRDA:10,2,f1,0\n\
BRDA:10,3,a0,1\n\
BRDA:10,3,a1,0\n\
BRDA:10,3,a2,1\n\
BRF:8\n\
BRH:5\n\
DA:10,1\n\
LF:1\n\
LH:1\n\
end_of_record\n";

    let db = parse_db(input);
    let opts = WriteOptions {
        function_coverage: false,
        branch_coverage: true,
        mcdc_coverage: false,
        checksum_output: false,
        comments: Vec::new(),
    };
    let out = write_info(&db, &opts);
    assert_eq!(
        String::from_utf8_lossy(&out),
        String::from_utf8_lossy(expected)
    );
}

#[test]
fn excluded_branch_emits_u_and_is_excluded_from_totals() {
    let input = b"\
TN:br_u_modes\n\
SF:src/br-u-modes.c\n\
BRDA:10,U0,unreach,0\n\
BRDA:10,0,reach,1\n\
BRDA:20,fU0,x > 0,0\n\
BRDA:20,0,x <= 0,1\n\
BRDA:30,eU0,exc,0\n\
BRDA:30,0,norm,1\n\
DA:10,1\n\
DA:20,1\n\
DA:30,1\n\
end_of_record\n";

    let expected = b"\
TN:br_u_modes\n\
SF:src/br-u-modes.c\n\
BRDA:10,U0,unreach,0\n\
BRDA:10,0,reach,1\n\
BRDA:20,fU0,x > 0,0\n\
BRDA:20,0,x <= 0,1\n\
BRDA:30,eU0,exc,0\n\
BRDA:30,0,norm,1\n\
BRF:3\n\
BRH:3\n\
DA:10,1\n\
DA:20,1\n\
DA:30,1\n\
LF:3\n\
LH:3\n\
end_of_record\n";

    let db = parse_db(input);
    let opts = WriteOptions {
        function_coverage: false,
        branch_coverage: true,
        mcdc_coverage: false,
        checksum_output: false,
        comments: Vec::new(),
    };
    assert_eq!(write_info(&db, &opts), expected);
}

#[test]
fn constructed_model_parse_write_parse_preserves_semantics() {
    // Build a small model directly, write, parse, compare key stores.
    let mut db = CoverageDatabase::new();
    let mut source = SourceCoverage::new(SourceIdentity::from_display_path("/src/demo.c"));
    source.set_version(Some(ferricov_model::ByteString::from("v1")));
    let tn = TestName::new("suite");

    let mut lines = ferricov_model::LineCoverage::new();
    lines.insert(LineKey::from_lexeme("10"), CoverageCount::from_lexeme("5"));
    lines.insert(LineKey::from_lexeme("11"), CoverageCount::from_lexeme("0"));
    source.testcases_mut().insert_lines(tn.clone(), lines.clone());
    *source.aggregate_mut().lines_mut() = lines;

    let mut fns = ferricov_model::FunctionTable::new();
    fns.insert_alias_at(
        LineKey::from_lexeme("10"),
        "main",
        CoverageCount::from_lexeme("3"),
    )
    .unwrap();
    fns.set_group_end(&LineKey::from_lexeme("10"), Some(LineKey::from_lexeme("20")));
    source
        .testcases_mut()
        .insert_functions(tn.clone(), fns.clone());
    *source.aggregate_mut().functions_mut() = fns;

    let mut branches = ferricov_model::BranchCoverage::new();
    {
        let bline = branches.entry_line(LineKey::from_lexeme("10"));
        bline.push_block();
        let block = bline.last_block_mut().unwrap();
        block.append_edge(BranchEdge::new(
            BranchTaken::from_token("1"),
            BranchKind::Vanilla,
            Some(ferricov_model::ByteString::from("edge")),
            false,
        ));
        block.append_edge(BranchEdge::new(
            BranchTaken::NeverEvaluated,
            BranchKind::Vanilla,
            Some(ferricov_model::ByteString::from("other")),
            false,
        ));
    }
    source
        .testcases_mut()
        .insert_branches(tn.clone(), branches.clone());
    *source.aggregate_mut().branches_mut() = branches;

    let mut mcdc = ferricov_model::McdcCoverage::new();
    {
        let mline = mcdc.entry_line(LineKey::from_lexeme("10"));
        let expr = mline.append_expression(
            GroupSizeKey::from_lexeme("1"),
            NumericAtom::from_lexeme("0"),
            "cond",
        );
        expr.set_sense(true, CoverageCount::from_lexeme("1"), false)
            .unwrap();
        expr.set_sense(false, CoverageCount::from_lexeme("2"), false)
            .unwrap();
    }
    source
        .testcases_mut()
        .insert_mcdc(tn.clone(), mcdc.clone());
    *source.aggregate_mut().mcdc_mut() = mcdc;

    db.insert(source);

    let out = write_info(&db, &opts_all());
    let db2 = parse_db(&out);

    let src2 = db2
        .get(&SourceLookupKey::from_path_bytes("/src/demo.c"))
        .expect("rewritten source");
    assert_eq!(src2.version().map(|v| v.as_bytes()), Some(b"v1".as_slice()));
    let tc_lines = src2.testcases().lines().get(&tn).expect("lines");
    assert_eq!(
        tc_lines
            .get(&LineKey::from_lexeme("10"))
            .map(CoverageCount::lexeme)
            .map(|b| b.as_bytes()),
        Some(b"5".as_slice())
    );
    let tc_fn = src2.testcases().functions().get(&tn).expect("fns");
    assert!(tc_fn.contains_alias(&ferricov_model::ByteString::from("main")));
    let tc_br = src2.testcases().branches().get(&tn).expect("br");
    assert!(tc_br
        .get_line(&LineKey::from_lexeme("10"))
        .unwrap()
        .blocks()[0]
        .edges()[1]
        .taken()
        .is_never_evaluated());
    let tc_mcdc = src2.testcases().mcdc().get(&tn).expect("mcdc");
    let group = tc_mcdc
        .get_line(&LineKey::from_lexeme("10"))
        .unwrap()
        .get_group(&GroupSizeKey::from_lexeme("1"))
        .unwrap();
    assert_eq!(group[0].true_sense().count().lexeme().as_bytes(), b"1");
    assert_eq!(group[0].false_sense().count().lexeme().as_bytes(), b"2");

    // Second write of rewritten model stays fixed.
    let out2 = write_info(&db2, &opts_all());
    assert_eq!(out, out2);
}

#[test]
fn legacy_fn_fnda_emits_current_fnl_fna() {
    let input = b"\
TN:forb\n\
KF:src/k.c\n\
FN:1,2,foo\n\
FNDA:3,foo\n\
DA:1,1\n\
DA:2,1\n\
end_of_record_and_junk\n";

    let expected = b"\
TN:forb\n\
SF:src/k.c\n\
FNL:0,1,2\n\
FNA:0,3,foo\n\
FNF:1\n\
FNH:1\n\
DA:1,1\n\
DA:2,1\n\
LF:2\n\
LH:2\n\
end_of_record\n";

    let db = parse_db(input);
    let mut opts = opts_all();
    opts.branch_coverage = false;
    opts.mcdc_coverage = false;
    assert_eq!(write_info(&db, &opts), expected);
}

#[test]
fn mcdc_only_testcase_omitted_without_line_key() {
    // Line-test enumeration: B owns MC/DC only → omitted from canonical output.
    let mut db = CoverageDatabase::new();
    let mut source = SourceCoverage::new(SourceIdentity::from_display_path("/m0/demo.c"));
    let a = TestName::new("A");
    let b = TestName::new("B");

    let mut a_lines = ferricov_model::LineCoverage::new();
    a_lines.insert(LineKey::from_lexeme("1"), CoverageCount::from_lexeme("1"));
    source.testcases_mut().insert_lines(a.clone(), a_lines);

    let mut b_mcdc = ferricov_model::McdcCoverage::new();
    {
        let mline = b_mcdc.entry_line(LineKey::from_lexeme("1"));
        let expr = mline.append_expression(
            GroupSizeKey::from_lexeme("1"),
            NumericAtom::from_lexeme("0"),
            "only_b",
        );
        expr.set_sense(true, CoverageCount::from_lexeme("1"), false)
            .unwrap();
    }
    source.testcases_mut().insert_mcdc(b, b_mcdc);
    db.insert(source);

    let out = write_info(&db, &opts_all());
    let text = String::from_utf8_lossy(&out);
    assert!(text.contains("TN:A\n"));
    assert!(!text.contains("TN:B\n"));
    assert!(!text.contains("only_b"));
}
