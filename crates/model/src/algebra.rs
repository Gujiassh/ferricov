//! Ordered coverage-family algebra (union / intersect / difference).
//!
//! Normative rules come from `coverage-model.md` Line / Functions / Branches /
//! MC/DC / Set Algebra sections. Operations are **ordered** and preserve
//! operand order; they do not assume unrestricted commutativity.
//!
//! Exact Oracle fixture binding for residual ALG rows is deferred where noted:
//! - `M1-ALG-FUNCTION-REP-001` — post-removal representative lexical quirk
//! - `M1-ALG-BRANCH-CACHE-001` — intersection cache / `changed` quirk
//! - `M1-ALG-MCDC-VECTOR-001` / `M1-ALG-MCDC-EXPR-001` — asymmetric vector /
//!   expression continuation diagnostics beyond fail-closed Result
//! - `M1-MD-014` — exact testcase-map left-only / empty right-only pin

use crate::branch_store::{BranchBlock, BranchCoverage, BranchError, BranchLine};
use crate::bytes::ByteString;
use crate::function::{FunctionError, FunctionGroup, FunctionTable};
use crate::identity::TestName;
use crate::keys::LineKey;
use crate::line::LineCoverage;
use crate::mcdc::{GroupSizeKey, McdcCoverage, McdcError, McdcExpression, McdcLine};
use crate::numeric::{AddError, CoverageCount};
use crate::stores::{CoverageStore, TestcaseStores};
use std::collections::BTreeMap;
use std::fmt;

/// Algebra operation kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AlgebraOp {
    Union,
    Intersect,
    Difference,
}

/// Errors from ordered algebra operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AlgebraError {
    /// Coverage-count addition failed.
    CountAdd(AddError),
    /// Function index / alias conflict.
    Function(FunctionError),
    /// MC/DC structural / compatibility failure.
    Mcdc(McdcError),
    /// Longer left MC/DC vector would dereference an undefined right element.
    ///
    /// Oracle can `die` here (`M1-ALG-MCDC-VECTOR-001`). Ferricov returns this
    /// fail-closed [`Result`] error instead of panicking or inventing padding.
    McdcAsymmetricVector {
        line: LineKey,
        group: GroupSizeKey,
        left_len: usize,
        right_len: usize,
    },
    /// Branch taken-state merge failed.
    BranchTaken(AddError),
    /// Branch structural invariant failed after algebra.
    Branch(BranchError),
}

impl fmt::Display for AlgebraError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::CountAdd(err) => write!(f, "algebra count add failed: {err:?}"),
            Self::Function(err) => write!(f, "algebra function error: {err}"),
            Self::Mcdc(err) => write!(f, "algebra mcdc error: {err}"),
            Self::McdcAsymmetricVector {
                line,
                group,
                left_len,
                right_len,
            } => write!(
                f,
                "mcdc asymmetric vector on line {} group {}: left_len={left_len} right_len={right_len}",
                line.lexeme(),
                group.lexeme()
            ),
            Self::BranchTaken(err) => write!(f, "algebra branch taken merge failed: {err:?}"),
            Self::Branch(err) => write!(f, "algebra branch error: {err}"),
        }
    }
}

impl std::error::Error for AlgebraError {}

impl From<AddError> for AlgebraError {
    fn from(value: AddError) -> Self {
        Self::CountAdd(value)
    }
}

impl From<FunctionError> for AlgebraError {
    fn from(value: FunctionError) -> Self {
        Self::Function(value)
    }
}

// ---------------------------------------------------------------------------
// LineCoverage
// ---------------------------------------------------------------------------

impl LineCoverage {
    /// Ordered union: copy right-only keys; add common counts.
    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        for (key, rcount) in right.iter() {
            if let Some(lcount) = self.get(key) {
                let summed = lcount.add(rcount)?;
                self.insert(key.clone(), summed);
            } else {
                self.insert(key.clone(), rcount.clone());
            }
        }
        Ok(())
    }

    /// Ordered intersection: keep common keys; **add** counts (not `min`).
    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        let keys: Vec<LineKey> = self.iter().map(|(k, _)| k.clone()).collect();
        for key in keys {
            match right.get(&key) {
                Some(rcount) => {
                    let summed = self.get(&key).expect("key present").add(rcount)?;
                    self.insert(key, summed);
                }
                None => {
                    self.remove(&key);
                }
            }
        }
        Ok(())
    }

    /// Ordered difference: remove common keys (not numeric subtract).
    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        let keys: Vec<LineKey> = right.iter().map(|(k, _)| k.clone()).collect();
        for key in keys {
            self.remove(&key);
        }
        Ok(())
    }

    /// Apply [`AlgebraOp`] against `right`.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => self.union(right),
            AlgebraOp::Intersect => self.intersect(right),
            AlgebraOp::Difference => self.difference(right),
        }
    }
}

// ---------------------------------------------------------------------------
// FunctionTable
// ---------------------------------------------------------------------------

impl FunctionTable {
    /// Union: merge by start; add aliases; left-biased range on existing start.
    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        for (start, rgroup) in right.groups() {
            if self.contains_start(start) {
                // Left-biased range: do not replace left end with right end.
                for (alias, count) in rgroup.aliases() {
                    self.insert_alias_at(start.clone(), alias.clone(), count.clone())?;
                }
            } else {
                // Right-only start: copy group wholesale (range + aliases).
                self.insert_group(clone_function_group(rgroup))?;
            }
        }
        self.assert_indexes_coherent()?;
        Ok(())
    }

    /// Intersection: common starts + common aliases; add common alias counts.
    ///
    /// Left range is retained. Groups that lose all aliases are deleted.
    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        let starts: Vec<LineKey> = self.groups().map(|(s, _)| s.clone()).collect();
        for start in starts {
            let Some(rgroup) = right.get_by_start(&start) else {
                self.remove_group(&start);
                continue;
            };

            let (end, common): (Option<LineKey>, Vec<(ByteString, CoverageCount)>) = {
                let lgroup = self.get_by_start(&start).expect("present");
                let end = lgroup.end().cloned();
                let common = lgroup
                    .aliases()
                    .iter()
                    .filter_map(|(alias, lcount)| {
                        rgroup
                            .aliases()
                            .get(alias)
                            .map(|rcount| lcount.add(rcount).map(|sum| (alias.clone(), sum)))
                    })
                    .collect::<Result<Vec<_>, _>>()?;
                (end, common)
            };

            self.remove_group(&start);
            if common.is_empty() {
                continue;
            }
            let (first_alias, first_count) = &common[0];
            let mut rebuilt = FunctionGroup::new(start.clone(), first_alias.clone(), end);
            let mut map = BTreeMap::new();
            for (alias, sum) in &common {
                map.insert(alias.clone(), sum.clone());
            }
            // Representative: shortest then lexical among survivors (defined CORE-004).
            let mut rep = first_alias.clone();
            let mut rep_len = crate::function::effective_alias_length(rep.as_bytes());
            for alias in map.keys() {
                let len = crate::function::effective_alias_length(alias.as_bytes());
                if len < rep_len || (len == rep_len && alias.as_bytes() < rep.as_bytes()) {
                    rep = alias.clone();
                    rep_len = len;
                }
            }
            let _ = first_count;
            rebuilt.set_aliases_for_algebra(map, rep);
            self.insert_group(rebuilt)?;
        }
        self.assert_indexes_coherent()?;
        Ok(())
    }

    /// Difference: remove common aliases; delete group when empty.
    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        let mut to_remove: Vec<ByteString> = Vec::new();
        for (alias, start) in self.alias_index() {
            if let Some(rgroup) = right.get_by_start(start) {
                if rgroup.aliases().contains_key(alias) {
                    to_remove.push(alias.clone());
                }
            }
        }
        for alias in to_remove {
            let _ = self.remove_alias(&alias);
        }
        self.assert_indexes_coherent()?;
        Ok(())
    }

    /// Apply [`AlgebraOp`] against `right`.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => self.union(right),
            AlgebraOp::Intersect => self.intersect(right),
            AlgebraOp::Difference => self.difference(right),
        }
    }
}

fn clone_function_group(group: &FunctionGroup) -> FunctionGroup {
    let mut aliases = group.aliases().iter();
    let (first_alias, first_count) = aliases.next().expect("group has ≥1 alias");
    let mut out = FunctionGroup::new(
        group.start().clone(),
        first_alias.clone(),
        group.end().cloned(),
    );
    let mut map = BTreeMap::new();
    map.insert(first_alias.clone(), first_count.clone());
    for (alias, count) in aliases {
        map.insert(alias.clone(), count.clone());
    }
    out.set_aliases_for_algebra(map, group.representative().clone());
    out
}

// ---------------------------------------------------------------------------
// BranchCoverage
// ---------------------------------------------------------------------------

impl BranchCoverage {
    /// Union: nth-signature match, merge edges, copy right-only occurrences.
    ///
    /// Does **not** implement the `U-BRANCH-INTERSECT` / cache-`changed` quirk
    /// (`M1-ALG-BRANCH-CACHE-001`); that residual remains deferred.
    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.merge_lines(right, AlgebraOp::Union)
    }

    /// Intersection: retain pairable matched signature occurrences only.
    ///
    /// Conventional structural match: unmatched left occurrences of a signature
    /// beyond the right multiplicity are dropped. Oracle may retain an unmatched
    /// left block when no matched edge merge reports `changed`
    /// (`M1-ALG-BRANCH-CACHE-001`) — intentionally not faked here.
    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.merge_lines(right, AlgebraOp::Intersect)
    }

    /// Difference: remove leading left blocks matched by right signature
    /// occurrences; retain the remainder.
    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.merge_lines(right, AlgebraOp::Difference)
    }

    /// Apply [`AlgebraOp`] against `right`.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => self.union(right),
            AlgebraOp::Intersect => self.intersect(right),
            AlgebraOp::Difference => self.difference(right),
        }
    }

    fn merge_lines(&mut self, right: &Self, op: AlgebraOp) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => {
                for (key, rline) in right.lines() {
                    if self.contains_line(key) {
                        let left_line = self.get_line_mut(key).expect("present");
                        merge_branch_line_union(left_line, rline)?;
                    } else {
                        self.insert_line(key.clone(), rline.clone());
                    }
                }
            }
            AlgebraOp::Intersect => {
                let keys: Vec<LineKey> = self.lines().map(|(k, _)| k.clone()).collect();
                for key in keys {
                    match right.get_line(&key) {
                        Some(rline) => {
                            let left_line = self.get_line_mut(&key).expect("present");
                            merge_branch_line_intersect(left_line, rline)?;
                            if left_line.is_empty() {
                                self.remove_line(&key);
                            }
                        }
                        None => {
                            self.remove_line(&key);
                        }
                    }
                }
            }
            AlgebraOp::Difference => {
                let keys: Vec<LineKey> = right.lines().map(|(k, _)| k.clone()).collect();
                for key in keys {
                    if let Some(left_line) = self.get_line_mut(&key) {
                        let rline = right.get_line(&key).expect("present");
                        merge_branch_line_difference(left_line, rline);
                        if left_line.is_empty() {
                            self.remove_line(&key);
                        }
                    }
                }
            }
        }
        self.assert_invariants().map_err(AlgebraError::Branch)?;
        Ok(())
    }
}

fn merge_branch_line_union(left: &mut BranchLine, right: &BranchLine) -> Result<(), AlgebraError> {
    // Snapshot left signatures/nth so we can mutate blocks without borrow conflicts.
    let left_meta: Vec<(usize, Vec<crate::branch_store::BranchKind>)> = left
        .blocks()
        .iter()
        .enumerate()
        .map(|(li, block)| {
            (
                count_signature_before(left.blocks(), li),
                block.signature().to_vec(),
            )
        })
        .collect();

    let mut right_matched = vec![false; right.blocks().len()];
    for (li, (nth, sig)) in left_meta.iter().enumerate() {
        if let Some(ri) = find_nth_signature(right.blocks(), sig, *nth) {
            merge_branch_block(&mut left.blocks_mut()[li], &right.blocks()[ri])?;
            right_matched[ri] = true;
        }
    }

    // Copy right-only signature occurrences in right order.
    for (ri, matched) in right_matched.iter().enumerate() {
        if !matched {
            left.append_block(right.blocks()[ri].clone());
        }
    }
    renumber_branch_line(left);
    Ok(())
}

fn merge_branch_line_intersect(
    left: &mut BranchLine,
    right: &BranchLine,
) -> Result<(), AlgebraError> {
    let mut kept: Vec<BranchBlock> = Vec::new();
    for (li, lblock) in left.blocks().iter().enumerate() {
        let nth = count_signature_before(left.blocks(), li);
        if let Some(ri) = find_nth_signature(right.blocks(), lblock.signature(), nth) {
            let mut merged = lblock.clone();
            merge_branch_block(&mut merged, &right.blocks()[ri])?;
            kept.push(merged);
        }
        // else: unmatched left occurrence dropped (conventional intersect).
    }
    *left.blocks_mut() = kept;
    renumber_branch_line(left);
    Ok(())
}

fn merge_branch_line_difference(left: &mut BranchLine, right: &BranchLine) {
    // Remove leading left blocks that pair with right signature occurrences.
    let mut remove = vec![false; left.blocks().len()];
    for (ri, rblock) in right.blocks().iter().enumerate() {
        let nth = count_signature_before(right.blocks(), ri);
        if let Some(li) = find_nth_signature(left.blocks(), rblock.signature(), nth) {
            remove[li] = true;
        }
    }
    let mut kept = Vec::new();
    for (i, block) in left.blocks().iter().enumerate() {
        if !remove[i] {
            kept.push(block.clone());
        }
    }
    *left.blocks_mut() = kept;
    renumber_branch_line(left);
}

fn merge_branch_block(left: &mut BranchBlock, right: &BranchBlock) -> Result<(), AlgebraError> {
    let n = left.edges().len().min(right.edges().len());
    for i in 0..n {
        let redge = &right.edges()[i];
        let ledge = &mut left.edges_mut()[i];
        let merged_taken = ledge
            .taken()
            .merge_with(redge.taken())
            .map_err(AlgebraError::BranchTaken)?;
        *ledge.taken_mut() = merged_taken;
        // Left expression retained when they differ (no assignment needed).
        if redge.is_excluded() {
            ledge.set_excluded();
        }
    }
    // Extra right edges beyond left length: not appended (signature identity is
    // kinds-only and matched blocks share signature length).
    let _ = right;
    Ok(())
}

fn count_signature_before(blocks: &[BranchBlock], index: usize) -> usize {
    let sig = blocks[index].signature();
    blocks[..index]
        .iter()
        .filter(|b| b.signature() == sig)
        .count()
}

fn find_nth_signature(
    blocks: &[BranchBlock],
    signature: &[crate::branch_store::BranchKind],
    nth: usize,
) -> Option<usize> {
    let mut seen = 0usize;
    for (i, block) in blocks.iter().enumerate() {
        if block.signature() == signature {
            if seen == nth {
                return Some(i);
            }
            seen += 1;
        }
    }
    None
}

fn renumber_branch_line(line: &mut BranchLine) {
    for (pos, block) in line.blocks_mut().iter_mut().enumerate() {
        block.set_model_position(pos);
        block.rebuild_signature_and_indexes();
    }
}

// ---------------------------------------------------------------------------
// McdcCoverage
// ---------------------------------------------------------------------------

impl McdcCoverage {
    /// Union: add compatible sense counts; copy right-only lines / groups.
    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.merge_lines(right, AlgebraOp::Union)
    }

    /// Intersection: common lines only; within a line, merge common groups and
    /// copy right-only groups when the line stays compatible.
    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.merge_lines(right, AlgebraOp::Intersect)
    }

    /// Difference: remove an entire left line when the right side has that line.
    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        let keys: Vec<LineKey> = right.lines().map(|(k, _)| k.clone()).collect();
        for key in keys {
            self.remove_line(&key);
        }
        Ok(())
    }

    /// Apply [`AlgebraOp`] against `right`.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => self.union(right),
            AlgebraOp::Intersect => self.intersect(right),
            AlgebraOp::Difference => self.difference(right),
        }
    }

    fn merge_lines(&mut self, right: &Self, op: AlgebraOp) -> Result<(), AlgebraError> {
        match op {
            AlgebraOp::Union => {
                for (key, rline) in right.lines() {
                    if self.contains_line(key) {
                        let left_line = self.get_line_mut(key).expect("present");
                        merge_mcdc_line(left_line, rline, AlgebraOp::Union, key)?;
                    } else {
                        self.insert_line(key.clone(), rline.clone());
                    }
                }
            }
            AlgebraOp::Intersect => {
                let keys: Vec<LineKey> = self.lines().map(|(k, _)| k.clone()).collect();
                for key in keys {
                    match right.get_line(&key) {
                        Some(rline) => {
                            let left_line = self.get_line_mut(&key).expect("present");
                            merge_mcdc_line(left_line, rline, AlgebraOp::Intersect, &key)?;
                            if left_line.is_empty() {
                                self.remove_line(&key);
                            }
                        }
                        None => {
                            self.remove_line(&key);
                        }
                    }
                }
            }
            AlgebraOp::Difference => unreachable!("handled above"),
        }
        self.assert_invariants().map_err(AlgebraError::Mcdc)?;
        Ok(())
    }
}

fn merge_mcdc_line(
    left: &mut McdcLine,
    right: &McdcLine,
    op: AlgebraOp,
    line_key: &LineKey,
) -> Result<(), AlgebraError> {
    let mut incompatible = false;
    let right_only: Vec<(GroupSizeKey, Vec<McdcExpression>)> = right
        .iter_groups()
        .filter(|(k, _)| left.get_group(k).is_none())
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();

    let common_keys: Vec<GroupSizeKey> = left
        .iter_groups()
        .map(|(k, _)| k.clone())
        .filter(|k| right.get_group(k).is_some())
        .collect();

    for key in &common_keys {
        let right_vec = right.get_group(key).expect("filtered");
        let left_vec = left.get_group_mut(key).expect("present");
        match merge_mcdc_vectors(left_vec, right_vec, line_key, key)? {
            MergeVectorOutcome::Merged => {}
            MergeVectorOutcome::ExpressionMismatch => {
                incompatible = true;
                // Leave left vector unchanged (Oracle continuation keeps left).
            }
        }
    }

    if op == AlgebraOp::Intersect {
        // Drop left-only groups.
        let left_only: Vec<GroupSizeKey> = left
            .iter_groups()
            .map(|(k, _)| k.clone())
            .filter(|k| right.get_group(k).is_none())
            .collect();
        for key in left_only {
            left.groups_mut_for_algebra().remove(&key);
        }
    }

    // Copy right-only groups for union and intersect when the shared line did
    // not hit an expression mismatch (matches md013 vs md013-expr fixtures).
    if !incompatible {
        for (key, exprs) in right_only {
            left.groups_mut_for_algebra().insert(key, exprs);
        }
    }

    Ok(())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum MergeVectorOutcome {
    Merged,
    ExpressionMismatch,
}

fn merge_mcdc_vectors(
    left: &mut [McdcExpression],
    right: &[McdcExpression],
    line_key: &LineKey,
    group_key: &GroupSizeKey,
) -> Result<MergeVectorOutcome, AlgebraError> {
    if left.len() > right.len() {
        // Longer left would dereference undefined right elements in Oracle.
        return Err(AlgebraError::McdcAsymmetricVector {
            line: line_key.clone(),
            group: group_key.clone(),
            left_len: left.len(),
            right_len: right.len(),
        });
    }

    // Compatibility: expression bytes at each paired position.
    let pair = left.len(); // shorter/equal left; ignore extra right exprs
    for i in 0..pair {
        if left[i].expression() != right[i].expression() {
            return Ok(MergeVectorOutcome::ExpressionMismatch);
        }
    }

    for i in 0..pair {
        left[i].merge_senses_from(&right[i])?;
    }
    Ok(MergeVectorOutcome::Merged)
}

// ---------------------------------------------------------------------------
// CoverageStore / TestcaseStores thin wrappers
// ---------------------------------------------------------------------------

impl CoverageStore {
    /// Apply an ordered algebra op to every coverage family.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        self.lines_mut().apply_op(op, right.lines())?;
        self.functions_mut().apply_op(op, right.functions())?;
        self.branches_mut().apply_op(op, right.branches())?;
        self.mcdc_mut().apply_op(op, right.mcdc())?;
        Ok(())
    }

    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Union, right)
    }

    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Intersect, right)
    }

    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Difference, right)
    }
}

impl TestcaseStores {
    /// Ordered algebra over per-family `TestName` maps.
    ///
    /// **Documented CORE-004 choice (pending `M1-MD-014` exact pin):**
    /// - **Union:** merge matching test names; insert clones of right-only
    ///   names; retain left-only names.
    /// - **Intersect / Difference:** operate only on names present on the
    ///   right that also exist on the left; **retain left-only** names; do
    ///   **not** invent empty right-only maps. Exact Oracle lazy empty-map
    ///   creation remains deferred.
    pub fn apply_op(&mut self, op: AlgebraOp, right: &Self) -> Result<(), AlgebraError> {
        apply_testcase_map(self.lines_mut(), right.lines(), op, LineCoverage::apply_op)?;
        apply_testcase_map(
            self.functions_mut(),
            right.functions(),
            op,
            FunctionTable::apply_op,
        )?;
        apply_testcase_map(
            self.branches_mut(),
            right.branches(),
            op,
            BranchCoverage::apply_op,
        )?;
        apply_testcase_map(self.mcdc_mut(), right.mcdc(), op, McdcCoverage::apply_op)?;
        Ok(())
    }

    pub fn union(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Union, right)
    }

    pub fn intersect(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Intersect, right)
    }

    pub fn difference(&mut self, right: &Self) -> Result<(), AlgebraError> {
        self.apply_op(AlgebraOp::Difference, right)
    }
}

fn apply_testcase_map<V, F>(
    left: &mut BTreeMap<TestName, V>,
    right: &BTreeMap<TestName, V>,
    op: AlgebraOp,
    mut apply: F,
) -> Result<(), AlgebraError>
where
    V: Clone,
    F: FnMut(&mut V, AlgebraOp, &V) -> Result<(), AlgebraError>,
{
    match op {
        AlgebraOp::Union => {
            for (name, rvalue) in right {
                if let Some(lvalue) = left.get_mut(name) {
                    apply(lvalue, AlgebraOp::Union, rvalue)?;
                } else {
                    left.insert(name.clone(), rvalue.clone());
                }
            }
        }
        AlgebraOp::Intersect | AlgebraOp::Difference => {
            // Only mutate keys present on both sides. Retain left-only.
            let common: Vec<TestName> = right
                .keys()
                .filter(|n| left.contains_key(*n))
                .cloned()
                .collect();
            for name in common {
                let rvalue = right.get(&name).expect("filtered");
                let lvalue = left.get_mut(&name).expect("filtered");
                apply(lvalue, op, rvalue)?;
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{AlgebraError, AlgebraOp};
    use crate::branch::BranchTaken;
    use crate::branch_store::{BranchCoverage, BranchEdge, BranchKind};
    use crate::bytes::ByteString;
    use crate::function::FunctionTable;
    use crate::keys::LineKey;
    use crate::line::LineCoverage;
    use crate::mcdc::{GroupSizeKey, McdcCoverage};
    use crate::numeric::{CoverageCount, NumericAtom};

    fn count(lex: &str) -> CoverageCount {
        CoverageCount::from_lexeme(lex)
    }

    fn line_key(lex: &str) -> LineKey {
        LineKey::from_lexeme(lex)
    }

    #[test]
    fn line_union_intersect_diff_order_and_non_min_intersection() {
        // md010 small-integer subset: L={10:1,20:2} R={10:4,30:8}
        let mut left = LineCoverage::new();
        left.insert(line_key("10"), count("1"));
        left.insert(line_key("20"), count("2"));
        let mut right = LineCoverage::new();
        right.insert(line_key("10"), count("4"));
        right.insert(line_key("30"), count("8"));

        let mut u = left.clone();
        u.union(&right).unwrap();
        assert_eq!(u.get(&line_key("10")).unwrap().lexeme().as_bytes(), b"5");
        assert_eq!(u.get(&line_key("20")).unwrap().lexeme().as_bytes(), b"2");
        assert_eq!(u.get(&line_key("30")).unwrap().lexeme().as_bytes(), b"8");

        let mut i = left.clone();
        i.intersect(&right).unwrap();
        // Intersection ADDS (1+4=5), does not take min(1,4)=1.
        assert_eq!(i.len(), 1);
        assert_eq!(i.get(&line_key("10")).unwrap().lexeme().as_bytes(), b"5");
        assert!(!i.contains_key(&line_key("20")));

        let mut d = left.clone();
        d.difference(&right).unwrap();
        assert_eq!(d.len(), 1);
        assert_eq!(d.get(&line_key("20")).unwrap().lexeme().as_bytes(), b"2");

        // Operand order: difference is non-commutative.
        let mut d_rev = right.clone();
        d_rev.difference(&left).unwrap();
        assert_eq!(d_rev.len(), 1);
        assert_eq!(
            d_rev.get(&line_key("30")).unwrap().lexeme().as_bytes(),
            b"8"
        );
        assert_ne!(d, d_rev);
    }

    #[test]
    fn function_union_merges_aliases_and_keeps_indexes_coherent() {
        // md011 start 10: L aa=2,b=3 end=20; R aa=7,c=11 end=99
        let mut left = FunctionTable::new();
        let s10 = line_key("10");
        left.insert_alias_at(s10.clone(), "aa", count("2")).unwrap();
        left.insert_alias_at(s10.clone(), "b", count("3")).unwrap();
        left.set_group_end(&s10, Some(line_key("20")));
        left.insert_alias_at(line_key("30"), "left_only", count("5"))
            .unwrap();
        left.set_group_end(&line_key("30"), Some(line_key("40")));

        let mut right = FunctionTable::new();
        right
            .insert_alias_at(s10.clone(), "aa", count("7"))
            .unwrap();
        right
            .insert_alias_at(s10.clone(), "c", count("11"))
            .unwrap();
        right.set_group_end(&s10, Some(line_key("99")));
        right
            .insert_alias_at(line_key("50"), "right_only", count("13"))
            .unwrap();
        right.set_group_end(&line_key("50"), Some(line_key("60")));

        left.union(&right).unwrap();
        left.assert_indexes_coherent().unwrap();

        let g10 = left.get_by_start(&s10).unwrap();
        assert_eq!(
            g10.end().map(|e| e.lexeme().as_bytes()),
            Some(b"20".as_slice())
        ); // left-biased
        assert_eq!(
            g10.aliases()
                .get(&ByteString::from("aa"))
                .unwrap()
                .lexeme()
                .as_bytes(),
            b"9"
        );
        assert_eq!(
            g10.aliases()
                .get(&ByteString::from("b"))
                .unwrap()
                .lexeme()
                .as_bytes(),
            b"3"
        );
        assert_eq!(
            g10.aliases()
                .get(&ByteString::from("c"))
                .unwrap()
                .lexeme()
                .as_bytes(),
            b"11"
        );
        assert!(left.contains_alias(&ByteString::from("left_only")));
        assert!(left.contains_alias(&ByteString::from("right_only")));
        assert_eq!(left.group_len(), 3);
    }

    #[test]
    fn function_difference_removes_aliases_and_drops_empty_groups() {
        let mut left = FunctionTable::new();
        let s10 = line_key("10");
        left.insert_alias_at(s10.clone(), "aa", count("2")).unwrap();
        left.insert_alias_at(s10.clone(), "b", count("3")).unwrap();
        left.insert_alias_at(line_key("30"), "left_only", count("5"))
            .unwrap();

        let mut right = FunctionTable::new();
        right
            .insert_alias_at(s10.clone(), "aa", count("7"))
            .unwrap();
        right
            .insert_alias_at(s10.clone(), "c", count("11"))
            .unwrap();

        left.difference(&right).unwrap();
        left.assert_indexes_coherent().unwrap();
        // aa removed; b remains; left_only remains
        assert!(!left.contains_alias(&ByteString::from("aa")));
        assert!(left.contains_alias(&ByteString::from("b")));
        assert!(left.contains_alias(&ByteString::from("left_only")));
        assert_eq!(
            left.get_by_start(&s10).unwrap().representative().as_bytes(),
            b"b"
        );

        // Removing last alias drops the group.
        let mut only = FunctionTable::new();
        only.insert_alias_at(s10.clone(), "aa", count("1")).unwrap();
        let mut r2 = FunctionTable::new();
        r2.insert_alias_at(s10.clone(), "aa", count("1")).unwrap();
        only.difference(&r2).unwrap();
        assert!(!only.contains_start(&s10));
        only.assert_indexes_coherent().unwrap();
    }

    #[test]
    fn branch_union_matches_nth_signature_occurrence() {
        // Two left blocks with signature `be`; right one `be` merges the first.
        let mut left = BranchCoverage::new();
        let key = line_key("10");
        {
            let line = left.entry_line(key.clone());
            line.push_block();
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("1"),
                BranchKind::Vanilla,
                Some(ByteString::from("left-a")),
                false,
            ));
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("-"),
                BranchKind::Exception,
                Some(ByteString::from("left-b")),
                false,
            ));
            line.push_block();
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("2"),
                BranchKind::Vanilla,
                Some(ByteString::from("left-c")),
                false,
            ));
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("0"),
                BranchKind::Exception,
                Some(ByteString::from("left-d")),
                false,
            ));
        }

        let mut right = BranchCoverage::new();
        {
            let line = right.entry_line(key.clone());
            line.push_block();
            let mut e0 = BranchEdge::new(
                BranchTaken::from_token("4"),
                BranchKind::Vanilla,
                Some(ByteString::from("right-a")),
                false,
            );
            e0.set_excluded();
            line.last_block_mut().unwrap().append_edge(e0);
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("5"),
                BranchKind::Exception,
                Some(ByteString::from("right-b")),
                false,
            ));
        }

        left.union(&right).unwrap();
        left.assert_invariants().unwrap();
        let blocks = left.get_line(&key).unwrap().blocks();
        assert_eq!(blocks.len(), 2);
        // First block merged: 1+4=5, - merges with 5 → 5; left expr retained; excluded sticky.
        assert_eq!(
            blocks[0].edges()[0]
                .taken()
                .as_evaluated()
                .unwrap()
                .lexeme()
                .as_bytes(),
            b"5"
        );
        assert!(blocks[0].edges()[0].is_excluded());
        assert_eq!(
            blocks[0].edges()[0].expression().map(ByteString::as_bytes),
            Some(b"left-a".as_slice())
        );
        // Second block retained unmatched.
        assert_eq!(
            blocks[1].edges()[0].expression().map(ByteString::as_bytes),
            Some(b"left-c".as_slice())
        );

        // Difference removes the leading matched occurrence only.
        let mut diff_left = BranchCoverage::new();
        {
            let line = diff_left.entry_line(key.clone());
            for block in blocks {
                line.append_block(block.clone());
            }
        }
        // Rebuild original left for clean difference probe.
        let mut orig_left = BranchCoverage::new();
        {
            let line = orig_left.entry_line(key.clone());
            line.push_block();
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("1"),
                BranchKind::Vanilla,
                Some(ByteString::from("left-a")),
                false,
            ));
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("-"),
                BranchKind::Exception,
                Some(ByteString::from("left-b")),
                false,
            ));
            line.push_block();
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("2"),
                BranchKind::Vanilla,
                Some(ByteString::from("left-c")),
                false,
            ));
            line.last_block_mut().unwrap().append_edge(BranchEdge::new(
                BranchTaken::from_token("0"),
                BranchKind::Exception,
                Some(ByteString::from("left-d")),
                false,
            ));
        }
        orig_left.difference(&right).unwrap();
        let dblocks = orig_left.get_line(&key).unwrap().blocks();
        assert_eq!(dblocks.len(), 1);
        assert_eq!(
            dblocks[0].edges()[0].expression().map(ByteString::as_bytes),
            Some(b"left-c".as_slice())
        );
    }

    #[test]
    fn mcdc_both_sense_add_and_sticky_exclusion_on_merge() {
        let mut left = McdcCoverage::new();
        let key = line_key("20");
        let size = GroupSizeKey::from_lexeme("2");
        {
            let line = left.entry_line(key.clone());
            let e0 = line.append_expression(size.clone(), NumericAtom::from_lexeme("0"), "a");
            e0.set_sense(true, count("1"), false).unwrap();
            e0.set_sense(false, count("0"), false).unwrap();
            let e1 = line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "b");
            e1.set_sense(true, count("2"), true).unwrap(); // sticky exclude on true
            e1.set_sense(false, count("0"), false).unwrap();
        }

        let mut right = McdcCoverage::new();
        {
            let line = right.entry_line(key.clone());
            let e0 = line.append_expression(size.clone(), NumericAtom::from_lexeme("0"), "a");
            e0.set_sense(true, count("3"), true).unwrap(); // right exclusion
            e0.set_sense(false, count("4"), false).unwrap();
            let e1 = line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "b");
            e1.set_sense(true, count("5"), false).unwrap();
            e1.set_sense(false, count("6"), false).unwrap();
            // right-only group size 3
            let size3 = GroupSizeKey::from_lexeme("3");
            line.append_expression(size3, NumericAtom::from_lexeme("0"), "c");
        }

        left.union(&right).unwrap();
        let line = left.get_line(&key).unwrap();
        let g2 = line.get_group(&size).unwrap();
        assert_eq!(g2[0].true_sense().count().lexeme().as_bytes(), b"4"); // 1+3
        assert_eq!(g2[0].false_sense().count().lexeme().as_bytes(), b"4");
        assert!(g2[0].true_sense().is_excluded()); // sticky from right
        assert_eq!(g2[1].true_sense().count().lexeme().as_bytes(), b"7"); // 2+5
        assert!(g2[1].true_sense().is_excluded()); // sticky from left
        assert_eq!(g2[1].false_sense().count().lexeme().as_bytes(), b"6");
        // right-only group copied on union
        assert!(line.get_group(&GroupSizeKey::from_lexeme("3")).is_some());
    }

    #[test]
    fn mcdc_difference_removes_whole_line() {
        let mut left = McdcCoverage::new();
        let k20 = line_key("20");
        let k30 = line_key("30");
        {
            let line = left.entry_line(k20.clone());
            line.append_expression(
                GroupSizeKey::from_lexeme("1"),
                NumericAtom::from_lexeme("0"),
                "a",
            );
        }
        {
            let line = left.entry_line(k30.clone());
            line.append_expression(
                GroupSizeKey::from_lexeme("1"),
                NumericAtom::from_lexeme("0"),
                "z",
            );
        }

        let mut right = McdcCoverage::new();
        right.entry_line(k20.clone());

        left.difference(&right).unwrap();
        assert!(!left.contains_line(&k20));
        assert!(left.contains_line(&k30));
    }

    #[test]
    fn operand_order_matters_for_function_range_bias() {
        let mut a = FunctionTable::new();
        let s = line_key("10");
        a.insert_alias_at(s.clone(), "aa", count("2")).unwrap();
        a.set_group_end(&s, Some(line_key("20")));

        let mut b = FunctionTable::new();
        b.insert_alias_at(s.clone(), "aa", count("7")).unwrap();
        b.set_group_end(&s, Some(line_key("99")));

        let mut ab = a.clone();
        ab.union(&b).unwrap();
        let mut ba = b.clone();
        ba.union(&a).unwrap();

        assert_eq!(
            ab.get_by_start(&s)
                .unwrap()
                .end()
                .map(|e| e.lexeme().as_bytes()),
            Some(b"20".as_slice())
        );
        assert_eq!(
            ba.get_by_start(&s)
                .unwrap()
                .end()
                .map(|e| e.lexeme().as_bytes()),
            Some(b"99".as_slice())
        );
        // Same alias sums, different retained ranges → order matters.
        assert_ne!(ab, ba);
    }

    #[test]
    fn mcdc_asymmetric_longer_left_is_fail_closed_result() {
        let mut left = McdcCoverage::new();
        let key = line_key("20");
        let size = GroupSizeKey::from_lexeme("3");
        {
            let line = left.entry_line(key.clone());
            line.append_expression(size.clone(), NumericAtom::from_lexeme("0"), "c");
            line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "d");
            line.append_expression(size.clone(), NumericAtom::from_lexeme("2"), "e");
        }
        let mut right = McdcCoverage::new();
        {
            let line = right.entry_line(key.clone());
            line.append_expression(size.clone(), NumericAtom::from_lexeme("0"), "c");
            line.append_expression(size.clone(), NumericAtom::from_lexeme("1"), "d");
        }

        let err = left.union(&right).expect_err("asymmetric");
        assert!(matches!(
            err,
            AlgebraError::McdcAsymmetricVector {
                left_len: 3,
                right_len: 2,
                ..
            }
        ));
    }

    #[test]
    fn coverage_store_apply_op_smoke() {
        let mut left = crate::stores::CoverageStore::new();
        left.lines_mut().insert(line_key("1"), count("1"));
        let mut right = crate::stores::CoverageStore::new();
        right.lines_mut().insert(line_key("1"), count("2"));
        right.lines_mut().insert(line_key("2"), count("3"));
        left.apply_op(AlgebraOp::Union, &right).unwrap();
        assert_eq!(left.lines().len(), 2);
        assert_eq!(
            left.lines()
                .get(&line_key("1"))
                .unwrap()
                .lexeme()
                .as_bytes(),
            b"3"
        );
    }
}
