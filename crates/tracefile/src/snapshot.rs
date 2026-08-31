//! Model-semantic snapshots and parser/run evidence envelopes.
use crate::{
    write_canonical, IgnorePolicy, LineSplitterSnapshot, OpenSection, ParserState,
    SerializationContext, SerializationError, StreamingParser,
};
use ferricov_model::{ByteString, CoverageDatabase};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Serializability {
    Serializable(ByteString),
    Nonserializable(SerializationError),
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
    pub serializability: Serializability,
    pub process: Option<ProcessEvidence>,
}
impl EvidenceSnapshot {
    #[must_use]
    pub fn capture(parser: &StreamingParser, context: &SerializationContext<'_>) -> Self {
        let serializability = match write_canonical(parser.database(), context) {
            Ok(bytes) => Serializability::Serializable(ByteString::new(bytes)),
            Err(error) => Serializability::Nonserializable(error),
        };
        let source_provenance = parser
            .database()
            .iter()
            .map(|(key, source)| SourceProvenance {
                lookup_key: key.as_byte_string().clone(),
                diagnostic_path: source.identity().diagnostic_path().cloned(),
            })
            .collect();
        Self {
            semantic: SemanticSnapshot::capture(parser.database()),
            parser_state: parser.state().clone(),
            splitter: parser.splitter_snapshot(),
            open_section: parser.apply_context().open.clone(),
            ignore_policy: parser.apply_context().policy,
            stopped: parser.stopped(),
            source_provenance,
            serializability,
            process: None,
        }
    }
    #[must_use]
    pub fn semantically_equal(&self, other: &Self) -> bool {
        self.semantic.semantically_equal(&other.semantic)
    }
}
