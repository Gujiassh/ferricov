//! Function coverage table with coherent location and alias indexes.
//!
//! Normative behavior comes from `coverage-model.md` "Functions And Aliases".
//! Ordered algebra lives in `algebra.rs` (CORE-004).

use crate::bytes::ByteString;
use crate::keys::LineKey;
use crate::numeric::{AddError, CoverageCount};
use std::collections::BTreeMap;
use std::fmt;

/// Errors from function-table mutations that would break index coherence or
/// Oracle-visible conflict rules.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FunctionError {
    /// Alias already belongs to a different start location.
    AliasStartConflict {
        alias: ByteString,
        existing_start: LineKey,
        requested_start: LineKey,
    },
    /// Count addition failed (unsupported operand class / promotion).
    CountAdd(AddError),
    /// Alias reverse index pointed at a missing start group.
    OrphanAlias { alias: ByteString, start: LineKey },
    /// Start index and alias reverse index disagree.
    IndexIncoherent(String),
}

impl fmt::Display for FunctionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::AliasStartConflict {
                alias,
                existing_start,
                requested_start,
            } => write!(
                f,
                "alias {alias} already at start {} but requested {}",
                existing_start.lexeme(),
                requested_start.lexeme()
            ),
            Self::CountAdd(err) => write!(f, "function alias count add failed: {err:?}"),
            Self::OrphanAlias { alias, start } => {
                write!(
                    f,
                    "alias {alias} reverse-index points to missing start {}",
                    start.lexeme()
                )
            }
            Self::IndexIncoherent(msg) => write!(f, "function index incoherent: {msg}"),
        }
    }
}

impl std::error::Error for FunctionError {}

/// One function group at a start location, with aliases and optional end.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FunctionGroup {
    start: LineKey,
    end: Option<LineKey>,
    aliases: BTreeMap<ByteString, CoverageCount>,
    representative: ByteString,
}

impl FunctionGroup {
    /// Create a group with a single alias at zero count.
    #[must_use]
    pub fn new(start: LineKey, alias: impl Into<ByteString>, end: Option<LineKey>) -> Self {
        let alias = alias.into();
        let mut aliases = BTreeMap::new();
        aliases.insert(alias.clone(), CoverageCount::zero());
        Self {
            start,
            end,
            aliases,
            representative: alias,
        }
    }

    /// Borrow the group start location (may be zero / ignored-error state).
    #[must_use]
    pub fn start(&self) -> &LineKey {
        &self.start
    }

    /// Borrow the optional end location (may be zero or before start).
    #[must_use]
    pub fn end(&self) -> Option<&LineKey> {
        self.end.as_ref()
    }

    /// Set or clear the optional end without writer diagnostics.
    pub fn set_end(&mut self, end: Option<LineKey>) {
        self.end = end;
    }

    /// Borrow the representative alias name.
    #[must_use]
    pub fn representative(&self) -> &ByteString {
        &self.representative
    }

    /// Borrow the alias → count map.
    #[must_use]
    pub fn aliases(&self) -> &BTreeMap<ByteString, CoverageCount> {
        &self.aliases
    }

    /// Replace the alias count map wholesale (algebra rebuild helpers).
    ///
    /// Caller must refresh representative and keep table indexes coherent.
    pub fn set_aliases_for_algebra(
        &mut self,
        aliases: BTreeMap<ByteString, CoverageCount>,
        representative: ByteString,
    ) {
        self.aliases = aliases;
        self.representative = representative;
    }

    /// Number of aliases in this group.
    #[must_use]
    pub fn alias_len(&self) -> usize {
        self.aliases.len()
    }

    /// Sum of all alias counts. Returns the first add error if any.
    pub fn total_count(&self) -> Result<CoverageCount, AddError> {
        let mut total = CoverageCount::zero();
        for count in self.aliases.values() {
            total = total.add(count)?;
        }
        Ok(total)
    }

    /// Return `true` when any alias count is strictly positive.
    #[must_use]
    pub fn is_hit(&self) -> bool {
        self.aliases.values().any(CoverageCount::is_positive)
    }

    /// Insert or add an alias count and refresh representative on first insert.
    pub fn add_alias(
        &mut self,
        alias: impl Into<ByteString>,
        count: CoverageCount,
    ) -> Result<bool, AddError> {
        let alias = alias.into();
        if let Some(existing) = self.aliases.get_mut(&alias) {
            *existing = existing.add(&count)?;
            return Ok(false);
        }
        self.aliases.insert(alias.clone(), count);
        self.refresh_representative_on_insert(&alias);
        Ok(true)
    }

    /// Remove an alias. Returns the prior count when present.
    ///
    /// When the removed alias was the representative, recomputes a defined
    /// survivor using shortest-effective-length then lexical order. Oracle
    /// `removeAliases` can disagree on equal-length ties (`M1-ALG-FUNCTION-REP-001`).
    pub fn remove_alias(&mut self, alias: &ByteString) -> Option<CoverageCount> {
        let prior = self.aliases.remove(alias)?;
        if self.aliases.is_empty() {
            // Representative is undefined on an empty group; keep last name only
            // long enough for the caller to drop the group.
            return Some(prior);
        }
        if self.representative == *alias {
            self.recompute_representative_after_removal();
        }
        Some(prior)
    }

    /// Defined post-removal representative: shortest effective length, then
    /// lexical bytes among remaining aliases.
    ///
    /// This is Ferricov's documented CORE-004 behavior. Exact Oracle hash-seed
    /// / non-lexical survivor selection remains `M1-ALG-FUNCTION-REP-001`.
    pub fn recompute_representative_after_removal(&mut self) {
        let mut best: Option<&ByteString> = None;
        let mut best_len = usize::MAX;
        for alias in self.aliases.keys() {
            let len = effective_alias_length(alias.as_bytes());
            if best.is_none()
                || len < best_len
                || (len == best_len && alias.as_bytes() < best.expect("checked").as_bytes())
            {
                best = Some(alias);
                best_len = len;
            }
        }
        if let Some(alias) = best {
            self.representative = alias.clone();
        }
    }

    /// Recompute representative using insertion tie-break (shortest + lexical).
    fn refresh_representative_on_insert(&mut self, new_alias: &ByteString) {
        let cur = &self.representative;
        let cur_len = effective_alias_length(cur.as_bytes());
        let new_len = effective_alias_length(new_alias.as_bytes());
        if new_len < cur_len || (new_len == cur_len && new_alias.as_bytes() < cur.as_bytes()) {
            self.representative = new_alias.clone();
        }
    }
}

/// Return `true` when the alias matches Oracle lambda patterns.
///
/// Upstream `FunctionEntry::addAlias` penalizes names matching
/// `/{lambda(|.lambda$/`.
#[must_use]
pub fn is_lambda_alias(alias: &[u8]) -> bool {
    contains_slice(alias, b"{lambda(") || contains_slice(alias, b".lambda$")
}

/// Effective length used for representative selection (lambda penalty +1000).
#[must_use]
pub fn effective_alias_length(alias: &[u8]) -> usize {
    let base = alias.len();
    if is_lambda_alias(alias) {
        base.saturating_add(1000)
    } else {
        base
    }
}

fn contains_slice(haystack: &[u8], needle: &[u8]) -> bool {
    haystack
        .windows(needle.len())
        .any(|window| window == needle)
}

/// Function coverage with coherent start-location and alias reverse indexes.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FunctionTable {
    by_start: BTreeMap<LineKey, FunctionGroup>,
    /// Alias name → start location of its owning group.
    by_alias: BTreeMap<ByteString, LineKey>,
}

impl FunctionTable {
    /// Create an empty function table.
    #[must_use]
    pub fn new() -> Self {
        Self {
            by_start: BTreeMap::new(),
            by_alias: BTreeMap::new(),
        }
    }

    /// Return `true` when no groups are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.by_start.is_empty()
    }

    /// Number of function groups (start locations).
    #[must_use]
    pub fn group_len(&self) -> usize {
        self.by_start.len()
    }

    /// Number of stored aliases across all groups.
    #[must_use]
    pub fn alias_len(&self) -> usize {
        self.by_alias.len()
    }

    /// Group-level found count (number of groups).
    #[must_use]
    pub fn group_found(&self) -> usize {
        self.by_start.len()
    }

    /// Group-level hit count (groups with any positive alias).
    #[must_use]
    pub fn group_hit(&self) -> usize {
        self.by_start.values().filter(|g| g.is_hit()).count()
    }

    /// Alias-level found count.
    #[must_use]
    pub fn alias_found(&self) -> usize {
        self.by_alias.len()
    }

    /// Alias-level hit count (aliases with positive count).
    #[must_use]
    pub fn alias_hit(&self) -> usize {
        self.by_start
            .values()
            .flat_map(|g| g.aliases().values())
            .filter(|c| c.is_positive())
            .count()
    }

    /// Borrow a group by start location.
    #[must_use]
    pub fn get_by_start(&self, start: &LineKey) -> Option<&FunctionGroup> {
        self.by_start.get(start)
    }

    /// Borrow a group by alias name via the reverse index.
    #[must_use]
    pub fn get_by_alias(&self, alias: &ByteString) -> Option<&FunctionGroup> {
        let start = self.by_alias.get(alias)?;
        self.by_start.get(start)
    }

    /// Return `true` when the reverse alias index contains `alias`.
    #[must_use]
    pub fn contains_alias(&self, alias: &ByteString) -> bool {
        self.by_alias.contains_key(alias)
    }

    /// Return `true` when a group exists at `start`.
    #[must_use]
    pub fn contains_start(&self, start: &LineKey) -> bool {
        self.by_start.contains_key(start)
    }

    /// Iterate groups in start-key order.
    pub fn groups(&self) -> impl Iterator<Item = (&LineKey, &FunctionGroup)> {
        self.by_start.iter()
    }

    /// Iterate alias → start reverse-index entries in lexical alias order.
    pub fn alias_index(&self) -> impl Iterator<Item = (&ByteString, &LineKey)> {
        self.by_alias.iter()
    }

    /// Ensure a group exists at `start`, creating it with `alias` when absent.
    ///
    /// When the group already exists, `end` is applied only when `Some` and the
    /// group currently has no end, or when the new end lexeme is accepted as a
    /// greater end candidate (greatest accepted end). Conflicting ends are
    /// representable without writer diagnostics.
    pub fn ensure_group(
        &mut self,
        start: LineKey,
        alias: impl Into<ByteString>,
        end: Option<LineKey>,
    ) -> Result<&mut FunctionGroup, FunctionError> {
        let alias = alias.into();
        if let Some(existing_start) = self.by_alias.get(&alias) {
            if existing_start != &start {
                return Err(FunctionError::AliasStartConflict {
                    alias,
                    existing_start: existing_start.clone(),
                    requested_start: start,
                });
            }
        }

        if !self.by_start.contains_key(&start) {
            let group = FunctionGroup::new(start.clone(), alias.clone(), end);
            self.by_start.insert(start.clone(), group);
            self.by_alias.insert(alias, start.clone());
            return Ok(self.by_start.get_mut(&start).expect("just inserted"));
        }

        // Group exists: optionally merge end, then ensure alias membership.
        {
            let group = self.by_start.get_mut(&start).expect("contains_key");
            match (&group.end, end) {
                (None, Some(new_end)) => group.end = Some(new_end),
                (Some(cur), Some(new_end)) if end_is_greater(&new_end, cur) => {
                    // Retain greatest accepted end by numeric-ish lexeme compare
                    // when both look like plain integers; otherwise keep current.
                    group.end = Some(new_end);
                }
                _ => {}
            }
        }

        if let std::collections::btree_map::Entry::Vacant(entry) =
            self.by_alias.entry(alias.clone())
        {
            let group = self.by_start.get_mut(&start).expect("contains_key");
            group
                .add_alias(alias, CoverageCount::zero())
                .map_err(FunctionError::CountAdd)?;
            entry.insert(start.clone());
        }

        Ok(self.by_start.get_mut(&start).expect("contains_key"))
    }

    /// Insert or add an alias count at `start`, keeping both indexes coherent.
    ///
    /// Repeated alias counts add. A new alias at an existing start joins that
    /// group. Alias already bound to another start returns
    /// [`FunctionError::AliasStartConflict`].
    pub fn insert_alias_at(
        &mut self,
        start: LineKey,
        alias: impl Into<ByteString>,
        count: CoverageCount,
    ) -> Result<(), FunctionError> {
        let alias = alias.into();
        if let Some(existing_start) = self.by_alias.get(&alias) {
            if existing_start != &start {
                return Err(FunctionError::AliasStartConflict {
                    alias,
                    existing_start: existing_start.clone(),
                    requested_start: start,
                });
            }
            let group =
                self.by_start
                    .get_mut(&start)
                    .ok_or_else(|| FunctionError::OrphanAlias {
                        alias: alias.clone(),
                        start: start.clone(),
                    })?;
            group
                .add_alias(alias, count)
                .map_err(FunctionError::CountAdd)?;
            return Ok(());
        }

        if let Some(group) = self.by_start.get_mut(&start) {
            group
                .add_alias(alias.clone(), count)
                .map_err(FunctionError::CountAdd)?;
            self.by_alias.insert(alias, start);
            return Ok(());
        }

        let mut group = FunctionGroup::new(start.clone(), alias.clone(), None);
        // Replace the zero seeded by `new` with the provided count.
        group.aliases.insert(alias.clone(), count);
        self.by_start.insert(start.clone(), group);
        self.by_alias.insert(alias, start);
        Ok(())
    }

    /// Compatibility helper used by CORE-002 store smoke tests.
    ///
    /// Inserts `alias` at start line `"0"` (explicitly representable ignored /
    /// unspecified start). Prefer [`FunctionTable::insert_alias_at`] for real
    /// locations.
    pub fn insert_alias(
        &mut self,
        alias: impl Into<ByteString>,
        count: CoverageCount,
    ) -> Result<(), FunctionError> {
        self.insert_alias_at(LineKey::from_lexeme("0"), alias, count)
    }

    /// Set the end line for an existing group. Creates nothing when missing.
    pub fn set_group_end(&mut self, start: &LineKey, end: Option<LineKey>) -> bool {
        match self.by_start.get_mut(start) {
            Some(group) => {
                group.set_end(end);
                true
            }
            None => false,
        }
    }

    /// Remove an alias by name, dropping the group when it becomes empty.
    ///
    /// Keeps both indexes coherent. Returns the prior count when the alias
    /// existed.
    pub fn remove_alias(&mut self, alias: &ByteString) -> Option<CoverageCount> {
        let start = self.by_alias.remove(alias)?;
        let group = self.by_start.get_mut(&start)?;
        let prior = group.remove_alias(alias);
        if group.alias_len() == 0 {
            self.by_start.remove(&start);
        }
        prior
    }

    /// Remove an entire group by start location, clearing all of its aliases
    /// from the reverse index.
    pub fn remove_group(&mut self, start: &LineKey) -> Option<FunctionGroup> {
        let group = self.by_start.remove(start)?;
        for alias in group.aliases().keys() {
            self.by_alias.remove(alias);
        }
        Some(group)
    }

    /// Borrow mutable group by start (algebra helpers).
    pub fn get_by_start_mut(&mut self, start: &LineKey) -> Option<&mut FunctionGroup> {
        self.by_start.get_mut(start)
    }

    /// Insert a fully-formed group, replacing any previous group at that start.
    ///
    /// Callers must ensure aliases do not conflict with other starts. Existing
    /// aliases at this start are cleared from the reverse index first.
    pub fn insert_group(&mut self, group: FunctionGroup) -> Result<(), FunctionError> {
        let start = group.start().clone();
        if let Some(old) = self.by_start.remove(&start) {
            for alias in old.aliases().keys() {
                self.by_alias.remove(alias);
            }
        }
        for alias in group.aliases().keys() {
            if let Some(existing) = self.by_alias.get(alias) {
                if existing != &start {
                    return Err(FunctionError::AliasStartConflict {
                        alias: alias.clone(),
                        existing_start: existing.clone(),
                        requested_start: start,
                    });
                }
            }
        }
        for alias in group.aliases().keys() {
            self.by_alias.insert(alias.clone(), start.clone());
        }
        self.by_start.insert(start, group);
        Ok(())
    }

    /// Assert that start and alias indexes are coherent.
    ///
    /// Used by tests and debug checks. Successful mutations must leave the
    /// table in a state that passes this check.
    pub fn assert_indexes_coherent(&self) -> Result<(), FunctionError> {
        for (alias, start) in &self.by_alias {
            let group = self
                .by_start
                .get(start)
                .ok_or_else(|| FunctionError::OrphanAlias {
                    alias: alias.clone(),
                    start: start.clone(),
                })?;
            if group.start() != start {
                return Err(FunctionError::IndexIncoherent(format!(
                    "alias {} maps to start {} but group.start is {}",
                    alias,
                    start.lexeme(),
                    group.start().lexeme()
                )));
            }
            if !group.aliases().contains_key(alias) {
                return Err(FunctionError::IndexIncoherent(format!(
                    "alias {} indexed at {} but missing from group aliases",
                    alias,
                    start.lexeme()
                )));
            }
        }

        for (start, group) in &self.by_start {
            if group.start() != start {
                return Err(FunctionError::IndexIncoherent(format!(
                    "by_start key {} disagrees with group.start {}",
                    start.lexeme(),
                    group.start().lexeme()
                )));
            }
            if !group.aliases().contains_key(group.representative()) {
                return Err(FunctionError::IndexIncoherent(format!(
                    "representative {} missing from aliases at {}",
                    group.representative(),
                    start.lexeme()
                )));
            }
            for alias in group.aliases().keys() {
                match self.by_alias.get(alias) {
                    Some(indexed) if indexed == start => {}
                    Some(indexed) => {
                        return Err(FunctionError::IndexIncoherent(format!(
                            "alias {} in group {} reverse-indexes to {}",
                            alias,
                            start.lexeme(),
                            indexed.lexeme()
                        )));
                    }
                    None => {
                        return Err(FunctionError::IndexIncoherent(format!(
                            "alias {} in group {} missing from reverse index",
                            alias,
                            start.lexeme()
                        )));
                    }
                }
            }
        }

        if self.by_alias.len()
            != self
                .by_start
                .values()
                .map(FunctionGroup::alias_len)
                .sum::<usize>()
        {
            return Err(FunctionError::IndexIncoherent(format!(
                "alias index len {} != sum of group aliases {}",
                self.by_alias.len(),
                self.by_start
                    .values()
                    .map(FunctionGroup::alias_len)
                    .sum::<usize>()
            )));
        }

        Ok(())
    }
}

fn end_is_greater(candidate: &LineKey, current: &LineKey) -> bool {
    let Some(c) = candidate.lexeme().as_utf8() else {
        return false;
    };
    let Some(cur) = current.lexeme().as_utf8() else {
        return true;
    };
    let c = c.trim();
    let cur = cur.trim();
    if !c.bytes().all(|b| b.is_ascii_digit()) || !cur.bytes().all(|b| b.is_ascii_digit()) {
        return c > cur;
    }
    match (c.parse::<u128>(), cur.parse::<u128>()) {
        (Ok(a), Ok(b)) => a > b,
        _ => c > cur,
    }
}

#[cfg(test)]
mod tests {
    use super::{FunctionTable, effective_alias_length, is_lambda_alias};
    use crate::bytes::ByteString;
    use crate::keys::LineKey;
    use crate::numeric::CoverageCount;

    #[test]
    fn aliases_at_same_start_form_one_group_with_coherent_reverse_index() {
        let mut table = FunctionTable::new();
        let start = LineKey::from_lexeme("10");
        table
            .insert_alias_at(start.clone(), "foo", CoverageCount::from_lexeme("1"))
            .expect("insert foo");
        table
            .insert_alias_at(start.clone(), "bar", CoverageCount::from_lexeme("0"))
            .expect("insert bar");

        assert_eq!(table.group_len(), 1);
        assert_eq!(table.alias_len(), 2);
        let group = table.get_by_start(&start).expect("group");
        assert_eq!(group.alias_len(), 2);
        assert!(table.contains_alias(&ByteString::from("foo")));
        assert!(table.contains_alias(&ByteString::from("bar")));
        assert_eq!(
            table
                .get_by_alias(&ByteString::from("foo"))
                .map(super::FunctionGroup::start),
            Some(&start)
        );
        table.assert_indexes_coherent().expect("coherent");
    }

    #[test]
    fn representative_is_shortest_then_lexical_with_lambda_penalty() {
        let mut table = FunctionTable::new();
        let start = LineKey::from_lexeme("3");
        table
            .insert_alias_at(start.clone(), "zebra", CoverageCount::zero())
            .unwrap();
        table
            .insert_alias_at(start.clone(), "aardvark", CoverageCount::zero())
            .unwrap();
        // shorter wins
        table
            .insert_alias_at(start.clone(), "ab", CoverageCount::zero())
            .unwrap();
        assert_eq!(
            table
                .get_by_start(&start)
                .unwrap()
                .representative()
                .as_bytes(),
            b"ab"
        );

        // equal length → lexical
        table
            .insert_alias_at(start.clone(), "aa", CoverageCount::zero())
            .unwrap();
        assert_eq!(
            table
                .get_by_start(&start)
                .unwrap()
                .representative()
                .as_bytes(),
            b"aa"
        );

        // lambda is penalized (+1000) so a longer non-lambda still wins
        let mut lambda_table = FunctionTable::new();
        let start = LineKey::from_lexeme("4");
        lambda_table
            .insert_alias_at(start.clone(), "ns::{lambda(int)#1}", CoverageCount::zero())
            .unwrap();
        lambda_table
            .insert_alias_at(start.clone(), "longer_name_here", CoverageCount::zero())
            .unwrap();
        assert!(is_lambda_alias(b"ns::{lambda(int)#1}"));
        assert!(
            effective_alias_length(b"ns::{lambda(int)#1}")
                > effective_alias_length(b"longer_name_here")
        );
        assert_eq!(
            lambda_table
                .get_by_start(&start)
                .unwrap()
                .representative()
                .as_bytes(),
            b"longer_name_here"
        );

        // found/hit: one group, two aliases; only one positive → group hit 1, alias hit 1
        let mut hits = FunctionTable::new();
        let start = LineKey::from_lexeme("5");
        hits.insert_alias_at(start.clone(), "a", CoverageCount::from_lexeme("2"))
            .unwrap();
        hits.insert_alias_at(start.clone(), "b", CoverageCount::zero())
            .unwrap();
        assert_eq!(hits.group_found(), 1);
        assert_eq!(hits.group_hit(), 1);
        assert_eq!(hits.alias_found(), 2);
        assert_eq!(hits.alias_hit(), 1);
    }

    #[test]
    fn repeated_alias_counts_add_and_zero_start_is_representable() {
        let mut table = FunctionTable::new();
        let start = LineKey::from_lexeme("0");
        assert!(start.is_zero());
        table
            .insert_alias_at(start.clone(), "main", CoverageCount::from_lexeme("1"))
            .unwrap();
        table
            .insert_alias_at(start.clone(), "main", CoverageCount::from_lexeme("3"))
            .unwrap();
        let count = table
            .get_by_start(&start)
            .unwrap()
            .aliases()
            .get(&ByteString::from("main"))
            .unwrap();
        assert_eq!(count.lexeme().as_bytes(), b"4");
        assert_eq!(table.alias_len(), 1);
        table.assert_indexes_coherent().unwrap();

        // end before start remains representable
        table.set_group_end(&start, Some(LineKey::from_lexeme("0")));
        // also allow end < start numerically
        let mut t2 = FunctionTable::new();
        let s = LineKey::from_lexeme("20");
        t2.insert_alias_at(s.clone(), "f", CoverageCount::zero())
            .unwrap();
        t2.set_group_end(&s, Some(LineKey::from_lexeme("1")));
        assert_eq!(
            t2.get_by_start(&s)
                .unwrap()
                .end()
                .map(|e| e.lexeme().as_bytes()),
            Some(b"1".as_slice())
        );
    }

    #[test]
    fn mutations_keep_alias_and_start_indexes_consistent() {
        let mut table = FunctionTable::new();
        let s1 = LineKey::from_lexeme("1");
        let s2 = LineKey::from_lexeme("2");
        table
            .insert_alias_at(s1.clone(), "one", CoverageCount::from_lexeme("1"))
            .unwrap();
        table
            .insert_alias_at(s1.clone(), "also", CoverageCount::zero())
            .unwrap();
        table
            .insert_alias_at(s2.clone(), "two", CoverageCount::from_lexeme("5"))
            .unwrap();
        table.assert_indexes_coherent().unwrap();

        // conflict: same alias at another start
        let err = table
            .insert_alias_at(s2.clone(), "one", CoverageCount::zero())
            .expect_err("conflict");
        assert!(matches!(
            err,
            super::FunctionError::AliasStartConflict { .. }
        ));
        table.assert_indexes_coherent().unwrap();

        assert_eq!(
            table
                .get_by_alias(&ByteString::from("also"))
                .unwrap()
                .start(),
            &s1
        );
        assert_eq!(
            table
                .get_by_alias(&ByteString::from("two"))
                .unwrap()
                .start(),
            &s2
        );
    }
}
