//! Canonical LCOV current-form writer (`TraceFile::write_info` projection).
//!
//! M1-CORE-007: deterministic serialization of [`CoverageDatabase`] without
//! mutating the model. Section selection follows line-testcase keys
//! (`U-TESTCASE-FILTER-WRITE`). Totals are recomputed from emitted points.

use ferricov_model::{
    BranchCoverage, BranchTaken, CoverageCount, CoverageDatabase, FunctionTable, LineCoverage,
    LineKey, McdcCoverage, SourceCoverage, TestName,
};

use crate::write_order::{
    cmp_line_numeric, format_brda_block_field, sorted_branch_block_indices,
};

/// Feature flags and optional comment stream for canonical serialization.
///
/// Matches the `SerializationContext` shape in `coverage-model.md` for the
/// subset CORE-007 owns. Path projection / checksum providers beyond stored
/// checksums remain residual.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WriteOptions {
    /// Emit function current-form records and `FNF`/`FNH`.
    pub function_coverage: bool,
    /// Emit `BRDA` records and `BRF`/`BRH` when non-excluded branches exist.
    pub branch_coverage: bool,
    /// Emit `MCDC` records and `MCF`/`MCH` when expressions exist.
    pub mcdc_coverage: bool,
    /// When true, emit stored checksums on `DA` records.
    pub checksum_output: bool,
    /// Explicit output comments (`#...`) prepended in insertion order.
    pub comments: Vec<Vec<u8>>,
}

impl Default for WriteOptions {
    fn default() -> Self {
        Self {
            function_coverage: true,
            branch_coverage: true,
            mcdc_coverage: true,
            checksum_output: false,
            comments: Vec::new(),
        }
    }
}

impl WriteOptions {
    /// Default options: all coverage families enabled, no checksums, no comments.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Append an output comment body (without the leading `#`).
    pub fn add_comment(&mut self, comment: impl AsRef<[u8]>) -> &mut Self {
        self.comments.push(comment.as_ref().to_vec());
        self
    }

    /// Replace the comment list wholesale.
    pub fn with_comments(mut self, comments: Vec<Vec<u8>>) -> Self {
        self.comments = comments;
        self
    }
}

/// Serialize `db` to canonical LCOV current-form bytes.
///
/// Alias of [`write_database`] matching Oracle `TraceFile::write_info` naming.
#[must_use]
pub fn write_info(db: &CoverageDatabase, options: &WriteOptions) -> Vec<u8> {
    write_database(db, options)
}

/// Serialize `db` to canonical LCOV current-form bytes.
///
/// Does not mutate `db`. Repeated calls with the same options are
/// byte-identical.
#[must_use]
pub fn write_database(db: &CoverageDatabase, options: &WriteOptions) -> Vec<u8> {
    let mut out = Vec::new();
    for comment in &options.comments {
        out.push(b'#');
        out.extend_from_slice(comment);
        out.push(b'\n');
    }

    // Source order: Perl lexical sort on display path bytes.
    let mut sources: Vec<&SourceCoverage> = db.iter().map(|(_, s)| s).collect();
    sources.sort_by(|a, b| {
        a.identity()
            .display_path()
            .as_bytes()
            .cmp(b.identity().display_path().as_bytes())
    });

    for source in sources {
        write_source_sections(&mut out, source, options);
    }
    out
}

fn write_source_sections(out: &mut Vec<u8>, source: &SourceCoverage, options: &WriteOptions) {
    // Section enumeration is driven by line-testcase keys only.
    let mut test_names: Vec<&TestName> = source.testcases().lines().keys().collect();
    test_names.sort(); // TestName Ord is lexical on identity bytes.

    let path = source.identity().display_path().as_bytes();
    for tn in test_names {
        let lines = source
            .testcases()
            .lines()
            .get(tn)
            .expect("key from iterator");
        // Oracle still emits sections that have an explicit empty line map only
        // when the key is present; empty maps produce LF:0 LH:0. Keep that.
        write_section(out, source, path, tn, lines, options);
    }
}

fn write_section(
    out: &mut Vec<u8>,
    source: &SourceCoverage,
    path: &[u8],
    tn: &TestName,
    lines: &LineCoverage,
    options: &WriteOptions,
) {
    // TN
    out.extend_from_slice(b"TN:");
    out.extend_from_slice(tn.as_bytes());
    out.push(b'\n');

    // SF (always SF, never KF)
    out.extend_from_slice(b"SF:");
    out.extend_from_slice(path);
    out.push(b'\n');

    // VER
    if let Some(ver) = source.version() {
        out.extend_from_slice(b"VER:");
        out.extend_from_slice(ver.as_bytes());
        out.push(b'\n');
    }

    if options.function_coverage {
        let empty_fn = FunctionTable::new();
        let functions = source
            .testcases()
            .functions()
            .get(tn)
            .unwrap_or(&empty_fn);
        write_functions(out, functions);
    }

    if options.branch_coverage {
        let empty_br = BranchCoverage::new();
        let branches = source
            .testcases()
            .branches()
            .get(tn)
            .unwrap_or(&empty_br);
        write_branches(out, branches);
    }

    if options.mcdc_coverage {
        let empty_mcdc = McdcCoverage::new();
        let mcdc = source.testcases().mcdc().get(tn).unwrap_or(&empty_mcdc);
        write_mcdc(out, mcdc);
    }

    write_lines(out, source, lines, options);

    out.extend_from_slice(b"end_of_record\n");
}

fn write_functions(out: &mut Vec<u8>, functions: &FunctionTable) {
    let mut groups: Vec<_> = functions.groups().collect();
    groups.sort_by(|(a, _), (b, _)| cmp_line_numeric(a, b));

    for (idx, (start, group)) in groups.iter().enumerate() {
        out.extend_from_slice(b"FNL:");
        out.extend_from_slice(idx.to_string().as_bytes());
        out.push(b',');
        out.extend_from_slice(start.lexeme().as_bytes());
        if let Some(end) = group.end() {
            out.push(b',');
            out.extend_from_slice(end.lexeme().as_bytes());
        }
        out.push(b'\n');

        // Aliases are already BTreeMap-ordered (lexical).
        for (alias, count) in group.aliases() {
            out.extend_from_slice(b"FNA:");
            out.extend_from_slice(idx.to_string().as_bytes());
            out.push(b',');
            out.extend_from_slice(count.lexeme().as_bytes());
            out.push(b',');
            out.extend_from_slice(alias.as_bytes());
            out.push(b'\n');
        }
    }

    // FNF/FNH always when function coverage enabled (including zeros).
    let found = functions.group_found();
    let hit = functions.group_hit();
    push_summary(out, b"FNF", found);
    push_summary(out, b"FNH", hit);
}

fn write_branches(out: &mut Vec<u8>, branches: &BranchCoverage) {
    let mut line_keys: Vec<&LineKey> = branches.lines().map(|(k, _)| k).collect();
    line_keys.sort_by(|a, b| cmp_line_numeric(a, b));

    let mut found: u64 = 0;
    let mut hit: u64 = 0;

    for line_key in line_keys {
        let line = branches.get_line(line_key).expect("key from iterator");
        let order = sorted_branch_block_indices(line.blocks());
        for (out_block_no, &src_idx) in order.iter().enumerate() {
            let block = &line.blocks()[src_idx];
            for edge in block.edges() {
                out.extend_from_slice(b"BRDA:");
                out.extend_from_slice(line_key.lexeme().as_bytes());
                out.push(b',');
                out.extend_from_slice(&format_brda_block_field(
                    edge.kind(),
                    edge.is_excluded(),
                    out_block_no,
                ));
                out.push(b',');
                if let Some(expr) = edge.expression() {
                    out.extend_from_slice(expr.as_bytes());
                }
                out.push(b',');
                match edge.taken() {
                    BranchTaken::NeverEvaluated => out.push(b'-'),
                    BranchTaken::Evaluated(count) => {
                        out.extend_from_slice(count.lexeme().as_bytes());
                    }
                }
                out.push(b'\n');

                if !edge.is_excluded() {
                    found = found.saturating_add(1);
                    if edge.taken().contributes_hit() {
                        hit = hit.saturating_add(1);
                    }
                }
            }
        }
    }

    if found > 0 {
        push_summary(out, b"BRF", found as usize);
        push_summary(out, b"BRH", hit as usize);
    }
}

fn write_mcdc(out: &mut Vec<u8>, mcdc: &McdcCoverage) {
    let mut line_keys: Vec<&LineKey> = mcdc.lines().map(|(k, _)| k).collect();
    line_keys.sort_by(|a, b| cmp_line_numeric(a, b));

    let mut found: u64 = 0;
    let mut hit: u64 = 0;
    let mut emitted = false;

    for line_key in line_keys {
        let line = mcdc.get_line(line_key).expect("key from iterator");
        // GroupSizeKey Ord is already Perl lexical on lexeme bytes.
        for (group_key, exprs) in line.iter_groups() {
            for (stored_idx, expr) in exprs.iter().enumerate() {
                // Sense order: t then f.
                for (is_true, sense) in [
                    (true, expr.true_sense()),
                    (false, expr.false_sense()),
                ] {
                    out.extend_from_slice(b"MCDC:");
                    out.extend_from_slice(line_key.lexeme().as_bytes());
                    out.push(b',');
                    if sense.is_excluded() {
                        out.push(b'U');
                    }
                    out.extend_from_slice(group_key.lexeme().as_bytes());
                    out.push(b',');
                    out.push(if is_true { b't' } else { b'f' });
                    out.push(b',');
                    out.extend_from_slice(sense.count().lexeme().as_bytes());
                    out.push(b',');
                    out.extend_from_slice(stored_idx.to_string().as_bytes());
                    out.push(b',');
                    out.extend_from_slice(expr.expression().as_bytes());
                    out.push(b'\n');
                    emitted = true;

                    // Oracle source totals: count every stored sense into MCF,
                    // and every nonzero sense into MCH, before exclusion filter
                    // (`M1-MD-009` / writer-mcdc-groups.canonical).
                    found = found.saturating_add(1);
                    if !sense.count().is_zero() {
                        hit = hit.saturating_add(1);
                    }
                }
            }
        }
    }

    if emitted {
        push_summary(out, b"MCF", found as usize);
        push_summary(out, b"MCH", hit as usize);
    }
}

fn write_lines(
    out: &mut Vec<u8>,
    source: &SourceCoverage,
    lines: &LineCoverage,
    options: &WriteOptions,
) {
    let mut entries: Vec<(&LineKey, &CoverageCount)> = lines.iter().collect();
    entries.sort_by(|(a, _), (b, _)| cmp_line_numeric(a, b));

    let mut found: usize = 0;
    let mut hit: usize = 0;
    for (key, count) in entries {
        out.extend_from_slice(b"DA:");
        out.extend_from_slice(key.lexeme().as_bytes());
        out.push(b',');
        out.extend_from_slice(count.lexeme().as_bytes());
        if options.checksum_output {
            if let Some(chk) = source.checksums().get(key) {
                out.push(b',');
                out.extend_from_slice(chk.as_bytes());
            }
        }
        out.push(b'\n');
        found = found.saturating_add(1);
        if count.is_positive() {
            hit = hit.saturating_add(1);
        }
    }
    push_summary(out, b"LF", found);
    push_summary(out, b"LH", hit);
}

fn push_summary(out: &mut Vec<u8>, tag: &[u8], value: usize) {
    out.extend_from_slice(tag);
    out.push(b':');
    out.extend_from_slice(value.to_string().as_bytes());
    out.push(b'\n');
}
