use crate::fuzzing::{FuzzTarget, HarnessBudget, derive_seed, run, run_with_cardinality};
use crate::{
    ContractClassification, EvidenceSnapshot, Serializability, SerializationContext,
    StreamingParser, classify_contract,
};
use ferricov_model::{AlgebraOp, ByteString, CoverageCount, LineKey, NumericClass};
use sha2::{Digest, Sha256};

const CANONICAL: &[u8] = b"TN:t\nSF:x.c\nFNL:0,1\nFNA:0,1,f\nBRDA:1,0,e,1\nMCDC:1,1,t,1,0,c\nMCDC:1,1,f,0,0,c\nDA:1,1\nend_of_record\n";

fn parsed(input: &[u8]) -> StreamingParser {
    let mut parser = StreamingParser::new();
    parser.parse_all(input);
    parser
}

#[test]
fn m1_prop_roundtrip_001() {
    let arbitrary_bytes = b"TN:t-\xff\nSF:x-\xfe.c\nFNL:0,1,9\nFNA:0,2,f-\xfd\nBRDA:1,0,e-\xfc,3\nMCDC:1,1,t,2,0,c-\xfb\nMCDC:1,1,f,0,0,c-\xfb\nDA:1,9007199254740993,sum-\xfa\nend_of_record\n";
    let parser = parsed(arbitrary_bytes);
    let before = parser.database().clone();
    let context = SerializationContext::default();
    let first = crate::write_canonical(parser.database(), &context).unwrap();
    let second = crate::write_canonical(parser.database(), &context).unwrap();
    assert_eq!(first, second);
    assert_eq!(before, *parser.database());
    let reparsed = parsed(&first);
    assert!(
        EvidenceSnapshot::capture(&parser, &context)
            .semantic
            .semantically_equal(&EvidenceSnapshot::capture(&reparsed, &context).semantic)
    );
    assert_eq!(
        crate::write_canonical(reparsed.database(), &context).unwrap(),
        first
    );
}

#[test]
fn m1_prop_accepted_input_001() {
    let cases: &[(&[u8], usize, usize, bool)] = &[
        (CANONICAL, 1, 0, false),
        (b"TN:t\r\nSF:x\r\nDA:1,1\r\nend_of_record\r\n", 1, 0, false),
        (b"garbage\nSF:x\n", 1, 1, false),
    ];
    for (input, sources, diagnostics, stopped) in cases {
        let parser = parsed(input);
        assert_eq!(parser.database().len(), *sources);
        assert_eq!(parser.state().diagnostics().len(), *diagnostics);
        assert_eq!(parser.stopped(), *stopped);
    }
    let original = EvidenceSnapshot::capture(&parsed(CANONICAL), &SerializationContext::default());
    let mutated = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x.c\nDA:1,2\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(!original.semantic.semantically_equal(&mutated.semantic));
}

#[test]
fn m1_prop_numeric_001() {
    let atoms = [
        b"0".as_slice(),
        b"-0",
        b"1e3",
        b"9007199254740993",
        b"NaN",
        b"Inf",
    ];
    for left in atoms {
        for right in atoms {
            let a = CoverageCount::from_lexeme(left);
            assert_eq!(a.lexeme().as_bytes(), left);
            assert_eq!(
                a.atom().class(),
                if left == b"NaN" {
                    NumericClass::Nan
                } else if left == b"Inf" {
                    NumericClass::PositiveInfinity
                } else {
                    NumericClass::Finite
                }
            );
            let result = a.add(&CoverageCount::from_lexeme(right));
            if left == b"NaN" || left == b"Inf" || right == b"NaN" || right == b"Inf" {
                assert!(result.is_err());
            }
        }
    }
    assert_eq!(
        CoverageCount::from_lexeme("9007199254740993")
            .add(&CoverageCount::from_lexeme("7"))
            .unwrap()
            .lexeme()
            .as_bytes(),
        b"9007199254741000"
    );
    assert_eq!(
        CoverageCount::from_lexeme("1e3").compare_threshold("999"),
        Some(std::cmp::Ordering::Greater)
    );
    let sequence = ["1", "2", "3", "4", "5", "6", "7", "8"]
        .into_iter()
        .map(CoverageCount::from_lexeme)
        .reduce(|a, b| a.add(&b).unwrap())
        .unwrap();
    assert_eq!(sequence.lexeme().as_bytes(), b"36");
}

#[test]
fn m1_prop_algebra_001() {
    let left = parsed(b"TN:a\nSF:x\nDA:1,2\nDA:2,4\nend_of_record\n");
    let right = parsed(b"TN:a\nSF:x\nDA:1,3\nDA:3,8\nend_of_record\n");
    let key = ferricov_model::SourceLookupKey::from_path_bytes("x");
    let mut union = left.database().get(&key).unwrap().aggregate().clone();
    union
        .apply_op(
            AlgebraOp::Union,
            right.database().get(&key).unwrap().aggregate(),
        )
        .unwrap();
    assert_eq!(
        union
            .lines()
            .get(&LineKey::from_lexeme("1"))
            .unwrap()
            .lexeme()
            .as_bytes(),
        b"5"
    );
    assert!(
        union.lines().contains_key(&LineKey::from_lexeme("2"))
            && union.lines().contains_key(&LineKey::from_lexeme("3"))
    );
    let mut testcase_union = left.database().get(&key).unwrap().testcases().clone();
    testcase_union
        .union(right.database().get(&key).unwrap().testcases())
        .unwrap();
    assert_eq!(
        testcase_union
            .lines()
            .values()
            .next()
            .unwrap()
            .get(&LineKey::from_lexeme("1"))
            .unwrap()
            .lexeme()
            .as_bytes(),
        b"5"
    );
    let mut difference = left.database().get(&key).unwrap().aggregate().clone();
    difference
        .apply_op(
            AlgebraOp::Difference,
            right.database().get(&key).unwrap().aggregate(),
        )
        .unwrap();
    assert!(
        difference.lines().contains_key(&LineKey::from_lexeme("2"))
            && !difference.lines().contains_key(&LineKey::from_lexeme("1"))
    );
    let functions_left = parsed(b"TN:t\nSF:f\nFNL:0,1,9\nFNA:0,1,a\nDA:1,1\nend_of_record\n");
    let functions_right = parsed(b"TN:t\nSF:f\nFNL:0,1,10\nFNA:0,2,b\nDA:1,1\nend_of_record\n");
    let fkey = ferricov_model::SourceLookupKey::from_path_bytes("f");
    let mut functions = functions_left
        .database()
        .get(&fkey)
        .unwrap()
        .aggregate()
        .functions()
        .clone();
    functions
        .union(
            functions_right
                .database()
                .get(&fkey)
                .unwrap()
                .aggregate()
                .functions(),
        )
        .unwrap();
    assert!(functions.contains_alias(&ByteString::from_slice(b"a")));
    assert!(functions.contains_alias(&ByteString::from_slice(b"b")));
    let long = parsed(b"TN:t\nSF:m\nMCDC:1,2,t,1,0,a\nMCDC:1,2,f,0,0,a\nMCDC:1,2,t,0,1,b\nMCDC:1,2,f,1,1,b\nDA:1,1\nend_of_record\n");
    let short = parsed(b"TN:t\nSF:m\nMCDC:1,2,t,1,0,a\nMCDC:1,2,f,0,0,a\nDA:1,1\nend_of_record\n");
    let mkey = ferricov_model::SourceLookupKey::from_path_bytes("m");
    let mut mcdc = long
        .database()
        .get(&mkey)
        .unwrap()
        .aggregate()
        .mcdc()
        .clone();
    assert!(
        mcdc.union(short.database().get(&mkey).unwrap().aggregate().mcdc())
            .is_err()
    );
}

#[test]
fn m1_prop_algebra_safe_001() {
    let a = parsed(b"TN:t\nSF:x\nDA:1,2\nDA:2,3\nend_of_record\n");
    let b = parsed(b"TN:t\nSF:x\nDA:1,4\nDA:3,5\nend_of_record\n");
    let key = ferricov_model::SourceLookupKey::from_path_bytes("x");
    let (sa, sb) = (
        a.database().get(&key).unwrap().aggregate(),
        b.database().get(&key).unwrap().aggregate(),
    );
    let mut ab = sa.clone();
    ab.union(sb).unwrap();
    let mut ba = sb.clone();
    ba.union(sa).unwrap();
    assert_eq!(ab, ba);
    let fixed = ab.clone();
    ab.union(&fixed).unwrap();
    assert_ne!(ab, fixed); // union adds counts: broad idempotence is intentionally false
}

#[test]
fn m1_prop_index_001() {
    let parser=parsed(b"TN:t\nSF:x\nFNL:0,1,9\nFNA:0,1,alpha\nFNA:0,2,beta\nBRDA:1,0,a,1\nBRDA:1,0,b,0\nBRDA:1,1,c,2\nMCDC:1,2,t,1,0,a\nMCDC:1,2,f,0,0,a\nMCDC:1,2,t,0,1,b\nMCDC:1,2,f,1,1,b\nDA:1,1\nend_of_record\n");
    let src = parser.database().iter().next().unwrap().1;
    src.aggregate()
        .functions()
        .assert_indexes_coherent()
        .unwrap();
    src.aggregate().branches().assert_invariants().unwrap();
    src.aggregate().mcdc().assert_invariants().unwrap();
    let mut corrupted = src.aggregate().clone();
    let group = corrupted
        .functions_mut()
        .get_by_start_mut(&LineKey::from_lexeme("1"))
        .unwrap();
    group.remove_alias(&ByteString::from_slice(b"alpha"));
    assert!(corrupted.functions().assert_indexes_coherent().is_err());
    let mut bad_branch = src.aggregate().branches().clone();
    bad_branch
        .get_line_mut(&LineKey::from_lexeme("1"))
        .unwrap()
        .blocks_mut()[0]
        .set_model_position(99);
    assert!(bad_branch.assert_invariants().is_err());
    let mut bad_mcdc = src.aggregate().mcdc().clone();
    bad_mcdc
        .get_line_mut(&LineKey::from_lexeme("1"))
        .unwrap()
        .get_group_mut(&ferricov_model::GroupSizeKey::from_lexeme("2"))
        .unwrap()
        .remove(0);
    assert!(bad_mcdc.assert_invariants().is_err());
}

#[test]
fn m1_prop_nonserial_001() {
    let absent_expression = parsed(b"TN:t\nSF:x\nBRDA:1,0,,1\nDA:1,1\nend_of_record\n");
    assert!(matches!(
        EvidenceSnapshot::capture(&absent_expression, &SerializationContext::default())
            .serializability,
        Serializability::NonSerializable(_)
    ));
    assert!(
        EvidenceSnapshot::capture(&absent_expression, &SerializationContext::default())
            .attempted_output
            .is_none()
    );
    let repeated_close =
        parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\nTN:t\nSF:x\nDA:1,2\nend_of_record\n");
    assert!(matches!(
        classify_contract(&repeated_close, &SerializationContext::default()),
        ContractClassification::BlockedOracleUnknown
    ));
    assert!(
        EvidenceSnapshot::capture(&repeated_close, &SerializationContext::default())
            .attempted_output
            .is_none()
    );
}

#[test]
fn deterministic_seed_derivation_is_domain_separated() {
    let seed = derive_seed("M1-FZ-LEX-001", "case", "00");
    assert_eq!(seed, derive_seed("M1-FZ-LEX-001", "case", "00"));
    assert_ne!(seed, derive_seed("M1-FZ-STATEFUL-001", "case", "00"));
}

#[test]
fn structural_budget_rejection_is_fail_closed() {
    let tiny = HarnessBudget {
        input_bytes: 4,
        ..HarnessBudget::CI_SMOKE
    };
    assert!(matches!(
        run(FuzzTarget::Lex, b"more than four", tiny),
        Err(crate::fuzzing::HarnessFailure::BudgetExceeded {
            dimension: "input_bytes",
            ..
        })
    ));
    assert!(matches!(
        run_with_cardinality(
            FuzzTarget::Lex,
            b"",
            2,
            HarnessBudget {
                family_cardinality: 1,
                ..HarnessBudget::CI_SMOKE
            }
        ),
        Err(crate::fuzzing::HarnessFailure::BudgetExceeded {
            dimension: "family_cardinality",
            ..
        })
    ));
    assert!(matches!(
        run(
            FuzzTarget::Lex,
            b"",
            HarnessBudget {
                per_case: std::time::Duration::ZERO,
                ..HarnessBudget::CI_SMOKE
            }
        ),
        Err(crate::fuzzing::HarnessFailure::DeadlineExceeded { .. })
    ));
}

#[test]
fn permanent_seed_corpus_hashes_are_pinned() {
    let canonical = include_bytes!("../../../fuzz/corpus/m1_fz_lex_001/canonical.trace");
    let prefixes = include_bytes!("../../../fuzz/corpus/m1_fz_lex_001/all-record-prefixes.trace");
    assert_eq!(
        format!("{:x}", Sha256::digest(canonical)),
        "85267961e048efc54c94f384efe8ef5f611aab198d17c9150cb1cf42954eadc6"
    );
    assert_eq!(
        format!("{:x}", Sha256::digest(prefixes)),
        "49b5c6f24424b3b311da7bafe279432603b7aec9257fff667e4d6f9f050e6fc8"
    );
}

#[test]
#[ignore = "execute through the CI subprocess watchdog and RSS cap"]
fn deterministic_64_case_campaign_replays_all_named_targets() {
    let targets = [
        ("M1-FZ-LEX-001", FuzzTarget::Lex),
        ("M1-FZ-STATEFUL-001", FuzzTarget::Stateful),
        ("M1-FZ-WRITER-001", FuzzTarget::Writer),
        ("M1-FZ-ROUNDTRIP-001", FuzzTarget::Roundtrip),
        ("M1-FZ-NUMERIC-001", FuzzTarget::Numeric),
        ("M1-FZ-LINE-ALGEBRA-001", FuzzTarget::LineAlgebra),
        ("M1-FZ-FUNCTION-ALGEBRA-001", FuzzTarget::FunctionAlgebra),
        ("M1-FZ-BRANCH-ALGEBRA-001", FuzzTarget::BranchAlgebra),
        ("M1-FZ-MCDC-ALGEBRA-001", FuzzTarget::McdcAlgebra),
    ];
    for (target_id, target) in targets {
        let mut state = derive_seed(
            target_id,
            "CORE009-SEED-CANONICAL-001",
            "85267961e048efc54c94f384efe8ef5f611aab198d17c9150cb1cf42954eadc6",
        );
        for _ in 0..64 {
            let mut bytes = vec![0; (state as usize % 256) + 1];
            for byte in &mut bytes {
                state ^= state << 13;
                state ^= state >> 7;
                state ^= state << 17;
                *byte = state as u8;
            }
            run(target, &bytes, HarnessBudget::CI_SMOKE).expect("within CORE-009 budget");
        }
    }
}
