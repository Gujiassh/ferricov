//! Line coverage map for aggregate and testcase stores.
//!
//! CORE-002 provides an empty-capable `LineCoverage` container. Found/hit
//! derivation and algebra arrive in later CORE tasks.

use crate::keys::LineKey;
use crate::numeric::CoverageCount;
use std::collections::BTreeMap;

/// Map from [`LineKey`] to [`CoverageCount`].
///
/// An explicitly empty map is a first-class value: inserting an empty
/// [`LineCoverage`] into a testcase-family map keeps the test name present.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LineCoverage {
    entries: BTreeMap<LineKey, CoverageCount>,
}

impl LineCoverage {
    /// Create an empty line coverage map.
    #[must_use]
    pub fn new() -> Self {
        Self {
            entries: BTreeMap::new(),
        }
    }

    /// Return `true` when no line entries are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Number of stored line keys.
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Insert or replace a line count.
    pub fn insert(&mut self, key: LineKey, count: CoverageCount) -> Option<CoverageCount> {
        self.entries.insert(key, count)
    }

    /// Borrow the count for a line key.
    #[must_use]
    pub fn get(&self, key: &LineKey) -> Option<&CoverageCount> {
        self.entries.get(key)
    }

    /// Remove a line key and return its count when present.
    pub fn remove(&mut self, key: &LineKey) -> Option<CoverageCount> {
        self.entries.remove(key)
    }

    /// Return `true` when the map contains `key`.
    #[must_use]
    pub fn contains_key(&self, key: &LineKey) -> bool {
        self.entries.contains_key(key)
    }

    /// Iterate stored entries in key order.
    pub fn iter(&self) -> impl Iterator<Item = (&LineKey, &CoverageCount)> {
        self.entries.iter()
    }

    /// Borrow the underlying ordered map.
    #[must_use]
    pub fn as_map(&self) -> &BTreeMap<LineKey, CoverageCount> {
        &self.entries
    }

    /// Consume and return the underlying ordered map.
    #[must_use]
    pub fn into_map(self) -> BTreeMap<LineKey, CoverageCount> {
        self.entries
    }
}

impl FromIterator<(LineKey, CoverageCount)> for LineCoverage {
    fn from_iter<T: IntoIterator<Item = (LineKey, CoverageCount)>>(iter: T) -> Self {
        Self {
            entries: iter.into_iter().collect(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::LineCoverage;
    use crate::keys::LineKey;
    use crate::numeric::CoverageCount;

    #[test]
    fn empty_line_coverage_is_representable() {
        let empty = LineCoverage::new();
        assert!(empty.is_empty());
        assert_eq!(empty.len(), 0);
    }

    #[test]
    fn insert_and_get_preserve_zero_line_keys() {
        let mut lines = LineCoverage::new();
        let key = LineKey::from_lexeme("0");
        lines.insert(key.clone(), CoverageCount::from_lexeme("3"));
        assert!(lines.contains_key(&key));
        assert_eq!(
            lines.get(&key).map(CoverageCount::lexeme).map(|b| b.as_bytes()),
            Some(b"3".as_slice())
        );
    }
}
