//! Ignore / stop-on-error policy for ignorable parser diagnostics.
//!
//! Full Oracle ignore-category matrices remain residual; this module provides
//! the minimal continue-vs-stop switch CORE-006 needs for unit tests and hard
//! failures.

/// How the streaming parser treats ignorable (`ERROR_FORMAT`-class) diagnostics.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum IgnorePolicy {
    /// Record the diagnostic and continue applying subsequent records.
    ///
    /// Default for focused unit tests unless a case asserts hard-fail stop.
    #[default]
    Continue,
    /// Stop applying further records after the first ignorable diagnostic.
    Stop,
}

impl IgnorePolicy {
    /// Return `true` when parsing should stop after an ignorable diagnostic.
    #[must_use]
    pub const fn stops_on_ignorable(self) -> bool {
        matches!(self, Self::Stop)
    }
}
