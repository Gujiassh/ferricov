//! MC/DC coverage store stub for CORE-002.
//!
//! TODO(CORE-003): implement group-size keys, expression vectors, dual-sense
//! coverage, exclusions, and asymmetric compatibility checks from
//! `coverage-model.md` "MC/DC Coverage".

use crate::bytes::ByteString;
use crate::keys::LineKey;
use crate::numeric::CoverageCount;
use std::collections::BTreeMap;

/// Minimal empty-capable MC/DC coverage container.
///
/// CORE-002 only needs independent store membership and emptiness. Sense pairs,
/// group identity, and merge compatibility belong to CORE-003.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct McdcCoverage {
    /// Placeholder line → expression-count pairs. Not Oracle group identity.
    lines: BTreeMap<LineKey, Vec<(ByteString, CoverageCount)>>,
}

impl McdcCoverage {
    /// Create an empty MC/DC coverage store.
    #[must_use]
    pub fn new() -> Self {
        Self {
            lines: BTreeMap::new(),
        }
    }

    /// Return `true` when no MC/DC lines are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.lines.is_empty()
    }

    /// Number of lines that currently hold stub MC/DC entries.
    #[must_use]
    pub fn line_len(&self) -> usize {
        self.lines.len()
    }

    /// Insert or replace stub expression counts for a line.
    ///
    /// TODO(CORE-003): replace with `McdcLine` / `McdcExpression` / sense pairs.
    pub fn insert_line(
        &mut self,
        key: LineKey,
        expressions: Vec<(ByteString, CoverageCount)>,
    ) -> Option<Vec<(ByteString, CoverageCount)>> {
        self.lines.insert(key, expressions)
    }

    /// Borrow stub expression counts for a line.
    #[must_use]
    pub fn get_line(&self, key: &LineKey) -> Option<&Vec<(ByteString, CoverageCount)>> {
        self.lines.get(key)
    }

    /// Return `true` when the stub map contains `key`.
    #[must_use]
    pub fn contains_line(&self, key: &LineKey) -> bool {
        self.lines.contains_key(key)
    }

    /// Iterate stub lines in key order.
    pub fn lines(&self) -> impl Iterator<Item = (&LineKey, &Vec<(ByteString, CoverageCount)>)> {
        self.lines.iter()
    }
}
