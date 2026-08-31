//! Bounded, deterministic CORE-009 harness shared by property tests and libFuzzer.

use std::time::{Duration, Instant};

use ferricov_model::{AlgebraOp, CoverageStore};
use sha2::{Digest, Sha256};

use crate::{
    ContractClassification, EvidenceSnapshot, SerializationContext, StreamingParser,
    classify_contract,
};

/// The activation contract's CI-smoke safety caps. These are harness caps, not
/// product input limits.
#[derive(Debug, Clone, Copy)]
pub struct HarnessBudget {
    pub input_bytes: usize,
    pub field_bytes: usize,
    pub records: usize,
    pub sections: usize,
    pub family_cardinality: usize,
    pub per_case: Duration,
}

impl HarnessBudget {
    pub const CI_SMOKE: Self = Self {
        input_bytes: 1_048_576,
        field_bytes: 262_144,
        records: 65_536,
        sections: 65_536,
        family_cardinality: 65_536,
        per_case: Duration::from_secs(2),
    };
}

#[derive(Debug, Clone, Copy)]
pub enum FuzzTarget {
    Lex,
    Stateful,
    Writer,
    Roundtrip,
    Numeric,
    LineAlgebra,
    FunctionAlgebra,
    BranchAlgebra,
    McdcAlgebra,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HarnessFailure {
    BudgetExceeded {
        dimension: &'static str,
        observed: usize,
        limit: usize,
    },
    DeadlineExceeded {
        elapsed: Duration,
        limit: Duration,
    },
}

/// Stable seed required by the CORE-009 contract.
#[must_use]
pub fn derive_seed(target_id: &str, case_id: &str, fixture_sha256: &str) -> u64 {
    let mut hash = Sha256::new();
    hash.update(target_id.as_bytes());
    hash.update([0]);
    hash.update(case_id.as_bytes());
    hash.update([0]);
    hash.update(fixture_sha256.as_bytes());
    u64::from_be_bytes(hash.finalize()[..8].try_into().expect("eight-byte seed"))
}

/// Execute one input after fail-closed structural budget validation.
pub fn run(target: FuzzTarget, input: &[u8], budget: HarnessBudget) -> Result<(), HarnessFailure> {
    run_with_cardinality(target, input, 0, budget)
}

pub fn run_with_cardinality(
    target: FuzzTarget,
    input: &[u8],
    family_cardinality: usize,
    budget: HarnessBudget,
) -> Result<(), HarnessFailure> {
    if family_cardinality > budget.family_cardinality {
        return Err(HarnessFailure::BudgetExceeded {
            dimension: "family_cardinality",
            observed: family_cardinality,
            limit: budget.family_cardinality,
        });
    }
    validate_budget(input, budget)?;
    let preview = parser(input);
    let mut cardinality = preview.database().len();
    for (_, source) in preview.database().iter() {
        cardinality += source.aggregate().lines().len();
        cardinality += source
            .aggregate()
            .functions()
            .groups()
            .map(|(_, group)| group.aliases().len())
            .sum::<usize>();
        cardinality += source
            .aggregate()
            .branches()
            .lines()
            .map(|(_, line)| {
                line.blocks()
                    .iter()
                    .map(|block| block.edges().len())
                    .sum::<usize>()
            })
            .sum::<usize>();
        cardinality += source
            .aggregate()
            .mcdc()
            .lines()
            .map(|(_, line)| line.groups().values().map(Vec::len).sum::<usize>())
            .sum::<usize>();
        cardinality += source
            .testcases()
            .lines()
            .values()
            .map(|family| family.len())
            .sum::<usize>();
        cardinality += source
            .testcases()
            .functions()
            .values()
            .map(|family| {
                family
                    .groups()
                    .map(|(_, group)| group.aliases().len())
                    .sum::<usize>()
            })
            .sum::<usize>();
        cardinality += source
            .testcases()
            .branches()
            .values()
            .map(|family| {
                family
                    .lines()
                    .map(|(_, line)| {
                        line.blocks()
                            .iter()
                            .map(|block| block.edges().len())
                            .sum::<usize>()
                    })
                    .sum::<usize>()
            })
            .sum::<usize>();
        cardinality += source
            .testcases()
            .mcdc()
            .values()
            .map(|family| {
                family
                    .lines()
                    .map(|(_, line)| line.groups().values().map(Vec::len).sum::<usize>())
                    .sum::<usize>()
            })
            .sum::<usize>();
    }
    if cardinality > budget.family_cardinality {
        return Err(HarnessFailure::BudgetExceeded {
            dimension: "actual_family_cardinality",
            observed: cardinality,
            limit: budget.family_cardinality,
        });
    }
    let started = Instant::now();
    match target {
        FuzzTarget::Lex => lexical(input),
        FuzzTarget::Stateful => stateful(input),
        FuzzTarget::Writer => writer(input),
        FuzzTarget::Roundtrip => roundtrip(input),
        FuzzTarget::Numeric => numeric(input),
        FuzzTarget::LineAlgebra => algebra(input, AlgebraOp::Union),
        FuzzTarget::FunctionAlgebra => algebra(input, AlgebraOp::Intersect),
        FuzzTarget::BranchAlgebra => algebra(input, AlgebraOp::Difference),
        FuzzTarget::McdcAlgebra => algebra(input, AlgebraOp::Union),
    }
    let elapsed = started.elapsed();
    if elapsed > budget.per_case {
        return Err(HarnessFailure::DeadlineExceeded {
            elapsed,
            limit: budget.per_case,
        });
    }
    Ok(())
}

fn validate_budget(input: &[u8], budget: HarnessBudget) -> Result<(), HarnessFailure> {
    if input.len() > budget.input_bytes {
        return Err(HarnessFailure::BudgetExceeded {
            dimension: "input_bytes",
            observed: input.len(),
            limit: budget.input_bytes,
        });
    }
    let mut records = 0usize;
    let mut sections = 0usize;
    for line in input.split(|byte| *byte == b'\n') {
        records += 1;
        let payload = line
            .iter()
            .position(|byte| *byte == b':')
            .map_or(line, |index| &line[index + 1..]);
        let opaque = [b"TN:".as_slice(), b"SF:", b"KF:", b"VER:"]
            .iter()
            .any(|prefix| line.starts_with(prefix));
        for field in payload.split(|byte| !opaque && *byte == b',') {
            if field.len() > budget.field_bytes {
                return Err(HarnessFailure::BudgetExceeded {
                    dimension: "field_bytes",
                    observed: field.len(),
                    limit: budget.field_bytes,
                });
            }
        }
        if records > budget.records {
            return Err(HarnessFailure::BudgetExceeded {
                dimension: "records",
                observed: records,
                limit: budget.records,
            });
        }
        if line.starts_with(b"end_of_record") {
            sections += 1;
            if sections > budget.sections {
                return Err(HarnessFailure::BudgetExceeded {
                    dimension: "sections",
                    observed: sections,
                    limit: budget.sections,
                });
            }
        }
    }
    Ok(())
}

fn parser(input: &[u8]) -> StreamingParser {
    let mut parser = StreamingParser::new();
    parser.parse_all(input);
    parser
}

fn lexical(input: &[u8]) {
    let first = parser(input);
    let second = parser(input);
    assert_eq!(
        EvidenceSnapshot::capture(&first, &SerializationContext::default()),
        EvidenceSnapshot::capture(&second, &SerializationContext::default())
    );
    const TAGS: &[(&[u8], crate::RecordTag)] = &[
        (b"TN:", crate::RecordTag::Tn),
        (b"SF:", crate::RecordTag::Sf),
        (b"KF:", crate::RecordTag::Kf),
        (b"DA:", crate::RecordTag::Da),
        (b"FNDA:", crate::RecordTag::Fnda),
        (b"FNA:", crate::RecordTag::Fna),
        (b"BRDA:", crate::RecordTag::Brda),
        (b"MCDC:", crate::RecordTag::Mcdc),
    ];
    for line in input.split(|byte| *byte == b'\n') {
        for (prefix, expected) in TAGS {
            if line.starts_with(prefix) {
                if let crate::LineClass::Record { tag, .. } = crate::classify_line(line) {
                    assert_eq!(tag, *expected, "structured lexical tag oracle");
                }
            }
        }
        if let Some(suffix) = line.strip_prefix(b"end_of_record") {
            match crate::classify_line(line) {
                crate::LineClass::Terminator { unconsumed } => {
                    assert_eq!(unconsumed.as_bytes(), suffix)
                }
                other => panic!("terminator reference mismatch: {other:?}"),
            }
        }
    }
}

fn stateful(input: &[u8]) {
    let whole = parser(input);
    for split in [0, input.len() / 2, input.len()] {
        let mut chunked = StreamingParser::new();
        chunked.feed(&input[..split]);
        chunked.feed(&input[split..]);
        chunked.finish();
        assert_eq!(
            EvidenceSnapshot::capture(&whole, &SerializationContext::default()),
            EvidenceSnapshot::capture(&chunked, &SerializationContext::default())
        );
    }
    let mut hard = StreamingParser::with_policy(crate::IgnorePolicy::Stop);
    hard.parse_all(b"TN:t\nSF:x\nVER:a\nVER:b\nDA:1,9\nend_of_record\n");
    assert!(hard.stopped());
    assert!(
        hard.database()
            .iter()
            .all(|(_, source)| source.aggregate().lines().is_empty()),
        "hard failure partially committed post-failure coverage"
    );
}

fn writer(input: &[u8]) {
    let parsed = parser(input);
    let before = parsed.database().clone();
    let context = SerializationContext::default();
    let evidence = EvidenceSnapshot::capture(&parsed, &context);
    if let crate::Serializability::Serializable(bytes) = evidence.serializability {
        assert_eq!(before, *parsed.database());
        let reparsed = parser(&bytes);
        assert!(
            evidence
                .semantic
                .semantically_equal(&EvidenceSnapshot::capture(&reparsed, &context).semantic)
        );
    }
    let generated = parser(b"TN:t-\xff\nSF:s-\xfe\nFNL:0,1,2\nFNA:0,3,f-\xfd\nBRDA:1,0,e-\xfc,1\nMCDC:1,1,t,1,0,c-\xfb\nMCDC:1,1,f,0,0,c-\xfb\nDA:1,2,sum-\xfa\nend_of_record\n");
    let before = generated.database().clone();
    let bytes = crate::write_canonical(generated.database(), &SerializationContext::default())
        .expect("generated model serializable");
    assert_eq!(
        bytes,
        crate::write_canonical(generated.database(), &SerializationContext::default()).unwrap()
    );
    assert_eq!(before, *generated.database());
}

fn roundtrip(input: &[u8]) {
    let parsed = parser(input);
    let context = SerializationContext::default();
    match classify_contract(&parsed, &context) {
        ContractClassification::Serializable => writer(input),
        ContractClassification::NonSerializable(_)
        | ContractClassification::BlockedOracleUnknown => {
            let evidence = EvidenceSnapshot::capture(&parsed, &context);
            assert!(
                evidence.attempted_output.is_none(),
                "writer invoked for preclassified model"
            );
        }
    }
}

fn numeric(input: &[u8]) {
    let atoms: Vec<_> = input
        .split(|b| *b == b',')
        .take(8)
        .map(ferricov_model::CoverageCount::from_lexeme)
        .collect();
    if let Some((first, rest)) = atoms.split_first() {
        let one = rest
            .iter()
            .try_fold(first.clone(), |left, right| left.add(right));
        let two = rest
            .iter()
            .try_fold(first.clone(), |left, right| left.add(right));
        assert_eq!(one, two);
    }
    for (left, right, expected) in [
        ("1", "2", "3"),
        ("9007199254740993", "7", "9007199254741000"),
        ("-0", "0", "0"),
    ] {
        let value = ferricov_model::CoverageCount::from_lexeme(left)
            .add(&ferricov_model::CoverageCount::from_lexeme(right))
            .expect("finite decimal reference");
        assert_eq!(value.lexeme().as_bytes(), expected.as_bytes());
    }
}

fn algebra(input: &[u8], default_operation: AlgebraOp) {
    let Some((&opcode, payload)) = input.split_first() else {
        return;
    };
    let split = payload
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(payload.len() / 2);
    let left = parser(&payload[..split]).database().clone();
    let right_bytes = if split < payload.len() {
        &payload[split + 1..]
    } else {
        &payload[split..]
    };
    let right = parser(right_bytes).database().clone();
    let operation = match opcode % 4 {
        0 => AlgebraOp::Union,
        1 => AlgebraOp::Intersect,
        2 => AlgebraOp::Difference,
        _ => default_operation,
    };
    let keys = left
        .iter()
        .map(|(key, _)| key.clone())
        .chain(right.iter().map(|(key, _)| key.clone()))
        .collect::<std::collections::BTreeSet<_>>();
    for key in keys {
        let mut store = left
            .get(&key)
            .map_or_else(CoverageStore::new, |source| source.aggregate().clone());
        let empty = CoverageStore::new();
        let rhs = right.get(&key).map_or(&empty, |source| source.aggregate());
        let result = match operation {
            AlgebraOp::Union => store.union(rhs),
            AlgebraOp::Intersect => store.intersect(rhs),
            AlgebraOp::Difference => store.difference(rhs),
        };
        if result.is_ok() {
            assert!(store.lines().len() <= HarnessBudget::CI_SMOKE.family_cardinality);
            store
                .functions()
                .assert_indexes_coherent()
                .expect("function indexes");
            store
                .branches()
                .assert_invariants()
                .expect("branch indexes");
            store.mcdc().assert_invariants().expect("mcdc indexes");
        }
    }
}
