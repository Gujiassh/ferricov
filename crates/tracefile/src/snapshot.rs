//! Stable semantic snapshots for differential comparison.

use ferricov_model::{ByteString, CoverageDatabase};

use crate::{
    write_canonical, IgnorePolicy, OpenSection, ParserState, SerializationContext,
    SerializationError, StreamingParser,
};

/// Canonical output classification captured alongside semantic state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Serializability {
    /// Canonical output bytes for the supplied pure serialization context.
    Serializable(ByteString),
    /// Accepted semantic state that cannot be projected without information loss.
    Nonserializable(SerializationError),
}

/// Complete parser/model snapshot used by CORE-008 equality.
///
/// `CoverageDatabase` equality includes source lookup/display identity, version,
/// checksums, aggregate/testcase family maps (including absent versus explicit
/// empty values), function dual indexes, ordered branch/MC/DC structures,
/// numeric atoms, and observable totals.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticSnapshot {
    pub database: CoverageDatabase,
    pub parser_state: ParserState,
    pub open_section: Option<OpenSection>,
    pub ignore_policy: IgnorePolicy,
    pub stopped: bool,
    pub serializability: Serializability,
}

impl SemanticSnapshot {
    /// Capture committed and in-flight state without mutating the parser.
    #[must_use]
    pub fn capture(parser: &StreamingParser, context: &SerializationContext<'_>) -> Self {
        let serializability = match write_canonical(parser.database(), context) {
            Ok(bytes) => Serializability::Serializable(ByteString::new(bytes)),
            Err(error) => Serializability::Nonserializable(error),
        };
        Self {
            database: parser.database().clone(),
            parser_state: parser.state().clone(),
            open_section: parser.apply_context().open.clone(),
            ignore_policy: parser.apply_context().policy,
            stopped: parser.stopped(),
            serializability,
        }
    }

    /// Explicit semantic equality entry point for differential callers.
    #[must_use]
    pub fn semantically_equal(&self, other: &Self) -> bool {
        self == other
    }
}
