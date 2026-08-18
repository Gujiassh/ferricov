//! Streaming LCOV tracefile parsing and serialization.
//!
//! # M1-CORE-005
//!
//! This crate currently delivers the **logical-line pipeline** and **binding
//! state** required before full record semantics (CORE-006):
//!
//! - byte-oriented line splitting (`\n` / `\r\n` / lone `\r`)
//! - Perl-compatible chomp + trailing ASCII `\s` normalization
//! - comment / empty / terminator / record / unclassified classification
//! - `TN` and `SF`/`KF` binding with late-TN semantics documented on
//!   [`ParserState`](state::ParserState)
//! - streaming [`StreamingParser`](parser::StreamingParser) API
//! - explicit malformed/diagnostic classes (no panic on arbitrary bytes)
//!
//! Canonical writing is CORE-007. Full apply of DA/FN/BRDA/MCDC is CORE-006.

#![forbid(unsafe_code)]

mod classify;
mod diag;
mod line;
mod parser;
mod state;

pub use classify::{
    classify_line, LineClass, MatchAnchor, RecordTag, TnPayload,
};
pub use diag::{DiagClass, DiagKind, ParseDiag};
pub use line::{
    is_perl_ascii_ws, normalize_logical_line, strip_line_terminator, trim_trailing_perl_ws,
    LineEnding, LineSplitter, RawLogicalLine, PERL_ASCII_WS,
};
pub use parser::StreamingParser;
pub use state::{
    is_perl_word_byte, sanitize_tn_base, ParseEvent, ParserState, SourceBinding, SourceTag,
};

#[cfg(test)]
mod tests_core005;
