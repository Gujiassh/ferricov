//! Tiny, independent algebra interpreters used by the CORE-009 fuzz targets.
//!
//! These intentionally do not call the model algebra while computing expected
//! results.  The generated domain is small and regular (one item per right
//! operand), which keeps the reference rules inspectable.

use std::collections::BTreeMap;

use ferricov_model::{
    AlgebraOp, BranchCoverage, BranchEdge, BranchKind, BranchTaken, ByteString, CoverageCount,
    FunctionTable, GroupSizeKey, LineCoverage, LineKey, McdcCoverage, NumericAtom,
};

fn op(byte: u8) -> AlgebraOp {
    match byte % 3 {
        0 => AlgebraOp::Union,
        1 => AlgebraOp::Intersect,
        _ => AlgebraOp::Difference,
    }
}

fn count(value: u8) -> u64 {
    u64::from(value % 7 + 1)
}
fn line(value: u8) -> u64 {
    u64::from(value % 8 + 1)
}
fn lk(value: u64) -> LineKey {
    LineKey::from_lexeme(value.to_string())
}
fn cc(value: u64) -> CoverageCount {
    CoverageCount::from_lexeme(value.to_string())
}
fn number(value: &CoverageCount) -> u64 {
    std::str::from_utf8(value.lexeme().as_bytes())
        .unwrap()
        .parse()
        .unwrap()
}

/// Run an ordered line-algebra program and compare every step with a small map oracle.
pub(super) fn run_line_program(input: &[u8]) {
    let mut actual = LineCoverage::new();
    let mut expected = BTreeMap::<u64, u64>::new();
    for chunk in input.chunks(3).take(64).filter(|c| c.len() == 3) {
        let operation = op(chunk[0]);
        let key = line(chunk[1]);
        let value = count(chunk[2]);
        let mut right = LineCoverage::new();
        right.insert(lk(key), cc(value));
        actual.apply_op(operation, &right).unwrap();
        map_step(&mut expected, operation, key, value);
        let observed = actual
            .iter()
            .map(|(k, v)| (number_atom(k.atom()), number(v)))
            .collect::<BTreeMap<_, _>>();
        assert_eq!(observed, expected);
    }
}

fn map_step(map: &mut BTreeMap<u64, u64>, operation: AlgebraOp, key: u64, value: u64) {
    match operation {
        AlgebraOp::Union => *map.entry(key).or_default() += value,
        AlgebraOp::Intersect => match map.get_mut(&key) {
            Some(old) => *old += value,
            None => map.clear(),
        },
        AlgebraOp::Difference => {
            map.remove(&key);
        }
    }
    if operation == AlgebraOp::Intersect {
        map.retain(|candidate, _| *candidate == key);
    }
}

/// Run a program over single-alias function groups.
pub(super) fn run_function_program(input: &[u8]) {
    let mut actual = FunctionTable::new();
    let mut expected = BTreeMap::<u64, u64>::new();
    for chunk in input.chunks(3).take(64).filter(|c| c.len() == 3) {
        let operation = op(chunk[0]);
        let key = line(chunk[1]);
        let value = count(chunk[2]);
        let alias = format!("f{key}");
        let mut right = FunctionTable::new();
        right
            .insert_alias_at(lk(key), alias.as_str(), cc(value))
            .unwrap();
        actual.apply_op(operation, &right).unwrap();
        map_step(&mut expected, operation, key, value);
        actual.assert_indexes_coherent().unwrap();
        let observed = actual
            .groups()
            .map(|(start, group)| {
                let value = group.aliases().values().next().map(number).unwrap();
                (number_atom(start.atom()), value)
            })
            .collect::<BTreeMap<_, _>>();
        assert_eq!(observed, expected);
    }
}

/// Run a program over one-edge branch blocks with a stable signature per line.
pub(super) fn run_branch_program(input: &[u8]) {
    let mut actual = BranchCoverage::new();
    let mut expected = BTreeMap::<u64, u64>::new();
    for chunk in input.chunks(3).take(64).filter(|c| c.len() == 3) {
        let operation = op(chunk[0]);
        let key = line(chunk[1]);
        let value = count(chunk[2]);
        let mut right = BranchCoverage::new();
        let block = right.entry_line(lk(key));
        block.push_block();
        block.last_block_mut().unwrap().append_edge(BranchEdge::new(
            BranchTaken::evaluated(cc(value)),
            BranchKind::Vanilla,
            None,
            false,
        ));
        actual.apply_op(operation, &right).unwrap();
        map_step(&mut expected, operation, key, value);
        actual.assert_invariants().unwrap();
        let observed = actual
            .lines()
            .map(|(key, branch_line)| {
                let taken = branch_line.blocks()[0].edges()[0]
                    .taken()
                    .as_evaluated()
                    .unwrap();
                (number_atom(key.atom()), number(taken))
            })
            .collect::<BTreeMap<_, _>>();
        assert_eq!(observed, expected);
    }
}

/// Run a program over one-expression MC/DC lines with both senses populated.
pub(super) fn run_mcdc_program(input: &[u8]) {
    let mut actual = McdcCoverage::new();
    let mut expected = BTreeMap::<u64, u64>::new();
    for chunk in input.chunks(3).take(64).filter(|c| c.len() == 3) {
        let operation = op(chunk[0]);
        let key = line(chunk[1]);
        let value = count(chunk[2]);
        let mut right = McdcCoverage::new();
        let expr = right.entry_line(lk(key)).append_expression(
            GroupSizeKey::from_lexeme("1"),
            NumericAtom::from_lexeme("0"),
            ByteString::from("x"),
        );
        expr.set_sense(false, cc(value), false).unwrap();
        expr.set_sense(true, cc(value), false).unwrap();
        actual.apply_op(operation, &right).unwrap();
        map_step(&mut expected, operation, key, value);
        actual.assert_invariants().unwrap();
        let observed = actual
            .lines()
            .map(|(key, mcdc_line)| {
                let expr = &mcdc_line.groups().values().next().unwrap()[0];
                assert_eq!(expr.false_sense().count(), expr.true_sense().count());
                (number_atom(key.atom()), number(expr.false_sense().count()))
            })
            .collect::<BTreeMap<_, _>>();
        assert_eq!(observed, expected);
    }
}

fn number_atom(value: &NumericAtom) -> u64 {
    std::str::from_utf8(value.lexeme().as_bytes())
        .unwrap()
        .parse()
        .unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reference_programs_cover_ordered_operations() {
        let program = [0, 1, 2, 0, 1, 3, 1, 1, 4, 2, 1, 5, 0, 2, 6];
        run_line_program(&program);
        run_function_program(&program);
        run_branch_program(&program);
        run_mcdc_program(&program);
    }

    #[test]
    fn difference_is_operand_ordered() {
        let program = [0, 1, 2, 2, 2, 9];
        run_line_program(&program);
        run_function_program(&program);
        run_branch_program(&program);
        run_mcdc_program(&program);
    }
}
