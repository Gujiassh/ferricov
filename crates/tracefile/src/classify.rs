//! Prefix-vs-full record matching for normalized logical lines.
//!
//! CORE-005 classifies lines and recognizes binding records (`TN`, `SF`/`KF`)
//! and the terminator. Other known tags are classified as stubs so CORE-006
//! can dispatch full semantics without redoing lexical work.

use ferricov_model::ByteString;

/// How a record expression is anchored after trailing-whitespace removal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchAnchor {
    /// Expression has `^` but no `$`; unconsumed suffix is observed permissiveness.
    Prefix,
    /// Expression is fully anchored (`^…$`).
    Full,
}

/// Known LCOV record tags recognized at the lexical layer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RecordTag {
    /// `TN`
    Tn,
    /// `SF`
    Sf,
    /// `KF` (observed alternate of `SF`; never emitted by the writer)
    Kf,
    /// `VER`
    Ver,
    /// `DA`
    Da,
    /// Legacy `FN`
    Fn,
    /// Legacy `FNDA`
    Fnda,
    /// Current `FNL`
    Fnl,
    /// Current `FNA`
    Fna,
    /// `BRDA`
    Brda,
    /// `MCDC`
    Mcdc,
    /// Summary `FNF`
    Fnf,
    /// Summary `FNH`
    Fnh,
    /// Summary `BRF`
    Brf,
    /// Summary `BRH`
    Brh,
    /// Summary `MCF`
    Mcf,
    /// Summary `MCH`
    Mch,
    /// Summary `LF`
    Lf,
    /// Summary `LH`
    Lh,
    /// `end_of_record`
    EndOfRecord,
}

impl RecordTag {
    /// ASCII tag bytes as they appear in a normalized line.
    #[must_use]
    pub fn as_bytes(self) -> &'static [u8] {
        match self {
            Self::Tn => b"TN",
            Self::Sf => b"SF",
            Self::Kf => b"KF",
            Self::Ver => b"VER",
            Self::Da => b"DA",
            Self::Fn => b"FN",
            Self::Fnda => b"FNDA",
            Self::Fnl => b"FNL",
            Self::Fna => b"FNA",
            Self::Brda => b"BRDA",
            Self::Mcdc => b"MCDC",
            Self::Fnf => b"FNF",
            Self::Fnh => b"FNH",
            Self::Brf => b"BRF",
            Self::Brh => b"BRH",
            Self::Mcf => b"MCF",
            Self::Mch => b"MCH",
            Self::Lf => b"LF",
            Self::Lh => b"LH",
            Self::EndOfRecord => b"end_of_record",
        }
    }

    /// Grammar anchor for this tag's reader expression.
    #[must_use]
    pub fn anchor(self) -> MatchAnchor {
        match self {
            Self::Tn
            | Self::Sf
            | Self::Kf
            | Self::Da
            | Self::Fnf
            | Self::Fnh
            | Self::Brf
            | Self::Brh
            | Self::Mcf
            | Self::Mch
            | Self::Lf
            | Self::Lh
            | Self::EndOfRecord => MatchAnchor::Prefix,
            Self::Ver | Self::Fn | Self::Fnda | Self::Fnl | Self::Fna | Self::Brda | Self::Mcdc => {
                MatchAnchor::Full
            }
        }
    }
}

/// Parsed `TN` payload after the `TN:` prefix match.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TnPayload {
    /// Base capture `([^,]*)` before optional `,diff`.
    pub base: ByteString,
    /// Exact optional `,diff` capture (includes the comma when present).
    pub diff_suffix: Option<ByteString>,
    /// Unconsumed suffix after the prefix match (observed permissiveness).
    pub unconsumed: ByteString,
}

/// Classification of one normalized logical line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LineClass {
    /// Empty after normalization (blank / whitespace-only).
    Empty,
    /// Column-zero `#` comment (`^#`); leading-space `#` is not a comment.
    Comment,
    /// Terminator: normalized line begins with `end_of_record`.
    Terminator {
        /// Bytes after the `end_of_record` prefix (may be empty).
        unconsumed: ByteString,
    },
    /// Binding / known record candidate with tag and remaining payload bytes.
    Record {
        tag: RecordTag,
        /// Bytes after the tag (and after `:` when the grammar uses a colon).
        payload: ByteString,
        /// Bytes after a successful prefix match that the Full form would reject.
        /// Always empty for Full-anchor tags that matched completely; for Prefix
        /// tags this may hold trailing junk when callers split further.
        unconsumed: ByteString,
        /// Structured `TN` fields when `tag == Tn`.
        tn: Option<TnPayload>,
    },
    /// Nonblank, noncomment line that matches no known reader alternative.
    ///
    /// Oracle raises ignorable `ERROR_FORMAT` for these (`tracefile.lexical.unknown`).
    Unclassified {
        /// Full normalized line bytes.
        line: ByteString,
    },
}

/// Classify a normalized logical line (already chomped + trailing-`\s` stripped).
///
/// Matching order mirrors `_read_info`:
/// 1. empty → ignore
/// 2. `^#` → comment
/// 3. `^[SK]F:(.*)` before other records
/// 4. remaining known tags / terminator / unknown
#[must_use]
pub fn classify_line(normalized: &[u8]) -> LineClass {
    if normalized.is_empty() {
        return LineClass::Empty;
    }

    if normalized[0] == b'#' {
        return LineClass::Comment;
    }

    // SF / KF share `^[SK]F:(.*)` and are tested before other alternatives.
    if let Some(class) = match_sf_or_kf(normalized) {
        return class;
    }

    if let Some(class) = match_tn(normalized) {
        return class;
    }

    if let Some(class) = match_end_of_record(normalized) {
        return class;
    }

    // Remaining known tags (stubs for CORE-006). Order follows grammar tables;
    // longer tags that share prefixes are checked before shorter ones.
    if let Some(class) = match_known_stub(normalized) {
        return class;
    }

    LineClass::Unclassified {
        line: ByteString::from_slice(normalized),
    }
}

fn match_sf_or_kf(line: &[u8]) -> Option<LineClass> {
    let tag = if line.starts_with(b"SF:") {
        RecordTag::Sf
    } else if line.starts_with(b"KF:") {
        RecordTag::Kf
    } else {
        return None;
    };
    let payload = &line[3..];
    Some(LineClass::Record {
        tag,
        payload: ByteString::from_slice(payload),
        unconsumed: ByteString::new(Vec::new()),
        tn: None,
    })
}

fn match_tn(line: &[u8]) -> Option<LineClass> {
    // `^TN:([^,]*)(,diff)?`
    if !line.starts_with(b"TN:") {
        return None;
    }
    let after_colon = &line[3..];
    let comma = after_colon.iter().position(|&b| b == b',');
    let (base, rest) = match comma {
        Some(i) => (&after_colon[..i], &after_colon[i..]),
        None => (after_colon, &[][..]),
    };
    let (diff_suffix, unconsumed) = if rest.starts_with(b",diff") {
        (Some(ByteString::from_slice(b",diff")), &rest[5..])
    } else {
        (None, rest)
    };
    let tn = TnPayload {
        base: ByteString::from_slice(base),
        diff_suffix,
        unconsumed: ByteString::from_slice(unconsumed),
    };
    Some(LineClass::Record {
        tag: RecordTag::Tn,
        payload: ByteString::from_slice(after_colon),
        unconsumed: ByteString::from_slice(unconsumed),
        tn: Some(tn),
    })
}

fn match_end_of_record(line: &[u8]) -> Option<LineClass> {
    // `^end_of_record` (prefix)
    const TAG: &[u8] = b"end_of_record";
    if !line.starts_with(TAG) {
        return None;
    }
    Some(LineClass::Terminator {
        unconsumed: ByteString::from_slice(&line[TAG.len()..]),
    })
}

fn match_known_stub(line: &[u8]) -> Option<LineClass> {
    // Full-anchored tags that require `TAG:` plus a payload shape are only
    // stub-classified when the tag prefix matches; CORE-006 validates Fully.
    // Summary tags use `^(FN|BR|L|MC)[HF]` with no colon requirement.
    //
    // Check longer / more specific prefixes first to avoid `FN` swallowing
    // `FNL`/`FNA`/`FNDA`/`FNF`/`FNH`.

    // Current function + legacy function + summaries that start with FN…
    if let Some(c) = stub_full(line, b"FNDA:", RecordTag::Fnda) {
        return Some(c);
    }
    if let Some(c) = stub_full(line, b"FNL:", RecordTag::Fnl) {
        return Some(c);
    }
    if let Some(c) = stub_full(line, b"FNA:", RecordTag::Fna) {
        return Some(c);
    }
    if line.starts_with(b"FNF") {
        return Some(summary_stub(RecordTag::Fnf, line));
    }
    if line.starts_with(b"FNH") {
        return Some(summary_stub(RecordTag::Fnh, line));
    }
    if let Some(c) = stub_full(line, b"FN:", RecordTag::Fn) {
        return Some(c);
    }

    if let Some(c) = stub_full(line, b"BRDA:", RecordTag::Brda) {
        return Some(c);
    }
    if line.starts_with(b"BRF") {
        return Some(summary_stub(RecordTag::Brf, line));
    }
    if line.starts_with(b"BRH") {
        return Some(summary_stub(RecordTag::Brh, line));
    }

    if let Some(c) = stub_full(line, b"MCDC:", RecordTag::Mcdc) {
        return Some(c);
    }
    if line.starts_with(b"MCF") {
        return Some(summary_stub(RecordTag::Mcf, line));
    }
    if line.starts_with(b"MCH") {
        return Some(summary_stub(RecordTag::Mch, line));
    }

    if line.starts_with(b"LF") {
        // Avoid classifying `LF` only when it is exactly the summary prefix;
        // `^(FN|BR|L|MC)[HF]` means `LF` or `LH` at start.
        return Some(summary_stub(RecordTag::Lf, line));
    }
    if line.starts_with(b"LH") {
        return Some(summary_stub(RecordTag::Lh, line));
    }

    if let Some(c) = stub_full(line, b"VER:", RecordTag::Ver) {
        return Some(c);
    }
    if let Some(c) = stub_full(line, b"DA:", RecordTag::Da) {
        return Some(c);
    }

    None
}

fn stub_full(line: &[u8], prefix: &[u8], tag: RecordTag) -> Option<LineClass> {
    // CORE-005 only checks the tag prefix. Full-anchor payload validation and
    // Prefix unconsumed splitting for DA/summaries are CORE-006.
    if !line.starts_with(prefix) {
        return None;
    }
    Some(LineClass::Record {
        tag,
        payload: ByteString::from_slice(&line[prefix.len()..]),
        unconsumed: ByteString::new(Vec::new()),
        tn: None,
    })
}

fn summary_stub(tag: RecordTag, line: &[u8]) -> LineClass {
    let tag_len = tag.as_bytes().len();
    LineClass::Record {
        tag,
        payload: ByteString::from_slice(&line[tag_len..]),
        unconsumed: ByteString::new(Vec::new()),
        tn: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn comment_requires_column_zero_hash() {
        assert!(matches!(classify_line(b"#comment"), LineClass::Comment));
        assert!(matches!(
            classify_line(b" #not-comment"),
            LineClass::Unclassified { .. }
        ));
    }

    #[test]
    fn empty_and_terminator() {
        assert!(matches!(classify_line(b""), LineClass::Empty));
        match classify_line(b"end_of_record") {
            LineClass::Terminator { unconsumed } => assert!(unconsumed.as_bytes().is_empty()),
            other => panic!("unexpected {other:?}"),
        }
        match classify_line(b"end_of_recordEXTRA") {
            LineClass::Terminator { unconsumed } => {
                assert_eq!(unconsumed.as_bytes(), b"EXTRA");
            }
            other => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn tn_empty_name_and_diff() {
        match classify_line(b"TN:") {
            LineClass::Record {
                tag: RecordTag::Tn,
                tn: Some(tn),
                ..
            } => {
                assert!(tn.base.as_bytes().is_empty());
                assert!(tn.diff_suffix.is_none());
            }
            other => panic!("unexpected {other:?}"),
        }
        match classify_line(b"TN:name,diff") {
            LineClass::Record {
                tag: RecordTag::Tn,
                tn: Some(tn),
                ..
            } => {
                assert_eq!(tn.base.as_bytes(), b"name");
                assert_eq!(
                    tn.diff_suffix.as_ref().map(ByteString::as_bytes),
                    Some(b",diff".as_slice())
                );
                assert!(tn.unconsumed.as_bytes().is_empty());
            }
            other => panic!("unexpected {other:?}"),
        }
        match classify_line(b"TN:foo,bar") {
            LineClass::Record { tn: Some(tn), .. } => {
                assert_eq!(tn.base.as_bytes(), b"foo");
                assert!(tn.diff_suffix.is_none());
                assert_eq!(tn.unconsumed.as_bytes(), b",bar");
            }
            other => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn sf_and_kf_prefix() {
        match classify_line(b"SF:/path/\xff") {
            LineClass::Record {
                tag: RecordTag::Sf,
                payload,
                ..
            } => assert_eq!(payload.as_bytes(), b"/path/\xff"),
            other => panic!("unexpected {other:?}"),
        }
        match classify_line(b"KF:alt") {
            LineClass::Record {
                tag: RecordTag::Kf,
                payload,
                ..
            } => assert_eq!(payload.as_bytes(), b"alt"),
            other => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn known_stubs_and_unknown() {
        assert!(matches!(
            classify_line(b"DA:1,1"),
            LineClass::Record {
                tag: RecordTag::Da,
                ..
            }
        ));
        assert!(matches!(
            classify_line(b"FNL:0,1,1"),
            LineClass::Record {
                tag: RecordTag::Fnl,
                ..
            }
        ));
        assert!(matches!(
            classify_line(b"FNF:1"),
            LineClass::Record {
                tag: RecordTag::Fnf,
                ..
            }
        ));
        assert!(matches!(
            classify_line(b"TD:nope"),
            LineClass::Unclassified { .. }
        ));
    }
}
