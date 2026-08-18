//! Byte-oriented field splitters shared by record apply.

use crate::line::is_perl_ascii_ws;
use ferricov_model::{BranchKind, ByteString};

pub(crate) fn split_once(bytes: &[u8], sep: u8) -> Option<(&[u8], &[u8])> {
    let i = bytes.iter().position(|&b| b == sep)?;
    Some((&bytes[..i], &bytes[i + 1..]))
}

pub(crate) fn split_at_last_comma(bytes: &[u8]) -> (&[u8], &[u8]) {
    match bytes.iter().rposition(|&b| b == b',') {
        Some(i) => (&bytes[..i], &bytes[i + 1..]),
        None => (bytes, &[][..]),
    }
}

pub(crate) fn split_commas(bytes: &[u8]) -> Vec<&[u8]> {
    let mut out = Vec::new();
    let mut start = 0usize;
    for (i, &b) in bytes.iter().enumerate() {
        if b == b',' {
            out.push(&bytes[start..i]);
            start = i + 1;
        }
    }
    out.push(&bytes[start..]);
    out
}

pub(crate) fn is_digits(bytes: &[u8]) -> bool {
    !bytes.is_empty() && bytes.iter().all(|b| b.is_ascii_digit())
}

pub(crate) fn parse_u64_digits(bytes: &[u8]) -> Option<u64> {
    if !is_digits(bytes) {
        return None;
    }
    let mut n: u64 = 0;
    for &b in bytes {
        n = n.checked_mul(10)?.checked_add(u64::from(b - b'0'))?;
    }
    Some(n)
}

pub(crate) fn line_numerically_non_positive(digits: &[u8]) -> bool {
    // Perl \d+ that is numerically <= 0 → only all-zeros.
    is_digits(digits) && digits.iter().all(|&b| b == b'0')
}

pub(crate) fn split_da_count_checksum(rest: &[u8]) -> (Vec<u8>, Option<ByteString>) {
    if let Some(comma) = rest.iter().position(|&b| b == b',') {
        let count = rest[..comma].to_vec();
        let after = &rest[comma + 1..];
        let end = after
            .iter()
            .position(|&b| b == b',' || is_perl_ascii_ws(b))
            .unwrap_or(after.len());
        if end == 0 {
            (count, None)
        } else {
            (count, Some(ByteString::from_slice(&after[..end])))
        }
    } else {
        (rest.to_vec(), None)
    }
}

pub(crate) fn parse_brda_field2(field2: &[u8]) -> Option<(BranchKind, bool, &[u8])> {
    let mut i = 0usize;
    let kind = if field2.first() == Some(&b'e') {
        i = 1;
        BranchKind::Exception
    } else if field2.first() == Some(&b'f') {
        i = 1;
        BranchKind::Fallthrough
    } else {
        BranchKind::Vanilla
    };
    let excluded = if field2.get(i) == Some(&b'U') {
        i += 1;
        true
    } else {
        false
    };
    let block = &field2[i..];
    if !is_digits(block) {
        return None;
    }
    Some((kind, excluded, block))
}
