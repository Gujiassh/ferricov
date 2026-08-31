//! Streaming LCOV tracefile parsing and serialization.
//!
//! # M1-CORE-005 / M1-CORE-006
//!
//! - byte-oriented line splitting (`\n` / `\r\n` / lone `\r`)
//! - Perl-compatible chomp + trailing ASCII `\s` normalization
//! - comment / empty / terminator / record / unclassified classification
//! - `TN` and `SF`/`KF` binding with late-TN semantics
//! - record apply for all 20 tags onto [`CoverageDatabase`](ferricov_model::CoverageDatabase)
//! - section commit on `end_of_record` (line/function/branch union; MC/DC late-TN close)
//! - streaming [`StreamingParser`](parser::StreamingParser) with `database()` / `into_database()`
//!
//! Canonical writing is CORE-007.

#![forbid(unsafe_code)]

mod classify;
mod commit;
mod diag;
mod line;
mod parser;
mod policy;
mod record_parse;
mod records;
mod section;
mod snapshot;
mod state;
mod writer;

pub use classify::{LineClass, MatchAnchor, RecordTag, TnPayload, classify_line};
pub use commit::{CommitOutcome, close_mcdc_block, commit_section};
pub use diag::{DiagClass, DiagKind, ParseDiag};
pub use line::{
    LineEnding, LineSplitter, LineSplitterSnapshot, PERL_ASCII_WS, RawLogicalLine,
    is_perl_ascii_ws, normalize_logical_line, strip_line_terminator, trim_trailing_perl_ws,
};
pub use parser::StreamingParser;
pub use policy::IgnorePolicy;
pub use records::{ApplyContext, ApplyResult, apply_event};
pub use section::{BranchCursor, OpenSection};
pub use snapshot::{
    ContractClassification, ContractNonSerializableReason, EvidenceSnapshot, NonSerializableReason,
    ProcessEvidence, SemanticSnapshot, Serializability, SourceBindingProvenance, SourceProvenance,
    TestNameProvenance, TestcaseFamily, TestcaseNameProvenance, classify_contract,
};
pub use state::{
    ParseEvent, ParserState, SourceBinding, SourceTag, is_perl_word_byte, sanitize_tn_base,
};
pub use writer::{
    ChecksumProvider, SerializationContext, SerializationError, SourcePathProjection,
    write_canonical,
};

#[cfg(test)]
mod tests_core005;
#[cfg(test)]
mod tests_core006;
#[cfg(test)]
mod tests_core007;
#[cfg(test)]
mod tests_core008;
