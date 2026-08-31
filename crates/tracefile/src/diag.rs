//! Malformed-state / diagnostic classification for the logical-line layer.
//!
//! CORE-005 exposes explicit ignored-vs-hard-fail classes. CORE-006 adds
//! record-semantic categories and wires [`crate::policy::IgnorePolicy`].

use ferricov_model::ByteString;

/// Severity / continuation class for a parser diagnostic.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiagClass {
    /// Informational note; never stops parsing.
    Note,
    /// Oracle ignorable category (e.g. `ERROR_FORMAT`). Continuation depends on
    /// [`crate::policy::IgnorePolicy`].
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
    /// Conflicting second `VER` for the same source (unconditional die).
    VersionConflict,
    /// Duplicate current-format `FNL` index (unconditional die).
    DuplicateFnlIndex,
    /// `FNA` references an unknown `FNL` index (unconditional die).
    UnknownFnlIndex,
    /// `FNDA` references an undeclared function name (`ERROR_MISMATCH`).
    FunctionMismatch,
    /// Returning to a closed MC/DC source line (`MCDC already defined`).
    McdcAlreadyDefined,
    /// Inconsistent MC/DC expression for an existing index.
    InconsistentData,
    /// Generic deferred / unclassified semantic issue.
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
    pub fn error_format(
        line_no: u64,
        message: impl Into<String>,
        related: Option<ByteString>,
    ) -> Self {
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

    /// Hard-fail: conflicting second version for a source.
    #[must_use]
    pub fn version_conflict(
        line_no: u64,
        message: impl Into<String>,
        related: Option<ByteString>,
    ) -> Self {
        Self {
            kind: DiagKind::VersionConflict,
            class: DiagClass::HardFail,
            line_no,
            message: message.into(),
            related,
        }
    }

    /// Hard-fail: duplicate FNL index.
    #[must_use]
    pub fn duplicate_fnl(line_no: u64, message: impl Into<String>) -> Self {
        Self {
            kind: DiagKind::DuplicateFnlIndex,
            class: DiagClass::HardFail,
            line_no,
            message: message.into(),
            related: None,
        }
    }

    /// Hard-fail: FNA for unknown FNL index.
    #[must_use]
    pub fn unknown_fnl(line_no: u64, message: impl Into<String>) -> Self {
        Self {
            kind: DiagKind::UnknownFnlIndex,
            class: DiagClass::HardFail,
            line_no,
            message: message.into(),
            related: None,
        }
    }

    /// Ignorable function mismatch (`ERROR_MISMATCH`).
    #[must_use]
    pub fn function_mismatch(
        line_no: u64,
        message: impl Into<String>,
        related: Option<ByteString>,
    ) -> Self {
        Self {
            kind: DiagKind::FunctionMismatch,
            class: DiagClass::Ignorable,
            line_no,
            message: message.into(),
            related,
        }
    }

    /// Hard-fail: MC/DC already defined for a line.
    #[must_use]
    pub fn mcdc_already_defined(line_no: u64, message: impl Into<String>) -> Self {
        Self {
            kind: DiagKind::McdcAlreadyDefined,
            class: DiagClass::HardFail,
            line_no,
            message: message.into(),
            related: None,
        }
    }

    /// Ignorable inconsistent-data diagnostic.
    #[must_use]
    pub fn inconsistent_data(
        line_no: u64,
        message: impl Into<String>,
        related: Option<ByteString>,
    ) -> Self {
        Self {
            kind: DiagKind::InconsistentData,
            class: DiagClass::Ignorable,
            line_no,
            message: message.into(),
            related,
        }
    }

    /// Generic hard-fail helper.
    #[must_use]
    pub fn hard_fail(
        kind: DiagKind,
        line_no: u64,
        message: impl Into<String>,
        related: Option<ByteString>,
    ) -> Self {
        Self {
            kind,
            class: DiagClass::HardFail,
            line_no,
            message: message.into(),
            related,
        }
    }
}
