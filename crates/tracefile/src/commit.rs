//! Section commit on `end_of_record` (and MC/DC close helpers).
//!
//! Normative close rules (grammar + coverage-model):
//! - union current testcase line / function / branch into aggregate;
//! - MC/DC: mutate aggregate first, then clone the open block into the
//!   *current* test name (`U-MCDC-LATE-TN`);
//! - source-scoped version / checksums merge into [`SourceCoverage`];
//! - terminator does not fully clear the source binding (Oracle residual).

use ferricov_model::{
    AlgebraOp, CoverageDatabase, McdcCoverage, SourceCoverage, TestName,
};

use crate::diag::{DiagClass, DiagKind, ParseDiag};
use crate::section::OpenSection;

/// Outcome of attempting to commit an open section.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CommitOutcome {
    /// Section committed into the database.
    Committed,
    /// No open section / skipped section — nothing to commit.
    Noop,
    /// Hard failure during union / MC/DC close.
    HardFail(ParseDiag),
}

/// Close the open MC/DC block onto aggregate + current test name.
///
/// Line/function/branch are *not* touched here. Callers pass the current
/// parser test name (may differ from SF-bound after a late `TN`).
pub fn close_mcdc_block(
    source: &mut SourceCoverage,
    open: &mut OpenSection,
    current_test_name: &TestName,
    line_no: u64,
) -> Result<(), ParseDiag> {
    if open.mcdc_closed || open.mcdc_open.is_empty() {
        open.mcdc_closed = true;
        return Ok(());
    }

    // Aggregate first (Oracle mutates aggregate, then clones into testcase).
    source
        .aggregate_mut()
        .mcdc_mut()
        .apply_op(AlgebraOp::Union, &open.mcdc_open)
        .map_err(|err| {
            ParseDiag::hard_fail(
                DiagKind::Deferred,
                line_no,
                format!("MC/DC aggregate union failed: {err}"),
                None,
            )
        })?;

    // Clone open block into the *current* test name (U-MCDC-LATE-TN).
    let tc_map = source.testcases_mut().mcdc_mut();
    match tc_map.get_mut(current_test_name) {
        Some(existing) => {
            existing
                .apply_op(AlgebraOp::Union, &open.mcdc_open)
                .map_err(|err| {
                    ParseDiag::hard_fail(
                        DiagKind::Deferred,
                        line_no,
                        format!("MC/DC testcase union failed: {err}"),
                        None,
                    )
                })?;
        }
        None => {
            tc_map.insert(current_test_name.clone(), open.mcdc_open.clone());
        }
    }

    // Mark every line in the open block as closed for revisit detection.
    for (key, _) in open.mcdc_open.lines() {
        open.mcdc_closed_lines.insert(key.clone(), ());
    }
    open.mcdc_open = McdcCoverage::new();
    open.mcdc_current_line = None;
    open.mcdc_closed = true;
    Ok(())
}

/// Commit an open section into `db` using `current_test_name` for MC/DC close.
pub fn commit_section(
    db: &mut CoverageDatabase,
    open: &mut OpenSection,
    current_test_name: &TestName,
    line_no: u64,
) -> CommitOutcome {
    let key = open.identity().lookup_key().clone();
    if !db.contains_key(&key) {
        db.insert(SourceCoverage::new(open.identity().clone()));
    }
    let Some(source) = db.get_mut(&key) else {
        return CommitOutcome::HardFail(ParseDiag::hard_fail(
            DiagKind::Deferred,
            line_no,
            "internal: missing source after insert",
            None,
        ));
    };

    // Version: identical repeats OK; conflicting second version hard-fails.
    if let Some(ver) = &open.version {
        match source.version() {
            None => source.set_version(Some(ver.clone())),
            Some(existing) if existing == ver => {}
            Some(existing) => {
                return CommitOutcome::HardFail(ParseDiag::version_conflict(
                    line_no,
                    format!(
                        "conflicting version for {}: '{}' vs '{}'",
                        open.identity().display_path().to_string_lossy(),
                        existing.to_string_lossy(),
                        ver.to_string_lossy()
                    ),
                    Some(ver.clone()),
                ));
            }
        }
    }

    // Checksums: first-wins for a line key (verification is residual).
    for (line, chk) in &open.checksums {
        source.checksums_mut().entry(line.clone()).or_insert_with(|| chk.clone());
    }

    let bound = open.bound_test_name().clone();

    // Ensure SF-bound testcase family entries exist (even if empty contribution
    // after MC/DC-only sections — presence is independent per family).
    {
        let tc = source.testcases_mut();
        let lines_map = tc.lines_mut();
        let entry = lines_map.entry(bound.clone()).or_insert_with(ferricov_model::LineCoverage::new);
        if let Err(err) = entry.apply_op(AlgebraOp::Union, &open.lines) {
            return CommitOutcome::HardFail(ParseDiag::hard_fail(
                DiagKind::Deferred,
                line_no,
                format!("line testcase union failed: {err}"),
                None,
            ));
        }
    }
    {
        let tc = source.testcases_mut();
        let fn_map = tc.functions_mut();
        let entry = fn_map
            .entry(bound.clone())
            .or_insert_with(ferricov_model::FunctionTable::new);
        if let Err(err) = entry.apply_op(AlgebraOp::Union, &open.functions) {
            return CommitOutcome::HardFail(ParseDiag::hard_fail(
                DiagKind::Deferred,
                line_no,
                format!("function testcase union failed: {err}"),
                None,
            ));
        }
    }
    {
        let tc = source.testcases_mut();
        let br_map = tc.branches_mut();
        let entry = br_map
            .entry(bound.clone())
            .or_insert_with(ferricov_model::BranchCoverage::new);
        if let Err(err) = entry.apply_op(AlgebraOp::Union, &open.branches) {
            return CommitOutcome::HardFail(ParseDiag::hard_fail(
                DiagKind::Deferred,
                line_no,
                format!("branch testcase union failed: {err}"),
                None,
            ));
        }
    }

    // Aggregate union of line/function/branch from this section contribution.
    if let Err(err) = source
        .aggregate_mut()
        .lines_mut()
        .apply_op(AlgebraOp::Union, &open.lines)
    {
        return CommitOutcome::HardFail(ParseDiag::hard_fail(
            DiagKind::Deferred,
            line_no,
            format!("line aggregate union failed: {err}"),
            None,
        ));
    }
    if let Err(err) = source
        .aggregate_mut()
        .functions_mut()
        .apply_op(AlgebraOp::Union, &open.functions)
    {
        return CommitOutcome::HardFail(ParseDiag::hard_fail(
            DiagKind::Deferred,
            line_no,
            format!("function aggregate union failed: {err}"),
            None,
        ));
    }
    if let Err(err) = source
        .aggregate_mut()
        .branches_mut()
        .apply_op(AlgebraOp::Union, &open.branches)
    {
        return CommitOutcome::HardFail(ParseDiag::hard_fail(
            DiagKind::Deferred,
            line_no,
            format!("branch aggregate union failed: {err}"),
            None,
        ));
    }

    // MC/DC close uses *current* test name.
    if let Err(diag) = close_mcdc_block(source, open, current_test_name, line_no) {
        if diag.class == DiagClass::HardFail {
            return CommitOutcome::HardFail(diag);
        }
    }

    CommitOutcome::Committed
}

/// Ensure a [`SourceCoverage`] exists for `open` without committing data.
pub fn ensure_source<'a>(
    db: &'a mut CoverageDatabase,
    open: &OpenSection,
) -> &'a mut SourceCoverage {
    let key = open.identity().lookup_key().clone();
    if !db.contains_key(&key) {
        db.insert(SourceCoverage::new(open.identity().clone()));
    }
    db.get_mut(&key).expect("just ensured")
}
