//! Bounded, deterministic CORE-009 harness shared by property tests and libFuzzer.

use std::time::{Duration, Instant};

use sha2::{Digest, Sha256};

use crate::{
    ContractClassification, EvidenceSnapshot, SerializationContext, StreamingParser,
    classify_contract,
};

#[path = "fuzzing/reference_oracle.rs"]
mod reference_oracle;

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

/// Evidence envelope produced by the process-isolation controller.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FailureArtifact {
    pub target_id: String,
    pub case_id: String,
    pub seed: u64,
    pub input_sha256: String,
    pub outcome: WorkerOutcome,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkerOutcome {
    Exit(i32),
    Signal(i32),
    Timeout,
    RssLimit,
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
    let started = Instant::now();
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
        cardinality += source.testcases().lines().len()
            + source.testcases().functions().len()
            + source.testcases().branches().len()
            + source.testcases().mcdc().len();
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
    cardinality += preview.state().diagnostics().len();
    if cardinality > budget.family_cardinality {
        return Err(HarnessFailure::BudgetExceeded {
            dimension: "actual_family_cardinality",
            observed: cardinality,
            limit: budget.family_cardinality,
        });
    }
    match target {
        FuzzTarget::Lex => lexical(input),
        FuzzTarget::Stateful => stateful(input),
        FuzzTarget::Writer => writer(input),
        FuzzTarget::Roundtrip => roundtrip(input),
        FuzzTarget::Numeric => numeric(input),
        FuzzTarget::LineAlgebra => reference_oracle::run_line_program(input),
        FuzzTarget::FunctionAlgebra => reference_oracle::run_function_program(input),
        FuzzTarget::BranchAlgebra => reference_oracle::run_branch_program(input),
        FuzzTarget::McdcAlgebra => reference_oracle::run_mcdc_program(input),
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
        for field in framed_fields(line) {
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

/// Conservatively frame only fields whose delimiters are unambiguously
/// structural.  The final field of name/expression/checksum records is allowed
/// to contain commas and therefore remains one field.
fn framed_fields(line: &[u8]) -> Vec<&[u8]> {
    let Some(colon) = line.iter().position(|byte| *byte == b':') else {
        return vec![line];
    };
    let tag = &line[..colon];
    let payload = &line[colon + 1..];
    let structural = match tag {
        b"DA" => 2,
        b"FN" => 2,
        b"FNDA" => 1,
        b"FNL" => 2,
        b"FNA" => 2,
        b"BRDA" => 3,
        b"MCDC" => 5,
        _ => 0,
    };
    if structural == 0 {
        return vec![payload];
    }
    payload
        .splitn(structural + 1, |byte| *byte == b',')
        .collect()
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
        (b"VER:", crate::RecordTag::Ver),
        (b"FN:", crate::RecordTag::Fn),
        (b"FNL:", crate::RecordTag::Fnl),
        (b"FNF:", crate::RecordTag::Fnf),
        (b"FNH:", crate::RecordTag::Fnh),
        (b"BRF:", crate::RecordTag::Brf),
        (b"BRH:", crate::RecordTag::Brh),
        (b"MCF:", crate::RecordTag::Mcf),
        (b"MCH:", crate::RecordTag::Mch),
        (b"LF:", crate::RecordTag::Lf),
        (b"LH:", crate::RecordTag::Lh),
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
    let byte = |index: usize| input.get(index).copied().unwrap_or(index as u8) | 0x80;
    let generated_bytes = [
        b"TN:t-".as_slice(),
        &[byte(0)],
        b"\nSF:s-",
        &[byte(1)],
        b"\nFNL:0,1,2\nFNA:0,3,f-",
        &[byte(2)],
        b"\nBRDA:1,0,e-",
        &[byte(3)],
        b",1\nMCDC:1,1,t,1,0,c-",
        &[byte(4)],
        b"\nMCDC:1,1,f,0,0,c-",
        &[byte(4)],
        b"\nDA:1,2,sum-",
        &[byte(5)],
        b"\nend_of_record\n",
    ]
    .concat();
    let generated = parser(&generated_bytes);
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
    // Decode a bounded integer program and calculate its result without using
    // CoverageCount.  This avoids the tautological "same fold twice" oracle.
    let values: Vec<i64> = input
        .chunks(2)
        .take(8)
        .map(|chunk| {
            let magnitude = i64::from(chunk[0] % 100);
            if chunk.get(1).is_some_and(|byte| byte & 1 != 0) {
                -magnitude
            } else {
                magnitude
            }
        })
        .collect();
    if let Some((first, rest)) = values.split_first() {
        let expected = rest.iter().fold(*first, |sum, value| sum + value);
        let observed = rest
            .iter()
            .map(|value| ferricov_model::CoverageCount::from_lexeme(value.to_string()))
            .try_fold(
                ferricov_model::CoverageCount::from_lexeme(first.to_string()),
                |sum, value| sum.add(&value),
            )
            .expect("generated integer program is finite");
        assert_eq!(
            observed.lexeme().as_bytes(),
            expected.to_string().as_bytes()
        );
        assert_eq!(
            observed.compare_threshold("0"),
            Some(expected.cmp(&0)),
            "independent threshold comparison"
        );
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

#[cfg(test)]
mod budget_tests {
    use super::*;

    #[test]
    fn comma_bearing_suffix_is_one_bounded_field() {
        let budget = HarnessBudget {
            field_bytes: 4,
            ..HarnessBudget::CI_SMOKE
        };
        assert!(matches!(
            validate_budget(b"FNA:0,1,a,b,c\n", budget),
            Err(HarnessFailure::BudgetExceeded {
                dimension: "field_bytes",
                observed: 5,
                ..
            })
        ));
        assert!(validate_budget(b"FNA:0,1,a,b\n", budget).is_ok());
    }
}
