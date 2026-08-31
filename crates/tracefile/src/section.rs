//! Open source-section working state for record apply and commit.
//!
//! Line / function / branch accumulate into the SF-bound testcase family.
//! MC/DC accumulates into an open block that closes onto the *current* test
//! name (`U-MCDC-LATE-TN`), not the SF-bound name.

use ferricov_model::{
    BranchCoverage, ByteString, FunctionTable, LineCoverage, McdcCoverage, SourceIdentity, TestName,
};
use std::collections::BTreeMap;

use crate::state::SourceBinding;

/// Working buffers for one open `SF`/`KF` section.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenSection {
    /// Source binding captured at `SF`/`KF`.
    pub binding: SourceBinding,
    /// Optional `VER` payload for this source (source-scoped).
    pub version: Option<ByteString>,
    /// Line checksums keyed by line lexeme (source-scoped).
    pub checksums: BTreeMap<ferricov_model::LineKey, ByteString>,
    /// Line map for the SF-bound test name (current section contribution).
    pub lines: LineCoverage,
    /// Function table for the SF-bound test name.
    pub functions: FunctionTable,
    /// Branch coverage for the SF-bound test name.
    pub branches: BranchCoverage,
    /// Open MC/DC block (closed onto current TN at terminator / line change).
    pub mcdc_open: McdcCoverage,
    /// Whether the open MC/DC block has been closed onto a testcase already.
    pub mcdc_closed: bool,
    /// Last MC/DC source line that received a record (contiguous-line rule).
    pub mcdc_current_line: Option<ferricov_model::LineKey>,
    /// Closed MC/DC line keys for this section (hard-fail on revisit).
    pub mcdc_closed_lines: BTreeMap<ferricov_model::LineKey, ()>,
    /// Current-format FNL index → (start, optional end).
    pub fnl_index: BTreeMap<u64, (ferricov_model::LineKey, Option<ferricov_model::LineKey>)>,
    /// Branch reader: last input (line, block-token) for contiguous blocks.
    pub branch_cursor: Option<BranchCursor>,
}

/// Branch construction cursor (input block token boundaries).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BranchCursor {
    pub line: ferricov_model::LineKey,
    pub block_token: ByteString,
}

impl OpenSection {
    /// Start a new open section from a source binding.
    #[must_use]
    pub fn new(binding: SourceBinding) -> Self {
        Self {
            binding,
            version: None,
            checksums: BTreeMap::new(),
            lines: LineCoverage::new(),
            functions: FunctionTable::new(),
            branches: BranchCoverage::new(),
            mcdc_open: McdcCoverage::new(),
            mcdc_closed: false,
            mcdc_current_line: None,
            mcdc_closed_lines: BTreeMap::new(),
            fnl_index: BTreeMap::new(),
            branch_cursor: None,
        }
    }

    /// SF-bound test name used for line/function/branch maps.
    #[must_use]
    pub fn bound_test_name(&self) -> &TestName {
        &self.binding.bound_test_name
    }

    /// Source identity for database lookup.
    #[must_use]
    pub fn identity(&self) -> &SourceIdentity {
        &self.binding.identity
    }

    /// Whether this section carries any semantic payload beyond its binding.
    #[must_use]
    pub fn has_semantic_payload(&self) -> bool {
        self.version.is_some()
            || !self.checksums.is_empty()
            || !self.lines.is_empty()
            || !self.functions.is_empty()
            || !self.branches.is_empty()
            || !self.mcdc_open.is_empty()
    }
}
