//! Independent aggregate and testcase-family coverage stores.
//!
//! Aggregate [`CoverageStore`] and the four [`TestcaseStores`] family maps are
//! first-class and MUST NOT be lazily derived from each other. Explicit empty
//! family values remain representable by map presence.

use crate::branch_store::BranchCoverage;
use crate::bytes::ByteString;
use crate::function::FunctionTable;
use crate::identity::{SourceIdentity, SourceLookupKey, TestName};
use crate::keys::LineKey;
use crate::line::LineCoverage;
use crate::mcdc::McdcCoverage;
use std::collections::BTreeMap;

/// Opaque holder for lifecycle-dependent / cache totals.
///
/// Oracle-exact semantics for when recomputation from current points is
/// insufficient are deferred. CORE-002 only requires a distinct field that can
/// be set and read without deriving from coverage points.
///
/// Deferred: exact Oracle cache lifecycle, terminator cloning interactions, and
/// writer-total separation proofs that may later remove this field if every
/// supported operation is shown recomputation-equivalent.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TotalState {
    /// Opaque payload bytes retained by callers until Oracle semantics land.
    payload: Option<ByteString>,
}

impl TotalState {
    /// Create an empty / unset totals holder.
    #[must_use]
    pub fn new() -> Self {
        Self { payload: None }
    }

    /// Construct from explicit opaque payload bytes.
    #[must_use]
    pub fn from_payload(payload: impl Into<ByteString>) -> Self {
        Self {
            payload: Some(payload.into()),
        }
    }

    /// Return `true` when no opaque payload is stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.payload.is_none()
    }

    /// Borrow the opaque payload when present.
    #[must_use]
    pub fn payload(&self) -> Option<&ByteString> {
        self.payload.as_ref()
    }

    /// Replace the opaque payload.
    pub fn set_payload(&mut self, payload: impl Into<ByteString>) {
        self.payload = Some(payload.into());
    }

    /// Clear the opaque payload.
    pub fn clear(&mut self) {
        self.payload = None;
    }
}

/// Four-family coverage store used by aggregate and (as values) by testcases.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CoverageStore {
    lines: LineCoverage,
    functions: FunctionTable,
    branches: BranchCoverage,
    mcdc: McdcCoverage,
}

impl CoverageStore {
    /// Create an empty four-family coverage store.
    #[must_use]
    pub fn new() -> Self {
        Self {
            lines: LineCoverage::new(),
            functions: FunctionTable::new(),
            branches: BranchCoverage::new(),
            mcdc: McdcCoverage::new(),
        }
    }

    /// Borrow line coverage.
    #[must_use]
    pub fn lines(&self) -> &LineCoverage {
        &self.lines
    }

    /// Borrow line coverage mutably.
    pub fn lines_mut(&mut self) -> &mut LineCoverage {
        &mut self.lines
    }

    /// Borrow the function table.
    #[must_use]
    pub fn functions(&self) -> &FunctionTable {
        &self.functions
    }

    /// Borrow the function table mutably.
    pub fn functions_mut(&mut self) -> &mut FunctionTable {
        &mut self.functions
    }

    /// Borrow branch coverage.
    #[must_use]
    pub fn branches(&self) -> &BranchCoverage {
        &self.branches
    }

    /// Borrow branch coverage mutably.
    pub fn branches_mut(&mut self) -> &mut BranchCoverage {
        &mut self.branches
    }

    /// Borrow MC/DC coverage.
    #[must_use]
    pub fn mcdc(&self) -> &McdcCoverage {
        &self.mcdc
    }

    /// Borrow MC/DC coverage mutably.
    pub fn mcdc_mut(&mut self) -> &mut McdcCoverage {
        &mut self.mcdc
    }

    /// Replace line coverage wholesale.
    pub fn set_lines(&mut self, lines: LineCoverage) {
        self.lines = lines;
    }

    /// Replace function coverage wholesale.
    pub fn set_functions(&mut self, functions: FunctionTable) {
        self.functions = functions;
    }

    /// Replace branch coverage wholesale.
    pub fn set_branches(&mut self, branches: BranchCoverage) {
        self.branches = branches;
    }

    /// Replace MC/DC coverage wholesale.
    pub fn set_mcdc(&mut self, mcdc: McdcCoverage) {
        self.mcdc = mcdc;
    }
}

/// Independent testcase-family maps.
///
/// The four key sets remain independently representable. A test name may exist
/// in one family with an explicit empty value while being absent from others.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TestcaseStores {
    lines: BTreeMap<TestName, LineCoverage>,
    functions: BTreeMap<TestName, FunctionTable>,
    branches: BTreeMap<TestName, BranchCoverage>,
    mcdc: BTreeMap<TestName, McdcCoverage>,
}

impl TestcaseStores {
    /// Create empty family maps.
    #[must_use]
    pub fn new() -> Self {
        Self {
            lines: BTreeMap::new(),
            functions: BTreeMap::new(),
            branches: BTreeMap::new(),
            mcdc: BTreeMap::new(),
        }
    }

    /// Borrow the line testcase map.
    #[must_use]
    pub fn lines(&self) -> &BTreeMap<TestName, LineCoverage> {
        &self.lines
    }

    /// Borrow the line testcase map mutably.
    pub fn lines_mut(&mut self) -> &mut BTreeMap<TestName, LineCoverage> {
        &mut self.lines
    }

    /// Borrow the function testcase map.
    #[must_use]
    pub fn functions(&self) -> &BTreeMap<TestName, FunctionTable> {
        &self.functions
    }

    /// Borrow the function testcase map mutably.
    pub fn functions_mut(&mut self) -> &mut BTreeMap<TestName, FunctionTable> {
        &mut self.functions
    }

    /// Borrow the branch testcase map.
    #[must_use]
    pub fn branches(&self) -> &BTreeMap<TestName, BranchCoverage> {
        &self.branches
    }

    /// Borrow the branch testcase map mutably.
    pub fn branches_mut(&mut self) -> &mut BTreeMap<TestName, BranchCoverage> {
        &mut self.branches
    }

    /// Borrow the MC/DC testcase map.
    #[must_use]
    pub fn mcdc(&self) -> &BTreeMap<TestName, McdcCoverage> {
        &self.mcdc
    }

    /// Borrow the MC/DC testcase map mutably.
    pub fn mcdc_mut(&mut self) -> &mut BTreeMap<TestName, McdcCoverage> {
        &mut self.mcdc
    }

    /// Insert a line-family value (including an explicit empty map).
    pub fn insert_lines(
        &mut self,
        name: TestName,
        coverage: LineCoverage,
    ) -> Option<LineCoverage> {
        self.lines.insert(name, coverage)
    }

    /// Insert a function-family value (including an explicit empty table).
    pub fn insert_functions(
        &mut self,
        name: TestName,
        coverage: FunctionTable,
    ) -> Option<FunctionTable> {
        self.functions.insert(name, coverage)
    }

    /// Insert a branch-family value (including an explicit empty store).
    pub fn insert_branches(
        &mut self,
        name: TestName,
        coverage: BranchCoverage,
    ) -> Option<BranchCoverage> {
        self.branches.insert(name, coverage)
    }

    /// Insert an MC/DC-family value (including an explicit empty store).
    pub fn insert_mcdc(
        &mut self,
        name: TestName,
        coverage: McdcCoverage,
    ) -> Option<McdcCoverage> {
        self.mcdc.insert(name, coverage)
    }
}

/// Per-source coverage record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceCoverage {
    identity: SourceIdentity,
    version: Option<ByteString>,
    checksums: BTreeMap<LineKey, ByteString>,
    aggregate: CoverageStore,
    testcases: TestcaseStores,
    observable_totals: TotalState,
}

impl SourceCoverage {
    /// Construct a source coverage record with empty stores and totals.
    #[must_use]
    pub fn new(identity: SourceIdentity) -> Self {
        Self {
            identity,
            version: None,
            checksums: BTreeMap::new(),
            aggregate: CoverageStore::new(),
            testcases: TestcaseStores::new(),
            observable_totals: TotalState::new(),
        }
    }

    /// Borrow source identity.
    #[must_use]
    pub fn identity(&self) -> &SourceIdentity {
        &self.identity
    }

    /// Borrow optional version bytes.
    #[must_use]
    pub fn version(&self) -> Option<&ByteString> {
        self.version.as_ref()
    }

    /// Set or clear the optional source-scoped version.
    pub fn set_version(&mut self, version: Option<ByteString>) {
        self.version = version;
    }

    /// Borrow checksum map.
    #[must_use]
    pub fn checksums(&self) -> &BTreeMap<LineKey, ByteString> {
        &self.checksums
    }

    /// Borrow checksum map mutably.
    pub fn checksums_mut(&mut self) -> &mut BTreeMap<LineKey, ByteString> {
        &mut self.checksums
    }

    /// Borrow the independent aggregate store.
    #[must_use]
    pub fn aggregate(&self) -> &CoverageStore {
        &self.aggregate
    }

    /// Borrow the independent aggregate store mutably.
    pub fn aggregate_mut(&mut self) -> &mut CoverageStore {
        &mut self.aggregate
    }

    /// Borrow the independent testcase-family stores.
    #[must_use]
    pub fn testcases(&self) -> &TestcaseStores {
        &self.testcases
    }

    /// Borrow the independent testcase-family stores mutably.
    pub fn testcases_mut(&mut self) -> &mut TestcaseStores {
        &mut self.testcases
    }

    /// Borrow observable totals (distinct from recomputed point totals).
    #[must_use]
    pub fn observable_totals(&self) -> &TotalState {
        &self.observable_totals
    }

    /// Borrow observable totals mutably.
    pub fn observable_totals_mut(&mut self) -> &mut TotalState {
        &mut self.observable_totals
    }

    /// Replace observable totals wholesale.
    pub fn set_observable_totals(&mut self, totals: TotalState) {
        self.observable_totals = totals;
    }
}

/// Top-level coverage database keyed by [`SourceLookupKey`].
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CoverageDatabase {
    sources: BTreeMap<SourceLookupKey, SourceCoverage>,
}

impl CoverageDatabase {
    /// Create an empty database.
    #[must_use]
    pub fn new() -> Self {
        Self {
            sources: BTreeMap::new(),
        }
    }

    /// Number of source entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.sources.len()
    }

    /// Return `true` when no sources are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.sources.is_empty()
    }

    /// Insert or replace a source coverage record keyed by its lookup key.
    pub fn insert(&mut self, source: SourceCoverage) -> Option<SourceCoverage> {
        let key = source.identity().lookup_key().clone();
        self.sources.insert(key, source)
    }

    /// Insert under an explicit lookup key (for callers that already folded).
    pub fn insert_with_key(
        &mut self,
        key: SourceLookupKey,
        source: SourceCoverage,
    ) -> Option<SourceCoverage> {
        self.sources.insert(key, source)
    }

    /// Borrow a source by lookup key.
    #[must_use]
    pub fn get(&self, key: &SourceLookupKey) -> Option<&SourceCoverage> {
        self.sources.get(key)
    }

    /// Borrow a source mutably by lookup key.
    pub fn get_mut(&mut self, key: &SourceLookupKey) -> Option<&mut SourceCoverage> {
        self.sources.get_mut(key)
    }

    /// Return `true` when the database contains `key`.
    #[must_use]
    pub fn contains_key(&self, key: &SourceLookupKey) -> bool {
        self.sources.contains_key(key)
    }

    /// Remove a source by lookup key.
    pub fn remove(&mut self, key: &SourceLookupKey) -> Option<SourceCoverage> {
        self.sources.remove(key)
    }

    /// Iterate sources in lookup-key order.
    pub fn iter(&self) -> impl Iterator<Item = (&SourceLookupKey, &SourceCoverage)> {
        self.sources.iter()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CoverageDatabase, CoverageStore, SourceCoverage, TestcaseStores, TotalState,
    };
    use crate::branch::BranchTaken;
    use crate::branch_store::BranchCoverage;
    use crate::bytes::ByteString;
    use crate::function::FunctionTable;
    use crate::identity::{SourceIdentity, SourceLookupKey, TestName};
    use crate::keys::LineKey;
    use crate::line::LineCoverage;
    use crate::mcdc::{GroupSizeKey, McdcCoverage};
    use crate::numeric::{CoverageCount, NumericAtom};

    fn sample_source(path: &str) -> SourceCoverage {
        SourceCoverage::new(SourceIdentity::from_display_path(path))
    }

    #[test]
    fn aggregate_and_testcase_stores_are_independent() {
        let mut source = sample_source("/src/a.c");
        let key = LineKey::from_lexeme("10");
        source
            .aggregate_mut()
            .lines_mut()
            .insert(key.clone(), CoverageCount::from_lexeme("1"));

        let tn = TestName::new("t1");
        let mut tc_lines = LineCoverage::new();
        tc_lines.insert(key.clone(), CoverageCount::from_lexeme("9"));
        source.testcases_mut().insert_lines(tn.clone(), tc_lines);

        // Mutate aggregate only.
        source
            .aggregate_mut()
            .lines_mut()
            .insert(key.clone(), CoverageCount::from_lexeme("2"));

        assert_eq!(
            source
                .aggregate()
                .lines()
                .get(&key)
                .map(CoverageCount::lexeme)
                .map(|b| b.as_bytes()),
            Some(b"2".as_slice())
        );
        assert_eq!(
            source
                .testcases()
                .lines()
                .get(&tn)
                .and_then(|m| m.get(&key))
                .map(CoverageCount::lexeme)
                .map(|b| b.as_bytes()),
            Some(b"9".as_slice())
        );

        // Mutate testcase only.
        source
            .testcases_mut()
            .lines_mut()
            .get_mut(&tn)
            .expect("present")
            .insert(key.clone(), CoverageCount::from_lexeme("8"));

        assert_eq!(
            source
                .aggregate()
                .lines()
                .get(&key)
                .map(CoverageCount::lexeme)
                .map(|b| b.as_bytes()),
            Some(b"2".as_slice())
        );
        assert_eq!(
            source
                .testcases()
                .lines()
                .get(&tn)
                .and_then(|m| m.get(&key))
                .map(CoverageCount::lexeme)
                .map(|b| b.as_bytes()),
            Some(b"8".as_slice())
        );
    }

    #[test]
    fn explicit_empty_line_coverage_remains_present_for_testcase() {
        let mut stores = TestcaseStores::new();
        let tn = TestName::new("empty-lines");
        stores.insert_lines(tn.clone(), LineCoverage::new());

        assert!(stores.lines().contains_key(&tn));
        let value = stores.lines().get(&tn).expect("present");
        assert!(value.is_empty());
        assert!(!stores.functions().contains_key(&tn));
        assert!(!stores.branches().contains_key(&tn));
        assert!(!stores.mcdc().contains_key(&tn));
    }

    #[test]
    fn four_family_maps_can_have_different_key_sets() {
        let mut source = sample_source("/src/families.c");
        let line_only = TestName::new("line-only");
        let fn_only = TestName::new("fn-only");
        let br_only = TestName::new("br-only");
        let mcdc_only = TestName::new("mcdc-only");

        source
            .testcases_mut()
            .insert_lines(line_only.clone(), LineCoverage::new());
        source
            .testcases_mut()
            .insert_functions(fn_only.clone(), FunctionTable::new());
        source
            .testcases_mut()
            .insert_branches(br_only.clone(), BranchCoverage::new());
        source
            .testcases_mut()
            .insert_mcdc(mcdc_only.clone(), McdcCoverage::new());

        let tc = source.testcases();
        assert_eq!(tc.lines().keys().cloned().collect::<Vec<_>>(), vec![line_only]);
        assert_eq!(tc.functions().keys().cloned().collect::<Vec<_>>(), vec![fn_only]);
        assert_eq!(tc.branches().keys().cloned().collect::<Vec<_>>(), vec![br_only]);
        assert_eq!(tc.mcdc().keys().cloned().collect::<Vec<_>>(), vec![mcdc_only]);
    }

    #[test]
    fn coverage_database_keys_by_source_lookup_key_with_case_folding() {
        let mut db = CoverageDatabase::new();

        let sensitive = SourceCoverage::new(SourceIdentity::from_display_path("Src/Foo.C"));
        db.insert(sensitive);
        assert!(db.contains_key(&SourceLookupKey::from_path_bytes("Src/Foo.C")));
        assert!(!db.contains_key(&SourceLookupKey::from_path_bytes("src/foo.c")));

        let mut folded_db = CoverageDatabase::new();
        let folded = SourceCoverage::new(SourceIdentity::ascii_case_insensitive("Src/Foo.C"));
        folded_db.insert(folded);
        assert!(folded_db.contains_key(&SourceLookupKey::ascii_case_insensitive("SRC/FOO.C")));
        assert!(folded_db.contains_key(&SourceLookupKey::ascii_case_insensitive("src/foo.c")));
        assert!(!folded_db.contains_key(&SourceLookupKey::from_path_bytes("Src/Foo.C")));
        assert_eq!(
            folded_db
                .get(&SourceLookupKey::ascii_case_insensitive("Src/Foo.C"))
                .map(|s| s.identity().display_path().as_bytes()),
            Some(b"Src/Foo.C".as_slice())
        );
    }

    #[test]
    fn observable_totals_are_distinct_from_coverage_points() {
        let mut source = sample_source("/src/totals.c");
        source
            .aggregate_mut()
            .lines_mut()
            .insert(LineKey::from_lexeme("1"), CoverageCount::from_lexeme("5"));

        assert!(source.observable_totals().is_empty());
        source.set_observable_totals(TotalState::from_payload("cached-lf=99"));
        assert_eq!(
            source.observable_totals().payload().map(ByteString::as_bytes),
            Some(b"cached-lf=99".as_slice())
        );

        // Clearing / replacing totals does not touch aggregate points.
        source.observable_totals_mut().clear();
        assert!(source.observable_totals().is_empty());
        assert_eq!(source.aggregate().lines().len(), 1);

        source.observable_totals_mut().set_payload("again");
        source.aggregate_mut().lines_mut().remove(&LineKey::from_lexeme("1"));
        assert_eq!(
            source.observable_totals().payload().map(ByteString::as_bytes),
            Some(b"again".as_slice())
        );
        assert!(source.aggregate().lines().is_empty());
    }

    #[test]
    fn coverage_store_families_are_independently_mutable() {
        let mut store = CoverageStore::new();
        store
            .lines_mut()
            .insert(LineKey::from_lexeme("1"), CoverageCount::from_lexeme("1"));
        store
            .functions_mut()
            .insert_alias("main", CoverageCount::from_lexeme("1"))
            .expect("alias insert");
        store
            .branches_mut()
            .push_taken_on_line(LineKey::from_lexeme("1"), BranchTaken::from_token("-"));
        {
            let mcdc_line = store.mcdc_mut().entry_line(LineKey::from_lexeme("1"));
            mcdc_line.append_expression(
                GroupSizeKey::from_lexeme("1"),
                NumericAtom::from_lexeme("0"),
                "a",
            );
        }

        assert_eq!(store.lines().len(), 1);
        assert_eq!(store.functions().alias_len(), 1);
        assert_eq!(store.branches().line_len(), 1);
        assert_eq!(store.mcdc().line_len(), 1);

        store.set_lines(LineCoverage::new());
        assert!(store.lines().is_empty());
        assert!(!store.functions().is_empty());
        assert!(!store.branches().is_empty());
        assert!(!store.mcdc().is_empty());
    }
}
