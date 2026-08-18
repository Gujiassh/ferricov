//! Function coverage table stub for CORE-002 stores.
//!
//! TODO(CORE-003): implement coherent start-location and alias indexes,
//! representative selection, range retention, and found/hit views described in
//! `coverage-model.md` "Functions And Aliases".

use crate::bytes::ByteString;
use crate::keys::LineKey;
use crate::numeric::CoverageCount;
use std::collections::BTreeMap;

/// Minimal empty-capable function coverage container.
///
/// CORE-002 only needs independent store membership and emptiness. Full alias
/// index invariants belong to CORE-003.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FunctionTable {
    /// Placeholder alias → count map. Not a claim of CORE-003 coherence.
    aliases: BTreeMap<ByteString, CoverageCount>,
    /// Optional retained start keys observed while stubbing; unused by algebra.
    starts: BTreeMap<LineKey, ByteString>,
}

impl FunctionTable {
    /// Create an empty function table.
    #[must_use]
    pub fn new() -> Self {
        Self {
            aliases: BTreeMap::new(),
            starts: BTreeMap::new(),
        }
    }

    /// Return `true` when no aliases or starts are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.aliases.is_empty() && self.starts.is_empty()
    }

    /// Number of stored aliases in this stub.
    #[must_use]
    pub fn alias_len(&self) -> usize {
        self.aliases.len()
    }

    /// Insert or replace a stub alias count.
    ///
    /// TODO(CORE-003): replace with group-aware insert that keeps location and
    /// alias indexes coherent.
    pub fn insert_alias(
        &mut self,
        alias: impl Into<ByteString>,
        count: CoverageCount,
    ) -> Option<CoverageCount> {
        self.aliases.insert(alias.into(), count)
    }

    /// Borrow a stub alias count.
    #[must_use]
    pub fn get_alias(&self, alias: &ByteString) -> Option<&CoverageCount> {
        self.aliases.get(alias)
    }

    /// Return `true` when the stub alias map contains `alias`.
    #[must_use]
    pub fn contains_alias(&self, alias: &ByteString) -> bool {
        self.aliases.contains_key(alias)
    }

    /// Iterate stub aliases in lexical order.
    pub fn aliases(&self) -> impl Iterator<Item = (&ByteString, &CoverageCount)> {
        self.aliases.iter()
    }
}
