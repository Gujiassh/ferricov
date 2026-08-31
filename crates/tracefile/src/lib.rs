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

pub use classify::{
    classify_line, LineClass, MatchAnchor, RecordTag, TnPayload,
};
pub use commit::{close_mcdc_block, commit_section, CommitOutcome};
pub use diag::{DiagClass, DiagKind, ParseDiag};
pub use line::{
    is_perl_ascii_ws, normalize_logical_line, strip_line_terminator, trim_trailing_perl_ws,
    LineEnding, LineSplitter, LineSplitterSnapshot, RawLogicalLine, PERL_ASCII_WS,
};
pub use parser::StreamingParser;
pub use policy::IgnorePolicy;
pub use records::{apply_event, ApplyContext, ApplyResult};
pub use section::{BranchCursor, OpenSection};
pub use snapshot::{EvidenceSnapshot, ProcessEvidence, SemanticSnapshot, Serializability, SourceProvenance};
pub use state::{
    is_perl_word_byte, sanitize_tn_base, ParseEvent, ParserState, SourceBinding, SourceTag,
};
pub use writer::{write_canonical, ChecksumProvider, SerializationContext, SerializationError, SourcePathProjection};

#[cfg(test)]
mod tests_core005;
#[cfg(test)]
mod tests_core006;
#[cfg(test)]
mod tests_core007;
#[cfg(test)]
mod tests_core008;
