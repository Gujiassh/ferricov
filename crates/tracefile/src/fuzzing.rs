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
        for field in line.split(|byte| *byte == b',') {
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
    for (_, source) in left.iter() {
        let mut store: CoverageStore = source.aggregate().clone();
        let rhs = right
            .get(source.identity().lookup_key())
            .expect("cloned source")
            .aggregate();
        let result = match operation {
            AlgebraOp::Union => store.union(rhs),
            AlgebraOp::Intersect => store.intersect(rhs),
            AlgebraOp::Difference => store.difference(rhs),
        };
        if result.is_ok() {
            assert!(store.lines().len() <= HarnessBudget::CI_SMOKE.family_cardinality);
        }
    }
}
