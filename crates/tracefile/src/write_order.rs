//! Ordering helpers for canonical LCOV current-form emission.
//!
//! Normative sort rules come from `tracefile-grammar.md` (Canonical Writer
//! Contract) and `coverage-model.md` (branch / MC/DC writer notes).

use ferricov_model::{BranchBlock, BranchKind, LineKey};

/// Compare two line keys with Oracle writer numeric preference.
///
/// Plain unsigned-digit lexemes compare by integer value. Everything else falls
/// back to byte-wise (Perl lexical) order of the retained lexeme.
#[must_use]
pub fn cmp_line_numeric(left: &LineKey, right: &LineKey) -> core::cmp::Ordering {
    match (parse_u64_digits(left.lexeme().as_bytes()), parse_u64_digits(right.lexeme().as_bytes())) {
        (Some(a), Some(b)) => a.cmp(&b),
        (Some(_), None) => core::cmp::Ordering::Less,
        (None, Some(_)) => core::cmp::Ordering::Greater,
        (None, None) => left.lexeme().as_bytes().cmp(right.lexeme().as_bytes()),
    }
}

/// Parse an unsigned ASCII digit sequence into `u64`.
#[must_use]
pub fn parse_u64_digits(bytes: &[u8]) -> Option<u64> {
    if bytes.is_empty() || !bytes.iter().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let mut n: u64 = 0;
    for &b in bytes {
        n = n.checked_mul(10)?.checked_add(u64::from(b - b'0'))?;
    }
    Some(n)
}

/// Canonical branch-block sort key: signature length, lexical signature, model
/// position. Expressions are not part of the signature.
#[must_use]
pub fn branch_block_sort_key(block: &BranchBlock) -> (usize, Vec<u8>, usize) {
    let sig = block.signature_bytes();
    (sig.len(), sig, block.model_position())
}

/// Sort block indices for one line into canonical writer order.
#[must_use]
pub fn sorted_branch_block_indices(blocks: &[BranchBlock]) -> Vec<usize> {
    let mut indices: Vec<usize> = (0..blocks.len()).collect();
    indices.sort_by(|&a, &b| {
        branch_block_sort_key(&blocks[a]).cmp(&branch_block_sort_key(&blocks[b]))
    });
    indices
}

/// Emit the `[e|f][U]<block>` field for one BRDA edge.
#[must_use]
pub fn format_brda_block_field(kind: BranchKind, excluded: bool, block_no: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(8);
    match kind {
        BranchKind::Vanilla => {}
        BranchKind::Exception => out.push(b'e'),
        BranchKind::Fallthrough => out.push(b'f'),
    }
    if excluded {
        out.push(b'U');
    }
    out.extend_from_slice(block_no.to_string().as_bytes());
    out
}

#[cfg(test)]
mod tests {
    use super::{
        branch_block_sort_key, cmp_line_numeric, format_brda_block_field, sorted_branch_block_indices,
    };
    use ferricov_model::{BranchBlock, BranchEdge, BranchKind, BranchTaken, LineKey};

    #[test]
    fn numeric_line_sort_prefers_integer_magnitude() {
        let a = LineKey::from_lexeme("2");
        let b = LineKey::from_lexeme("10");
        assert_eq!(cmp_line_numeric(&a, &b), core::cmp::Ordering::Less);
        // Lexical byte order puts "10" before "2".
        assert_eq!(
            a.lexeme().as_bytes().cmp(b.lexeme().as_bytes()),
            core::cmp::Ordering::Greater
        );
    }

    #[test]
    fn branch_blocks_sort_by_signature_length_then_text_then_position() {
        // Mirror fixtures/branches/sort-signatures.info after parse:
        // bbb @0, bb @1, e @2, fb @3
        let mut bbb = BranchBlock::new(0);
        for _ in 0..3 {
            bbb.append_edge(BranchEdge::from_taken(BranchTaken::from_token("1")));
        }
        let mut bb = BranchBlock::new(1);
        bb.append_edge(BranchEdge::from_taken(BranchTaken::from_token("1")));
        bb.append_edge(BranchEdge::from_taken(BranchTaken::from_token("0")));
        let mut e = BranchBlock::new(2);
        e.append_edge(BranchEdge::new(
            BranchTaken::from_token("1"),
            BranchKind::Exception,
            None,
            false,
        ));
        let mut fb = BranchBlock::new(3);
        fb.append_edge(BranchEdge::new(
            BranchTaken::from_token("1"),
            BranchKind::Fallthrough,
            None,
            false,
        ));
        fb.append_edge(BranchEdge::from_taken(BranchTaken::from_token("0")));

        let blocks = vec![bbb, bb, e, fb];
        let order = sorted_branch_block_indices(&blocks);
        // e (len1), bb (len2 "bb"), fb (len2 "fb"), bbb (len3)
        assert_eq!(order, vec![2, 1, 3, 0]);
        assert!(branch_block_sort_key(&blocks[2]) < branch_block_sort_key(&blocks[1]));
    }

    #[test]
    fn brda_block_field_prefixes() {
        assert_eq!(format_brda_block_field(BranchKind::Vanilla, false, 0), b"0");
        assert_eq!(format_brda_block_field(BranchKind::Vanilla, true, 0), b"U0");
        assert_eq!(format_brda_block_field(BranchKind::Exception, false, 0), b"e0");
        assert_eq!(format_brda_block_field(BranchKind::Exception, true, 0), b"eU0");
        assert_eq!(
            format_brda_block_field(BranchKind::Fallthrough, true, 2),
            b"fU2"
        );
    }
}
