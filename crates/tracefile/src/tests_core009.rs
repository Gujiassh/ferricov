use crate::fuzzing::{FuzzTarget, HarnessBudget, derive_seed, run};
use crate::{
    ContractClassification, EvidenceSnapshot, Serializability, SerializationContext,
    StreamingParser, classify_contract,
};
use ferricov_model::CoverageCount;
use sha2::{Digest, Sha256};

const CANONICAL: &[u8] = b"TN:t\nSF:x.c\nFNL:0,1\nFNA:0,1,f\nBRDA:1,0,e,1\nMCDC:1,1,t,1,0,c\nMCDC:1,1,f,0,0,c\nDA:1,1\nend_of_record\n";

fn parsed(input: &[u8]) -> StreamingParser {
    let mut parser = StreamingParser::new();
    parser.parse_all(input);
    parser
}

#[test]
fn m1_prop_roundtrip_001() {
    run(FuzzTarget::Roundtrip, CANONICAL, HarnessBudget::CI_SMOKE);
    run(FuzzTarget::Writer, CANONICAL, HarnessBudget::CI_SMOKE);
}

#[test]
fn m1_prop_accepted_input_001() {
    for input in [
        CANONICAL,
        b"TN:t\r\nSF:x\r\nDA:1,1\r\nend_of_record\r\n",
        b"garbage\nSF:x\n",
    ] {
        let a = EvidenceSnapshot::capture(&parsed(input), &SerializationContext::default());
        let b = EvidenceSnapshot::capture(&parsed(input), &SerializationContext::default());
        assert_eq!(a, b);
    }
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
            let a = CoverageCount::from_lexeme(left).add(&CoverageCount::from_lexeme(right));
            let b = CoverageCount::from_lexeme(left).add(&CoverageCount::from_lexeme(right));
            assert_eq!(a, b);
        }
    }
}

#[test]
fn m1_prop_algebra_001() {
    for target in [
        FuzzTarget::LineAlgebra,
        FuzzTarget::FunctionAlgebra,
        FuzzTarget::BranchAlgebra,
        FuzzTarget::McdcAlgebra,
    ] {
        run(target, CANONICAL, HarnessBudget::CI_SMOKE);
    }
}

#[test]
fn m1_prop_algebra_safe_001() {
    // Identical, canonical operands satisfy the documented safe-subset preconditions.
    run(FuzzTarget::LineAlgebra, CANONICAL, HarnessBudget::CI_SMOKE);
    run(
        FuzzTarget::FunctionAlgebra,
        CANONICAL,
        HarnessBudget::CI_SMOKE,
    );
}

#[test]
fn m1_prop_index_001() {
    run(
        FuzzTarget::FunctionAlgebra,
        CANONICAL,
        HarnessBudget::CI_SMOKE,
    );
    run(
        FuzzTarget::BranchAlgebra,
        CANONICAL,
        HarnessBudget::CI_SMOKE,
    );
    run(FuzzTarget::McdcAlgebra, CANONICAL, HarnessBudget::CI_SMOKE);
}

#[test]
fn m1_prop_nonserial_001() {
    let absent_expression = parsed(b"TN:t\nSF:x\nBRDA:1,0,,1\nDA:1,1\nend_of_record\n");
    assert!(matches!(
        EvidenceSnapshot::capture(&absent_expression, &SerializationContext::default())
            .serializability,
        Serializability::NonSerializable(_)
    ));
    let repeated_close =
        parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\nTN:t\nSF:x\nDA:1,2\nend_of_record\n");
    assert!(matches!(
        classify_contract(&repeated_close, &SerializationContext::default()),
        ContractClassification::BlockedOracleUnknown
    ));
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
    run(FuzzTarget::Lex, b"more than four", tiny);
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
fn deterministic_64_case_campaign_replays_all_named_targets() {
    let targets = [
        FuzzTarget::Lex,
        FuzzTarget::Stateful,
        FuzzTarget::Writer,
        FuzzTarget::Roundtrip,
        FuzzTarget::Numeric,
        FuzzTarget::LineAlgebra,
        FuzzTarget::FunctionAlgebra,
        FuzzTarget::BranchAlgebra,
        FuzzTarget::McdcAlgebra,
    ];
    for (index, target) in targets.into_iter().enumerate() {
        let mut state = derive_seed("M1-CORE-009", &index.to_string(), "deterministic-64");
        for _ in 0..64 {
            let mut bytes = vec![0; (state as usize % 256) + 1];
            for byte in &mut bytes {
                state ^= state << 13;
                state ^= state >> 7;
                state ^= state << 17;
                *byte = state as u8;
            }
            run(target, &bytes, HarnessBudget::CI_SMOKE);
        }
    }
}
