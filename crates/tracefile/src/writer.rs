//! Deterministic canonical LCOV serialization.

use std::cmp::Ordering;

use ferricov_model::{
    BranchKind, BranchTaken, ByteString, CoverageCount, CoverageDatabase, FunctionTable,
    McdcCoverage,
};

/// Explicit, side-effect-free canonical serialization configuration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SerializationContext {
    pub function_coverage_enabled: bool,
    pub branch_coverage_enabled: bool,
    pub mcdc_coverage_enabled: bool,
    pub checksum_output_enabled: bool,
    pub output_comments: Vec<ByteString>,
}

impl Default for SerializationContext {
    fn default() -> Self {
        Self {
            function_coverage_enabled: true,
            branch_coverage_enabled: true,
            mcdc_coverage_enabled: true,
            checksum_output_enabled: true,
            output_comments: Vec::new(),
        }
    }
}

/// Serialize `database` without mutating it.
#[must_use]
pub fn write_canonical(database: &CoverageDatabase, context: &SerializationContext) -> Vec<u8> {
    let mut out = Vec::new();
    for comment in &context.output_comments {
        push(&mut out, b"#");
        push(&mut out, comment.as_bytes());
        push(&mut out, b"\n");
    }
    for (_, source) in database.iter() {
        // The Oracle selects sections exclusively from line-testcase membership.
        for (test, lines) in source.testcases().lines() {
            push_record(&mut out, b"TN:", test.as_bytes());
            push_record(
                &mut out,
                b"SF:",
                source.identity().display_path().as_bytes(),
            );
            if let Some(version) = source.version() {
                push_record(&mut out, b"VER:", version.as_bytes());
            }
            if context.function_coverage_enabled {
                if let Some(functions) = source.testcases().functions().get(test) {
                    write_functions(&mut out, functions);
                }
            }
            if context.branch_coverage_enabled {
                if let Some(branches) = source.testcases().branches().get(test) {
                    let mut found = 0usize;
                    let mut hit = 0usize;
                    let mut branch_lines: Vec<_> = branches.lines().collect();
                    branch_lines.sort_by(|(left, _), (right, _)| numeric_bytes_cmp(left.lexeme().as_bytes(), right.lexeme().as_bytes()));
                    for (line, branch_line) in branch_lines {
                        let mut blocks: Vec<_> = branch_line.blocks().iter().enumerate().collect();
                        blocks.sort_by(|(ai, a), (bi, b)| {
                            let sa = a.signature_bytes();
                            let sb = b.signature_bytes();
                            sa.len().cmp(&sb.len()).then(sa.cmp(&sb)).then(ai.cmp(bi))
                        });
                        for (output_block, (_, block)) in blocks.into_iter().enumerate() {
                            for (edge_index, edge) in block.edges().iter().enumerate() {
                                let mut block_token = Vec::new();
                                if edge.kind() == BranchKind::Exception {
                                    block_token.push(b'e');
                                } else if edge.kind() == BranchKind::Fallthrough {
                                    block_token.push(b'f');
                                }
                                if edge.is_excluded() {
                                    block_token.push(b'U');
                                }
                                block_token.extend_from_slice(output_block.to_string().as_bytes());
                                let taken = match edge.taken() {
                                    BranchTaken::NeverEvaluated => b"-".to_vec(),
                                    BranchTaken::Evaluated(count) => count_bytes(count),
                                };
                                push(&mut out, b"BRDA:");
                                push(&mut out, line.lexeme().as_bytes());
                                push(&mut out, b",");
                                push(&mut out, &block_token);
                                push(&mut out, b",");
                                if let Some(expression) = edge.expression() {
                                    push(&mut out, expression.as_bytes());
                                } else {
                                    push(&mut out, edge_index.to_string().as_bytes());
                                }
                                push(&mut out, b",");
                                push(&mut out, &taken);
                                push(&mut out, b"\n");
                                if !edge.is_excluded() {
                                    found += 1;
                                    if edge.taken().contributes_hit() {
                                        hit += 1;
                                    }
                                }
                            }
                        }
                    }
                    if found > 0 {
                        summary(&mut out, b"BRF:", found);
                        summary(&mut out, b"BRH:", hit);
                    }
                }
            }
            if context.mcdc_coverage_enabled {
                if let Some(mcdc) = source.testcases().mcdc().get(test) {
                    write_mcdc(&mut out, mcdc);
                }
            }
            let mut hit = 0usize;
            let mut ordered_lines: Vec<_> = lines.iter().collect();
            ordered_lines.sort_by(|(left, _), (right, _)| numeric_bytes_cmp(left.lexeme().as_bytes(), right.lexeme().as_bytes()));
            for (line, count) in ordered_lines {
                push(&mut out, b"DA:");
                push(&mut out, line.lexeme().as_bytes());
                push(&mut out, b",");
                push(&mut out, &count_bytes(count));
                if context.checksum_output_enabled {
                    if let Some(checksum) = source.checksums().get(line) {
                        push(&mut out, b",");
                        push(&mut out, checksum.as_bytes());
                    }
                }
                push(&mut out, b"\n");
                if count.is_positive() {
                    hit += 1;
                }
            }
            summary(&mut out, b"LF:", lines.len());
            summary(&mut out, b"LH:", hit);
            push(&mut out, b"end_of_record\n");
        }
    }
    out
}

fn write_functions(out: &mut Vec<u8>, functions: &FunctionTable) {
    let mut groups: Vec<_> = functions.groups().collect();
    groups.sort_by(|(left, _), (right, _)| numeric_bytes_cmp(left.lexeme().as_bytes(), right.lexeme().as_bytes()));
    for (index, (_, group)) in groups.into_iter().enumerate() {
        push(out, b"FNL:");
        push(out, index.to_string().as_bytes());
        push(out, b",");
        push(out, group.start().lexeme().as_bytes());
        if let Some(end) = group.end() {
            push(out, b",");
            push(out, end.lexeme().as_bytes());
        }
        push(out, b"\n");
        for (alias, count) in group.aliases() {
            push(out, b"FNA:");
            push(out, index.to_string().as_bytes());
            push(out, b",");
            push(out, &count_bytes(count));
            push(out, b",");
            push(out, alias.as_bytes());
            push(out, b"\n");
        }
    }
    summary(out, b"FNF:", functions.group_found());
    summary(out, b"FNH:", functions.group_hit());
}

fn write_mcdc(out: &mut Vec<u8>, mcdc: &McdcCoverage) {
    let mut found = 0usize;
    let mut hit = 0usize;
    let mut lines: Vec<_> = mcdc.lines().collect();
    lines.sort_by(|(left, _), (right, _)| numeric_bytes_cmp(left.lexeme().as_bytes(), right.lexeme().as_bytes()));
    for (line, data) in lines {
        for (size, expressions) in data.iter_groups() {
            for (index, expression) in expressions.iter().enumerate() {
                for (sense, coverage) in [
                    (b't', expression.true_sense()),
                    (b'f', expression.false_sense()),
                ] {
                    let count = coverage.count();
                    push(out, b"MCDC:");
                    push(out, line.lexeme().as_bytes());
                    push(out, b",");
                    if coverage.is_excluded() {
                        push(out, b"U");
                    }
                    push(out, size.lexeme().as_bytes());
                    push(out, b",");
                    out.push(sense);
                    push(out, b",");
                    push(out, &count_bytes(count));
                    push(out, b",");
                    push(out, index.to_string().as_bytes());
                    push(out, b",");
                    push(out, expression.expression().as_bytes());
                    push(out, b"\n");
                    found += 1;
                    if count.is_positive() {
                        hit += 1;
                    }
                }
            }
        }
    }
    if found > 0 {
        summary(out, b"MCF:", found);
        summary(out, b"MCH:", hit);
    }
}

fn count_bytes(count: &CoverageCount) -> Vec<u8> {
    if count.is_coerced_zero() {
        b"0".to_vec()
    } else {
        count.lexeme().as_bytes().to_vec()
    }
}
fn summary(out: &mut Vec<u8>, tag: &[u8], value: usize) {
    push(out, tag);
    push(out, value.to_string().as_bytes());
    push(out, b"\n");
}
fn push_record(out: &mut Vec<u8>, tag: &[u8], value: &[u8]) {
    push(out, tag);
    push(out, value);
    push(out, b"\n");
}
fn push(out: &mut Vec<u8>, bytes: &[u8]) {
    out.extend_from_slice(bytes);
}
\n#[derive(Debug)]\nstruct DecimalOrder { negative: bool, digits: Vec<u8>, integer_digits: i64 }\n\nfn numeric_bytes_cmp(left: &[u8], right: &[u8]) -> Ordering {\n    match (decimal_order(left), decimal_order(right)) {\n        (Some(l), Some(r)) => compare_decimal_order(&l, &r),\n        _ => left.cmp(right),\n    }\n}\n\nfn decimal_order(raw: &[u8]) -> Option<DecimalOrder> {\n    let text = std::str::from_utf8(raw).ok()?.trim();\n    let (negative, unsigned) = if let Some(rest) = text.strip_prefix('-') { (true, rest) }\n        else if let Some(rest) = text.strip_prefix('+') { (false, rest) } else { (false, text) };\n    let (mantissa, exponent) = if let Some(index) = unsigned.find(['e', 'E']) {\n        (&unsigned[..index], unsigned[index + 1..].parse::<i64>().ok()?)\n    } else { (unsigned, 0) };\n    let (whole, fraction) = mantissa.split_once('.').unwrap_or((mantissa, ""));\n    if whole.is_empty() && fraction.is_empty() || !whole.bytes().chain(fraction.bytes()).all(|b| b.is_ascii_digit()) { return None; }\n    let mut digits: Vec<u8> = whole.bytes().chain(fraction.bytes()).collect();\n    let leading = digits.iter().position(|b| *b != b'0').unwrap_or(digits.len());\n    digits.drain(..leading);\n    if digits.is_empty() { return Some(DecimalOrder { negative: false, digits: vec![b'0'], integer_digits: 1 }); }\n    Some(DecimalOrder { negative, digits, integer_digits: i64::try_from(whole.len()).ok()? + exponent - i64::try_from(leading).ok()? })\n}\n\nfn compare_decimal_order(left: &DecimalOrder, right: &DecimalOrder) -> Ordering {\n    if left.negative != right.negative { return if left.negative { Ordering::Less } else { Ordering::Greater }; }\n    let magnitude = left.integer_digits.cmp(&right.integer_digits).then_with(|| {\n        let length = left.digits.len().max(right.digits.len());\n        (0..length).map(|i| *left.digits.get(i).unwrap_or(&b'0')).cmp((0..length).map(|i| *right.digits.get(i).unwrap_or(&b'0')))\n    });\n    if left.negative { magnitude.reverse() } else { magnitude }\n}\n