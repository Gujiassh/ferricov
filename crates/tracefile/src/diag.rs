//! Malformed-state / diagnostic classification for the logical-line layer.
//!
//! CORE-005 exposes explicit ignored-vs-hard-fail classes where the grammar is
//! already clear for this slice. Full ignore-policy / stop-on-error wiring is
//! CORE-006+.

use ferricov_model::ByteString;

/// Severity / continuation class for a parser diagnostic.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiagClass {
    /// Informational note; never stops parsing.
    Note,
    /// Oracle ignorable category (e.g. `ERROR_FORMAT`). Continuation depends on
    /// ignore / stop-on-error policy (policy application is CORE-006+).
    Ignorable,
    /// Unconditional hard failure in the Oracle (`die` / non-ignorable).
    HardFail,
}

/// Stable diagnostic category names aligned with Oracle error tokens where known.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DiagKind {
    /// Unrecognized nonblank noncomment line (`ERROR_FORMAT`).
    ErrorFormat,
    /// Empty / whitespace-only `SF`/`KF` payload (`ERROR_FORMAT`, marks skip).
    EmptySourcePath,
    /// Test name `\W` sanitization warning (`ERROR_FORMAT` warning after parse).
    TestNameSanitized,
    /// Placeholder for categories CORE-006 will emit (negative, mismatch, …).
    Deferred,
}

/// One diagnostic event produced while feeding the parser.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseDiag {
    /// Category.
    pub kind: DiagKind,
    /// Ignorable vs hard-fail vs note.
    pub class: DiagClass,
    /// 1-based logical line number within the current feed (best-effort).
    pub line_no: u64,
    /// Human-readable message (English); not an Oracle byte-identical stream.
    pub message: String,
    /// Optional related raw / normalized bytes for provenance.
    pub related: Option<ByteString>,
}

impl ParseDiag {
    /// Construct an ignorable `ERROR_FORMAT` diagnostic.
    #[must_use]
    pub fn error_format(line_no: u64, message: impl Into<String>, related: Option<ByteString>) -> Self {
        Self {
            kind: DiagKind::ErrorFormat,
            class: DiagClass::Ignorable,
            line_no,
            message: message.into(),
            related,
        }
    }

    /// Construct an empty-source-path diagnostic (ignorable `ERROR_FORMAT`).
    #[must_use]
    pub fn empty_source_path(line_no: u64, related: ByteString) -> Self {
        Self {
            kind: DiagKind::EmptySourcePath,
            class: DiagClass::Ignorable,
            line_no,
            message: "unexpected empty file name in SF/KF record".into(),
            related: Some(related),
        }
    }

    /// Construct a test-name sanitization warning note.
    #[must_use]
    pub fn test_name_sanitized(line_no: u64, original: ByteString, sanitized: ByteString) -> Self {
        Self {
            kind: DiagKind::TestNameSanitized,
            class: DiagClass::Note,
            line_no,
            message: format!(
                "invalid characters removed from testname: '{}'->'{}'",
                original.to_string_lossy(),
                sanitized.to_string_lossy()
            ),
            related: Some(original),
        }
    }
}
