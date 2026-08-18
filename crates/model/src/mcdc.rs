//! Hierarchical MC/DC coverage with dual-sense sticky exclusion.
//!
//! Normative layout comes from `coverage-model.md` "MC/DC Coverage".
//! Asymmetric vector merge algebra is deferred (`M1-ALG-MCDC-*`).

use crate::bytes::ByteString;
use crate::keys::LineKey;
use crate::numeric::{AddError, CoverageCount, NumericAtom};
use std::collections::BTreeMap;
use std::fmt;

/// Explicit group-size key. Not a plain `u64`.
///
/// Wraps [`NumericAtom`] so Oracle-retained spellings (including ignored-error
/// states) remain representable. Map order is by retained lexeme bytes.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct GroupSizeKey {
    atom: NumericAtom,
}

impl PartialOrd for GroupSizeKey {
    fn partial_cmp(&self, other: &Self) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for GroupSizeKey {
    fn cmp(&self, other: &Self) -> core::cmp::Ordering {
        self.atom.lexeme().cmp(other.atom.lexeme())
    }
}

impl GroupSizeKey {
    /// Construct from an explicit numeric atom.
    #[must_use]
    pub fn from_atom(atom: NumericAtom) -> Self {
        Self { atom }
    }

    /// Construct from a raw group-size lexeme.
    #[must_use]
    pub fn from_lexeme(lexeme: impl Into<ByteString>) -> Self {
        Self::from_atom(NumericAtom::from_lexeme(lexeme))
    }

    /// Borrow the retained numeric atom.
    #[must_use]
    pub fn atom(&self) -> &NumericAtom {
        &self.atom
    }

    /// Borrow the original lexeme bytes.
    #[must_use]
    pub fn lexeme(&self) -> &ByteString {
        self.atom.lexeme()
    }
}

/// One sense (false or true) of an MC/DC expression.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SenseCoverage {
    count: CoverageCount,
    excluded: bool,
}

impl SenseCoverage {
    /// Unseen sense: zero count, not excluded.
    #[must_use]
    pub fn unseen() -> Self {
        Self {
            count: CoverageCount::zero(),
            excluded: false,
        }
    }

    /// Construct with explicit count and exclusion.
    #[must_use]
    pub fn new(count: CoverageCount, excluded: bool) -> Self {
        Self { count, excluded }
    }

    /// Borrow the sense count.
    #[must_use]
    pub fn count(&self) -> &CoverageCount {
        &self.count
    }

    /// Whether this sense is excluded.
    #[must_use]
    pub fn is_excluded(&self) -> bool {
        self.excluded
    }

    /// Sticky exclusion: once set, never clears via this API.
    pub fn set_excluded(&mut self) {
        self.excluded = true;
    }

    /// Add to the sense count. Exclusion is unchanged unless `exclude` is true.
    ///
    /// When `exclude` is `true`, sticky exclusion is set and never cleared.
    pub fn set(&mut self, count: CoverageCount, exclude: bool) -> Result<(), AddError> {
        if exclude {
            self.excluded = true;
        }
        if count.is_zero() {
            return Ok(());
        }
        self.count = self.count.add(&count)?;
        Ok(())
    }

    /// Replace the count without clearing sticky exclusion.
    pub fn set_count(&mut self, count: CoverageCount) {
        self.count = count;
    }
}

impl Default for SenseCoverage {
    fn default() -> Self {
        Self::unseen()
    }
}

/// One MC/DC expression with both senses always present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McdcExpression {
    stored_position: usize,
    declared_index: NumericAtom,
    expression: ByteString,
    false_sense: SenseCoverage,
    true_sense: SenseCoverage,
}

impl McdcExpression {
    /// Create an expression with both senses unseen (zero, not excluded).
    #[must_use]
    pub fn new(
        stored_position: usize,
        declared_index: NumericAtom,
        expression: impl Into<ByteString>,
    ) -> Self {
        Self {
            stored_position,
            declared_index,
            expression: expression.into(),
            false_sense: SenseCoverage::unseen(),
            true_sense: SenseCoverage::unseen(),
        }
    }

    /// Contiguous stored position in the group vector.
    #[must_use]
    pub fn stored_position(&self) -> usize {
        self.stored_position
    }

    /// Declared index atom retained for provenance / diagnostics.
    #[must_use]
    pub fn declared_index(&self) -> &NumericAtom {
        &self.declared_index
    }

    /// Expression identity bytes (not an AST).
    #[must_use]
    pub fn expression(&self) -> &ByteString {
        &self.expression
    }

    /// Borrow the false sense.
    #[must_use]
    pub fn false_sense(&self) -> &SenseCoverage {
        &self.false_sense
    }

    /// Borrow the true sense.
    #[must_use]
    pub fn true_sense(&self) -> &SenseCoverage {
        &self.true_sense
    }

    /// Mutable false sense.
    pub fn false_sense_mut(&mut self) -> &mut SenseCoverage {
        &mut self.false_sense
    }

    /// Mutable true sense.
    pub fn true_sense_mut(&mut self) -> &mut SenseCoverage {
        &mut self.true_sense
    }

    /// Apply a sense update with sticky exclusion semantics.
    pub fn set_sense(
        &mut self,
        true_sense: bool,
        count: CoverageCount,
        excluded: bool,
    ) -> Result<(), AddError> {
        if true_sense {
            self.true_sense.set(count, excluded)
        } else {
            self.false_sense.set(count, excluded)
        }
    }
}

/// MC/DC groups on a single line: at most one vector per [`GroupSizeKey`].
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct McdcLine {
    groups: BTreeMap<GroupSizeKey, Vec<McdcExpression>>,
}

impl McdcLine {
    /// Create an empty MC/DC line.
    #[must_use]
    pub fn new() -> Self {
        Self {
            groups: BTreeMap::new(),
        }
    }

    /// Return `true` when no groups are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.groups.is_empty()
    }

    /// Number of group-size keys on this line.
    #[must_use]
    pub fn group_len(&self) -> usize {
        self.groups.len()
    }

    /// Borrow groups map.
    #[must_use]
    pub fn groups(&self) -> &BTreeMap<GroupSizeKey, Vec<McdcExpression>> {
        &self.groups
    }

    /// Borrow the expression vector for a group-size key.
    #[must_use]
    pub fn get_group(&self, key: &GroupSizeKey) -> Option<&Vec<McdcExpression>> {
        self.groups.get(key)
    }

    /// Mutable expression vector for a group-size key.
    pub fn get_group_mut(&mut self, key: &GroupSizeKey) -> Option<&mut Vec<McdcExpression>> {
        self.groups.get_mut(key)
    }

    /// Ensure a group exists for `key` and return the mutable vector.
    ///
    /// At most one group per size key: repeated calls return the same vector.
    pub fn entry_group(&mut self, key: GroupSizeKey) -> &mut Vec<McdcExpression> {
        self.groups.entry(key).or_default()
    }

    /// Append an expression to the group for `key`, assigning `stored_position`.
    ///
    /// Declared index is retained for provenance; stored order is contiguous.
    pub fn append_expression(
        &mut self,
        key: GroupSizeKey,
        declared_index: NumericAtom,
        expression: impl Into<ByteString>,
    ) -> &mut McdcExpression {
        let group = self.groups.entry(key).or_default();
        let pos = group.len();
        group.push(McdcExpression::new(pos, declared_index, expression));
        group.last_mut().expect("just pushed")
    }

    /// Iterate groups in key order.
    pub fn iter_groups(&self) -> impl Iterator<Item = (&GroupSizeKey, &Vec<McdcExpression>)> {
        self.groups.iter()
    }
}

/// Errors from MC/DC invariant checks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum McdcError {
    /// Structural invariant failed.
    Invariant(String),
}

impl fmt::Display for McdcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invariant(msg) => write!(f, "mcdc invariant: {msg}"),
        }
    }
}

impl std::error::Error for McdcError {}

/// Line-keyed hierarchical MC/DC coverage.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct McdcCoverage {
    lines: BTreeMap<LineKey, McdcLine>,
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

    /// Number of lines that currently hold MC/DC data.
    #[must_use]
    pub fn line_len(&self) -> usize {
        self.lines.len()
    }

    /// Insert or replace a full [`McdcLine`].
    pub fn insert_line(&mut self, key: LineKey, line: McdcLine) -> Option<McdcLine> {
        self.lines.insert(key, line)
    }

    /// Ensure a line exists and return a mutable reference.
    pub fn entry_line(&mut self, key: LineKey) -> &mut McdcLine {
        self.lines.entry(key).or_default()
    }

    /// Borrow an MC/DC line.
    #[must_use]
    pub fn get_line(&self, key: &LineKey) -> Option<&McdcLine> {
        self.lines.get(key)
    }

    /// Mutable borrow of an MC/DC line.
    pub fn get_line_mut(&mut self, key: &LineKey) -> Option<&mut McdcLine> {
        self.lines.get_mut(key)
    }

    /// Return `true` when the map contains `key`.
    #[must_use]
    pub fn contains_line(&self, key: &LineKey) -> bool {
        self.lines.contains_key(key)
    }

    /// Iterate lines in key order.
    pub fn lines(&self) -> impl Iterator<Item = (&LineKey, &McdcLine)> {
        self.lines.iter()
    }

    /// Assert both-senses and stored_position invariants.
    pub fn assert_invariants(&self) -> Result<(), McdcError> {
        for (line_key, line) in &self.lines {
            for (group_key, exprs) in line.iter_groups() {
                for (idx, expr) in exprs.iter().enumerate() {
                    if expr.stored_position() != idx {
                        return Err(McdcError::Invariant(format!(
                            "line {} group {}: stored_position {} != vector index {}",
                            line_key.lexeme(),
                            group_key.lexeme(),
                            expr.stored_position(),
                            idx
                        )));
                    }
                    // Both senses always exist by construction; verify unseen
                    // defaults are representable (counts readable).
                    let _ = expr.false_sense().count();
                    let _ = expr.true_sense().count();
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{GroupSizeKey, McdcCoverage, McdcLine, SenseCoverage};
    use crate::keys::LineKey;
    use crate::numeric::{CoverageCount, NumericAtom};

    #[test]
    fn both_senses_present_sticky_exclusion_and_one_group_per_size() {
        let mut line = McdcLine::new();
        let size = GroupSizeKey::from_lexeme("2");
        {
            let expr = line.append_expression(
                size.clone(),
                NumericAtom::from_lexeme("0"),
                "a",
            );
            assert!(!expr.false_sense().is_excluded());
            assert!(!expr.true_sense().is_excluded());
            assert!(expr.false_sense().count().is_zero());
            assert!(expr.true_sense().count().is_zero());

            expr.set_sense(true, CoverageCount::from_lexeme("1"), true)
                .unwrap();
            assert!(expr.true_sense().is_excluded());
            assert_eq!(expr.true_sense().count().lexeme().as_bytes(), b"1");

            // sticky: later set with exclude=false must not clear
            expr.set_sense(true, CoverageCount::from_lexeme("2"), false)
                .unwrap();
            assert!(expr.true_sense().is_excluded());
            assert_eq!(expr.true_sense().count().lexeme().as_bytes(), b"3");
        }

        // same size key → same group (one vector)
        line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "b");
        assert_eq!(line.group_len(), 1);
        assert_eq!(line.get_group(&size).unwrap().len(), 2);

        // different size → second group
        line.append_expression(
            GroupSizeKey::from_lexeme("3"),
            NumericAtom::from_lexeme("0"),
            "c",
        );
        assert_eq!(line.group_len(), 2);

        // SenseCoverage::set sticky unit
        let mut sense = SenseCoverage::unseen();
        sense.set(CoverageCount::zero(), true).unwrap();
        assert!(sense.is_excluded());
        sense.set(CoverageCount::from_lexeme("1"), false).unwrap();
        assert!(sense.is_excluded());
    }

    #[test]
    fn expression_stored_position_order_retained() {
        let mut coverage = McdcCoverage::new();
        let key = LineKey::from_lexeme("7");
        let line = coverage.entry_line(key.clone());
        let size = GroupSizeKey::from_lexeme("2");
        // declared indexes may have a gap; stored positions are contiguous
        line.append_expression(size.clone(), NumericAtom::from_lexeme("0"), "first");
        line.append_expression(size.clone(), NumericAtom::from_lexeme("2"), "third-declared");
        line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "second-declared");

        let exprs = coverage.get_line(&key).unwrap().get_group(&size).unwrap();
        assert_eq!(exprs.len(), 3);
        assert_eq!(exprs[0].stored_position(), 0);
        assert_eq!(exprs[1].stored_position(), 1);
        assert_eq!(exprs[2].stored_position(), 2);
        assert_eq!(exprs[0].expression().as_bytes(), b"first");
        assert_eq!(exprs[1].declared_index().lexeme().as_bytes(), b"2");
        assert_eq!(exprs[2].declared_index().lexeme().as_bytes(), b"1");
        coverage.assert_invariants().unwrap();
    }
}
