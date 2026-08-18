//! Branch coverage store stub for CORE-002.
//!
//! TODO(CORE-003): implement ordered blocks, signatures, edge indexes,
//! exclusion retention, and model-vs-canonical order from
//! `coverage-model.md` "Ordered Branch Coverage".

use crate::branch::BranchTaken;
use crate::keys::LineKey;
use std::collections::BTreeMap;

/// Minimal empty-capable branch coverage container.
///
/// CORE-002 only preserves independent emptiness and line-keyed presence. Full
/// hierarchical block/edge invariants belong to CORE-003.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BranchCoverage {
    /// Placeholder line → taken sequence. Not Oracle block identity.
    lines: BTreeMap<LineKey, Vec<BranchTaken>>,
}

impl BranchCoverage {
    /// Create an empty branch coverage store.
    #[must_use]
    pub fn new() -> Self {
        Self {
            lines: BTreeMap::new(),
        }
    }

    /// Return `true` when no branch lines are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.lines.is_empty()
    }

    /// Number of lines that currently hold stub branch entries.
    #[must_use]
    pub fn line_len(&self) -> usize {
        self.lines.len()
    }

    /// Insert or replace stub taken values for a line.
    ///
    /// TODO(CORE-003): replace with ordered `BranchLine` / `BranchBlock`
    /// construction driven by parser transition state.
    pub fn insert_line(
        &mut self,
        key: LineKey,
        taken: Vec<BranchTaken>,
    ) -> Option<Vec<BranchTaken>> {
        self.lines.insert(key, taken)
    }

    /// Borrow stub taken values for a line.
    #[must_use]
    pub fn get_line(&self, key: &LineKey) -> Option<&Vec<BranchTaken>> {
        self.lines.get(key)
    }

    /// Return `true` when the stub map contains `key`.
    #[must_use]
    pub fn contains_line(&self, key: &LineKey) -> bool {
        self.lines.contains_key(key)
    }

    /// Iterate stub lines in key order.
    pub fn lines(&self) -> impl Iterator<Item = (&LineKey, &Vec<BranchTaken>)> {
        self.lines.iter()
    }
}
