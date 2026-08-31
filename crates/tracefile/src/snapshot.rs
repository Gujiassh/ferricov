//! Model-semantic snapshots and parser/run evidence envelopes.
use crate::{
    IgnorePolicy, LineSplitterSnapshot, OpenSection, ParserState, SerializationContext,
    SerializationError, StreamingParser, write_canonical,
};
use ferricov_model::{AlgebraOp, CoverageStore, TestName};
use ferricov_model::{ByteString, CoverageDatabase};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContractNonSerializableReason {
    EmptySource,
    AggregateTestcaseDivergence,
    FamilyWithoutLineMembership,
    ChecksumWithoutLineMembership,
    ObservableTotals,
    AlgebraFailure,
    DisabledFamily,
    DisabledChecksum,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContractClassification {
    Serializable,
    NonSerializable(ContractNonSerializableReason),
    BlockedOracleUnknown,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NonSerializableReason {
    Contract(ContractNonSerializableReason),
    Writer(SerializationError),
    CanonicalParseRejected,
    RoundTripSemanticMismatch,
    SecondWriter(SerializationError),
    WriterFixedPointMismatch,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Serializability {
    Serializable(ByteString),
    NonSerializable(NonSerializableReason),
    /// The model is retained, but its classification depends on an Oracle
    /// behavior that is not qualified by the active compatibility contract.
    ///
    /// CORE-008 does not infer this outcome from writer success or failure.
    /// Callers that build contract corpora use it to represent an explicitly
    /// blocked case rather than collapsing that case into either of the two
    /// decided outcomes above.
    BlockedOracleUnknown,
}

/// Stable semantic model projection; parser/run evidence is deliberately absent.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticSnapshot {
    pub database: CoverageDatabase,
}
impl SemanticSnapshot {
    #[must_use]
    pub fn capture(database: &CoverageDatabase) -> Self {
        Self {
            database: database.clone(),
        }
    }
    #[must_use]
    pub fn semantically_equal(&self, other: &Self) -> bool {
        self.database == other.database
    }
}

/// Provenance deliberately excluded from SourceIdentity semantic equality.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceProvenance {
    pub lookup_key: ByteString,
    pub diagnostic_path: Option<ByteString>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBindingProvenance {
    pub raw_path: ByteString,
    pub diagnostic_path: Option<ByteString>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TestNameProvenance {
    pub identity: ByteString,
    pub unsanitized: Option<ByteString>,
}

impl From<&TestName> for TestNameProvenance {
    fn from(name: &TestName) -> Self {
        Self {
            identity: name.as_byte_string().clone(),
            unsanitized: name.unsanitized().cloned(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TestcaseFamily {
    Lines,
    Functions,
    Branches,
    Mcdc,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TestcaseNameProvenance {
    pub source_lookup_key: ByteString,
    pub family: TestcaseFamily,
    pub test_name: TestNameProvenance,
}

impl From<&crate::SourceBinding> for SourceBindingProvenance {
    fn from(binding: &crate::SourceBinding) -> Self {
        Self {
            raw_path: binding.raw_path.clone(),
            diagnostic_path: binding.identity.diagnostic_path().cloned(),
        }
    }
}

/// Optional process-owned evidence; in-process parser capture leaves this absent.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcessEvidence {
    pub stdout: ByteString,
    pub stderr: ByteString,
    pub exit_status: i32,
}

/// Full parser/evidence envelope. Derived equality compares every evidence fact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceSnapshot {
    pub semantic: SemanticSnapshot,
    pub parser_state: ParserState,
    pub splitter: LineSplitterSnapshot,
    pub open_section: Option<OpenSection>,
    pub ignore_policy: IgnorePolicy,
    pub stopped: bool,
    pub source_provenance: Vec<SourceProvenance>,
    pub active_source_provenance: Option<SourceBindingProvenance>,
    pub open_source_provenance: Option<SourceBindingProvenance>,
    pub current_test_name_provenance: TestNameProvenance,
    pub active_test_name_provenance: Option<TestNameProvenance>,
    pub open_test_name_provenance: Option<TestNameProvenance>,
    pub testcase_name_provenance: Vec<TestcaseNameProvenance>,
    /// Bytes produced by the first writer attempt. This remains present when
    /// reparse, semantic equality, or fixed-point validation later fails.
    pub attempted_output: Option<ByteString>,
    pub serializability: Serializability,
    pub process: Option<ProcessEvidence>,
}
impl EvidenceSnapshot {
    #[must_use]
    pub fn capture(parser: &StreamingParser, context: &SerializationContext<'_>) -> Self {
        let (serializability, attempted_output) = classify_and_validate(parser, context);
        let source_provenance = parser
            .database()
            .iter()
            .map(|(key, source)| SourceProvenance {
                lookup_key: key.as_byte_string().clone(),
                diagnostic_path: source.identity().diagnostic_path().cloned(),
            })
            .collect();
        let mut testcase_name_provenance = Vec::new();
        for (source_key, source) in parser.database().iter() {
            let mut push = |family, name: &TestName| {
                testcase_name_provenance.push(TestcaseNameProvenance {
                    source_lookup_key: ByteString::from_slice(source_key.as_bytes()),
                    family,
                    test_name: name.into(),
                });
            };
            for name in source.testcases().lines().keys() {
                push(TestcaseFamily::Lines, name);
            }
            for name in source.testcases().functions().keys() {
                push(TestcaseFamily::Functions, name);
            }
            for name in source.testcases().branches().keys() {
                push(TestcaseFamily::Branches, name);
            }
            for name in source.testcases().mcdc().keys() {
                push(TestcaseFamily::Mcdc, name);
            }
        }
        Self {
            semantic: SemanticSnapshot::capture(parser.database()),
            parser_state: parser.state().clone(),
            splitter: parser.splitter_snapshot(),
            open_section: parser.apply_context().open.clone(),
            ignore_policy: parser.apply_context().policy,
            stopped: parser.stopped(),
            source_provenance,
            active_source_provenance: parser.state().source().map(Into::into),
            open_source_provenance: parser
                .apply_context()
                .open
                .as_ref()
                .map(|open| (&open.binding).into()),
            current_test_name_provenance: parser.state().test_name().into(),
            active_test_name_provenance: parser
                .state()
                .source()
                .map(|binding| (&binding.bound_test_name).into()),
            open_test_name_provenance: parser
                .apply_context()
                .open
                .as_ref()
                .map(|open| open.bound_test_name().into()),
            testcase_name_provenance,
            attempted_output,
            serializability,
            process: None,
        }
    }
    #[must_use]
    pub fn semantically_equal(&self, other: &Self) -> bool {
        self.semantic.semantically_equal(&other.semantic)
    }
}

/// Classify model/lifecycle shape without invoking the canonical writer.
#[must_use]
pub fn classify_contract(
    parser: &StreamingParser,
    context: &SerializationContext<'_>,
) -> ContractClassification {
    if parser.apply_context().repeated_close_observed {
        return ContractClassification::BlockedOracleUnknown;
    }
    for (_, source) in parser.database().iter() {
        if !source.observable_totals().is_empty() {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::ObservableTotals,
            );
        }
        let line_names = source.testcases().lines();
        if line_names.is_empty() {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::EmptySource,
            );
        }
        if (!context.function_coverage_enabled && !source.testcases().functions().is_empty())
            || (!context.branch_coverage_enabled && !source.testcases().branches().is_empty())
            || (!context.mcdc_coverage_enabled && !source.testcases().mcdc().is_empty())
        {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::DisabledFamily,
            );
        }
        if !context.checksum_output_enabled && !source.checksums().is_empty() {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::DisabledChecksum,
            );
        }
        if source
            .testcases()
            .functions()
            .keys()
            .any(|name| !line_names.contains_key(name))
            || source
                .testcases()
                .branches()
                .keys()
                .any(|name| !line_names.contains_key(name))
            || source
                .testcases()
                .mcdc()
                .keys()
                .any(|name| !line_names.contains_key(name))
        {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::FamilyWithoutLineMembership,
            );
        }
        let emitted_lines: std::collections::BTreeSet<_> = line_names
            .values()
            .flat_map(|coverage| coverage.iter().map(|(line, _)| line.clone()))
            .collect();
        if source
            .checksums()
            .keys()
            .any(|line| !emitted_lines.contains(line))
        {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::ChecksumWithoutLineMembership,
            );
        }
        let mut reconstructed = CoverageStore::new();
        for coverage in source.testcases().lines().values() {
            if reconstructed
                .lines_mut()
                .apply_op(AlgebraOp::Union, coverage)
                .is_err()
            {
                return ContractClassification::NonSerializable(
                    ContractNonSerializableReason::AlgebraFailure,
                );
            }
        }
        for coverage in source.testcases().functions().values() {
            if reconstructed
                .functions_mut()
                .apply_op(AlgebraOp::Union, coverage)
                .is_err()
            {
                return ContractClassification::NonSerializable(
                    ContractNonSerializableReason::AlgebraFailure,
                );
            }
        }
        for coverage in source.testcases().branches().values() {
            if reconstructed
                .branches_mut()
                .apply_op(AlgebraOp::Union, coverage)
                .is_err()
            {
                return ContractClassification::NonSerializable(
                    ContractNonSerializableReason::AlgebraFailure,
                );
            }
        }
        for coverage in source.testcases().mcdc().values() {
            if reconstructed
                .mcdc_mut()
                .apply_op(AlgebraOp::Union, coverage)
                .is_err()
            {
                return ContractClassification::NonSerializable(
                    ContractNonSerializableReason::AlgebraFailure,
                );
            }
        }
        if &reconstructed != source.aggregate() {
            return ContractClassification::NonSerializable(
                ContractNonSerializableReason::AggregateTestcaseDivergence,
            );
        }
    }
    ContractClassification::Serializable
}

fn classify_and_validate(
    parser: &StreamingParser,
    context: &SerializationContext<'_>,
) -> (Serializability, Option<ByteString>) {
    match classify_contract(parser, context) {
        ContractClassification::BlockedOracleUnknown => {
            (Serializability::BlockedOracleUnknown, None)
        }
        ContractClassification::NonSerializable(reason) => (
            Serializability::NonSerializable(NonSerializableReason::Contract(reason)),
            None,
        ),
        ContractClassification::Serializable => {
            let bytes = match write_canonical(parser.database(), context) {
                Ok(bytes) => bytes,
                Err(error) => {
                    return (
                        Serializability::NonSerializable(NonSerializableReason::Writer(error)),
                        None,
                    );
                }
            };
            let attempted = ByteString::new(bytes.clone());
            let mut reconstructed = StreamingParser::new();
            let _ = reconstructed.parse_all(&bytes);
            let clean = !reconstructed.stopped()
                && reconstructed.state().diagnostics().is_empty()
                && reconstructed.apply_context().open.is_none()
                && reconstructed.splitter_snapshot().buffered.is_empty()
                && !reconstructed.splitter_snapshot().pending_cr;
            if !clean {
                return (
                    Serializability::NonSerializable(NonSerializableReason::CanonicalParseRejected),
                    Some(attempted),
                );
            }
            if !SemanticSnapshot::capture(reconstructed.database())
                .semantically_equal(&SemanticSnapshot::capture(parser.database()))
            {
                return (
                    Serializability::NonSerializable(
                        NonSerializableReason::RoundTripSemanticMismatch,
                    ),
                    Some(attempted),
                );
            }
            match write_canonical(reconstructed.database(), context) {
                Err(error) => (
                    Serializability::NonSerializable(NonSerializableReason::SecondWriter(error)),
                    Some(attempted),
                ),
                Ok(second) if second != bytes => (
                    Serializability::NonSerializable(
                        NonSerializableReason::WriterFixedPointMismatch,
                    ),
                    Some(attempted),
                ),
                Ok(_) => (
                    Serializability::Serializable(attempted.clone()),
                    Some(attempted),
                ),
            }
        }
    }
}
