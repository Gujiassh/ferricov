//! Parser binding state for test name and source sections.
//!
//! # Late-TN rule (CORE-005)
//!
//! Changing `TN` updates the name used by the **next** `SF`/`KF`. It does
//! **not** rebind line, function, or branch maps already selected for the
//! current open source. MC/DC close paths are exceptional (they look up the
//! current test name at close time); that ownership quirk is applied in
//! CORE-006, not here. This module only tracks the binding fields CORE-005
//! owns so CORE-006 can dispatch records onto them.

use crate::classify::{LineClass, RecordTag, TnPayload};
use crate::diag::ParseDiag;
use crate::line::is_perl_ascii_ws;
use ferricov_model::{ByteString, SourceIdentity, TestName};

/// Which source tag opened the current section.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceTag {
    /// `SF:`
    Sf,
    /// `KF:` (same bind semantics; never emitted by the writer)
    Kf,
}

/// Snapshot of the active source binding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBinding {
    /// Tag that opened this section.
    pub tag: SourceTag,
    /// Source identity constructed from the raw path payload bytes.
    pub identity: SourceIdentity,
    /// Raw path payload bytes as captured after `SF:` / `KF:` (before resolve).
    pub raw_path: ByteString,
    /// Test name that was current when this source was bound.
    pub bound_test_name: TestName,
}

/// Mutable parser binding state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParserState {
    /// Current test name (initial empty string).
    test_name: TestName,
    /// Optional unsanitized TN base retained as diagnostic provenance.
    last_tn_unsanitized: Option<ByteString>,
    /// Active source section, if any.
    source: Option<SourceBinding>,
    /// True after a successful `SF`/`KF` bind until a skip or (CORE-006) clear.
    source_open: bool,
    /// True when the current source was marked skipped (empty path / exclude).
    source_skipped: bool,
    /// 1-based logical line counter for diagnostics.
    line_no: u64,
    /// Accumulated diagnostics for the current parse.
    diags: Vec<ParseDiag>,
    /// Remembers whether any TN sanitization occurred (Oracle warns once at EOF).
    tn_sanitized_once: bool,
}

impl Default for ParserState {
    fn default() -> Self {
        Self::new()
    }
}

impl ParserState {
    /// Create initial state: empty test name, no source open.
    #[must_use]
    pub fn new() -> Self {
        Self {
            test_name: TestName::empty(),
            last_tn_unsanitized: None,
            source: None,
            source_open: false,
            source_skipped: false,
            line_no: 0,
            diags: Vec::new(),
            tn_sanitized_once: false,
        }
    }

    /// Borrow the current test name.
    #[must_use]
    pub fn test_name(&self) -> &TestName {
        &self.test_name
    }

    /// Borrow the active source binding, if any.
    #[must_use]
    pub fn source(&self) -> Option<&SourceBinding> {
        self.source.as_ref()
    }

    /// Return `true` when a source section is open and not skipped.
    #[must_use]
    pub fn source_open(&self) -> bool {
        self.source_open && !self.source_skipped
    }

    /// Return `true` when the current source was marked skipped.
    #[must_use]
    pub fn source_skipped(&self) -> bool {
        self.source_skipped
    }

    /// Current 1-based logical line number (0 before any line is processed).
    #[must_use]
    pub fn line_no(&self) -> u64 {
        self.line_no
    }

    /// Borrow accumulated diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[ParseDiag] {
        &self.diags
    }

    /// Take accumulated diagnostics, leaving the buffer empty.
    pub fn take_diagnostics(&mut self) -> Vec<ParseDiag> {
        std::mem::take(&mut self.diags)
    }

    /// Push an externally produced diagnostic (CORE-006 record apply).
    pub fn push_diag(&mut self, diag: ParseDiag) {
        self.diags.push(diag);
    }

    /// Advance the line counter and apply a classified line to binding state.
    ///
    /// Returns the [`ParseEvent`] describing what happened. Known non-binding
    /// tags emit [`ParseEvent::RecordStub`] without mutating coverage stores
    /// (CORE-006).
    pub fn apply_classified(&mut self, class: LineClass) -> ParseEvent {
        self.line_no = self.line_no.saturating_add(1);
        match class {
            LineClass::Empty => ParseEvent::IgnoredEmpty,
            LineClass::Comment => ParseEvent::IgnoredComment,
            LineClass::Terminator { unconsumed } => {
                // Terminator detection only in CORE-005; section commit is CORE-006.
                ParseEvent::Terminator { unconsumed }
            }
            LineClass::Record {
                tag: RecordTag::Tn,
                tn: Some(tn),
                ..
            } => self.apply_tn(tn),
            LineClass::Record {
                tag: RecordTag::Sf,
                payload,
                ..
            } => self.apply_source(SourceTag::Sf, payload),
            LineClass::Record {
                tag: RecordTag::Kf,
                payload,
                ..
            } => self.apply_source(SourceTag::Kf, payload),
            LineClass::Record {
                tag,
                payload,
                unconsumed,
                ..
            } => ParseEvent::RecordStub {
                tag,
                payload,
                unconsumed,
            },
            LineClass::Unclassified { line } => {
                self.diags.push(ParseDiag::error_format(
                    self.line_no,
                    format!("unexpected .info file record '{}'", line.to_string_lossy()),
                    Some(line.clone()),
                ));
                ParseEvent::Malformed {
                    kind: crate::diag::DiagKind::ErrorFormat,
                    line,
                }
            }
        }
    }

    fn apply_tn(&mut self, tn: TnPayload) -> ParseEvent {
        let original_base = tn.base.clone();
        let (sanitized_base, changed) = sanitize_tn_base(tn.base.as_bytes());
        if changed {
            self.tn_sanitized_once = true;
            self.last_tn_unsanitized = Some(original_base.clone());
            self.diags.push(ParseDiag::test_name_sanitized(
                self.line_no,
                original_base.clone(),
                ByteString::from_slice(&sanitized_base),
            ));
        }

        let mut identity = sanitized_base;
        if let Some(diff) = &tn.diff_suffix {
            identity.extend_from_slice(diff.as_bytes());
        }

        let mut name = TestName::new(ByteString::new(identity));
        if changed {
            name = name.with_unsanitized(original_base);
        }
        self.test_name = name;

        // Late-TN: do not touch `self.source` / bound maps. Documented above.
        ParseEvent::TestNameChanged {
            test_name: self.test_name.clone(),
            unconsumed: tn.unconsumed,
        }
    }

    fn apply_source(&mut self, tag: SourceTag, payload: ByteString) -> ParseEvent {
        // Empty or whitespace-only payload → ERROR_FORMAT, skip current file.
        if is_empty_or_ws_only(payload.as_bytes()) {
            self.source_skipped = true;
            self.source_open = false;
            self.diags
                .push(ParseDiag::empty_source_path(self.line_no, payload.clone()));
            return ParseEvent::SourceSkippedEmpty { tag, payload };
        }

        let identity = SourceIdentity::from_display_path(payload.clone());
        let binding = SourceBinding {
            tag,
            identity,
            raw_path: payload,
            bound_test_name: self.test_name.clone(),
        };
        self.source = Some(binding.clone());
        self.source_open = true;
        self.source_skipped = false;
        ParseEvent::SourceBound(binding)
    }
}

/// Events emitted by the streaming parser for each logical line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseEvent {
    /// Blank / whitespace-only line ignored.
    IgnoredEmpty,
    /// Column-zero comment ignored.
    IgnoredComment,
    /// `TN` updated the current test name (does not rebind open maps).
    TestNameChanged {
        test_name: TestName,
        unconsumed: ByteString,
    },
    /// `SF`/`KF` bound a source path under the current test name.
    SourceBound(SourceBinding),
    /// Empty/whitespace `SF`/`KF` payload; section marked skipped.
    SourceSkippedEmpty { tag: SourceTag, payload: ByteString },
    /// `end_of_record` detected (section commit applied by StreamingParser).
    Terminator { unconsumed: ByteString },
    /// Known tag classified but not yet semantically applied.
    ///
    /// Emitted by [`ParserState::apply_classified`] for non-binding tags.
    /// [`crate::parser::StreamingParser`] replaces this with
    /// [`ParseEvent::RecordApplied`] after CORE-006 dispatch.
    RecordStub {
        tag: RecordTag,
        payload: ByteString,
        unconsumed: ByteString,
    },
    /// Known tag whose payload was applied (or intentionally ignored).
    RecordApplied {
        tag: RecordTag,
        payload: ByteString,
        unconsumed: ByteString,
    },
    /// Unclassified / malformed line reported as ignorable format error.
    Malformed {
        kind: crate::diag::DiagKind,
        line: ByteString,
    },
}

/// Sanitize a TN base capture: replace Perl `\W` bytes with `_`.
///
/// On the pinned Linux Perl without Unicode semantics for this substitution,
/// `\W` is the complement of ASCII `[0-9A-Za-z_]`. Returns `(sanitized, changed)`.
#[must_use]
pub fn sanitize_tn_base(base: &[u8]) -> (Vec<u8>, bool) {
    let mut out = Vec::with_capacity(base.len());
    let mut changed = false;
    for &b in base {
        if is_perl_word_byte(b) {
            out.push(b);
        } else {
            out.push(b'_');
            changed = true;
        }
    }
    (out, changed)
}

/// Perl ASCII `\w` byte: `[0-9A-Za-z_]`.
#[must_use]
pub fn is_perl_word_byte(byte: u8) -> bool {
    matches!(byte, b'0'..=b'9' | b'A'..=b'Z' | b'a'..=b'z' | b'_')
}

fn is_empty_or_ws_only(bytes: &[u8]) -> bool {
    // After line-level trailing-\s strip, a whitespace-only SF/KF payload is
    // empty. Still treat any all-`\s` payload as empty for direct API use.
    bytes.iter().all(|&b| is_perl_ascii_ws(b))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::classify::classify_line;

    #[test]
    fn tn_empty_and_diff_bind() {
        let mut state = ParserState::new();
        assert!(state.test_name().is_empty());

        let ev = state.apply_classified(classify_line(b"TN:"));
        assert!(matches!(ev, ParseEvent::TestNameChanged { .. }));
        assert!(state.test_name().is_empty());

        let ev = state.apply_classified(classify_line(b"TN:name,diff"));
        match ev {
            ParseEvent::TestNameChanged { test_name, .. } => {
                assert_eq!(test_name.as_bytes(), b"name,diff");
            }
            other => panic!("unexpected {other:?}"),
        }
        assert_eq!(state.test_name().as_bytes(), b"name,diff");
    }

    #[test]
    fn tn_sanitizes_non_word_and_keeps_diff() {
        let mut state = ParserState::new();
        state.apply_classified(classify_line(b"TN:a-b,diff"));
        assert_eq!(state.test_name().as_bytes(), b"a_b,diff");
        assert!(
            state
                .diagnostics()
                .iter()
                .any(|d| { matches!(d.kind, crate::diag::DiagKind::TestNameSanitized) })
        );
    }

    #[test]
    fn sf_binds_source_under_current_tn() {
        let mut state = ParserState::new();
        state.apply_classified(classify_line(b"TN:suite"));
        let ev = state.apply_classified(classify_line(b"SF:/src/\xff.c"));
        match ev {
            ParseEvent::SourceBound(b) => {
                assert_eq!(b.tag, SourceTag::Sf);
                assert_eq!(b.raw_path.as_bytes(), b"/src/\xff.c");
                assert_eq!(b.identity.display_path().as_bytes(), b"/src/\xff.c");
                assert_eq!(b.bound_test_name.as_bytes(), b"suite");
            }
            other => panic!("unexpected {other:?}"),
        }
        assert!(state.source_open());
    }

    #[test]
    fn late_tn_does_not_clear_source_binding() {
        let mut state = ParserState::new();
        state.apply_classified(classify_line(b"TN:A"));
        state.apply_classified(classify_line(b"SF:/m0/late-tn.c"));
        let bound = state.source().unwrap().bound_test_name.clone();
        assert_eq!(bound.as_bytes(), b"A");

        state.apply_classified(classify_line(b"TN:B"));
        assert_eq!(state.test_name().as_bytes(), b"B");
        // Source binding and bound_test_name from SF remain A.
        let src = state.source().unwrap();
        assert_eq!(src.bound_test_name.as_bytes(), b"A");
        assert_eq!(src.raw_path.as_bytes(), b"/m0/late-tn.c");
        assert!(state.source_open());
    }

    #[test]
    fn empty_sf_marks_skipped() {
        let mut state = ParserState::new();
        let ev = state.apply_classified(classify_line(b"SF:"));
        assert!(matches!(ev, ParseEvent::SourceSkippedEmpty { .. }));
        assert!(state.source_skipped());
        assert!(!state.source_open());
    }

    #[test]
    fn kf_binds_like_sf() {
        let mut state = ParserState::new();
        let ev = state.apply_classified(classify_line(b"KF:alt.c"));
        match ev {
            ParseEvent::SourceBound(b) => {
                assert_eq!(b.tag, SourceTag::Kf);
                assert_eq!(b.raw_path.as_bytes(), b"alt.c");
            }
            other => panic!("unexpected {other:?}"),
        }
    }
}
