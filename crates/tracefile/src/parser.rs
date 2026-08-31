//! Streaming logical-line parser API.
//!
//! Feed arbitrary bytes (or pre-split lines). The parser splits, normalizes,
//! classifies, updates binding state, and applies record semantics into a
//! [`CoverageDatabase`](ferricov_model::CoverageDatabase).

use ferricov_model::CoverageDatabase;

use crate::classify::{classify_line, LineClass};
use crate::line::{normalize_logical_line, LineSplitter, LineSplitterSnapshot, RawLogicalLine};
use crate::policy::IgnorePolicy;
use crate::records::{apply_event, ApplyContext, ApplyResult};
use crate::state::{ParseEvent, ParserState};

/// Streaming LCOV logical-line parser (CORE-005 binding + CORE-006 apply).
#[derive(Debug, Clone)]
pub struct StreamingParser {
    splitter: LineSplitter,
    state: ParserState,
    apply: ApplyContext,
}

impl Default for StreamingParser {
    fn default() -> Self {
        Self::new()
    }
}

impl StreamingParser {
    #[must_use]
    pub fn splitter_snapshot(&self) -> LineSplitterSnapshot {
        self.splitter.snapshot()
    }
    /// Create a new parser with empty binding state and continue-on-error policy.
    #[must_use]
    pub fn new() -> Self {
        Self::with_policy(IgnorePolicy::Continue)
    }

    /// Create a parser with an explicit ignore policy.
    #[must_use]
    pub fn with_policy(policy: IgnorePolicy) -> Self {
        Self {
            splitter: LineSplitter::new(),
            state: ParserState::new(),
            apply: ApplyContext::new(policy),
        }
    }

    /// Borrow the binding state.
    #[must_use]
    pub fn state(&self) -> &ParserState {
        &self.state
    }

    /// Borrow the binding state mutably.
    pub fn state_mut(&mut self) -> &mut ParserState {
        &mut self.state
    }

    /// Borrow the coverage database accumulated so far.
    #[must_use]
    pub fn database(&self) -> &CoverageDatabase {
        self.apply.database()
    }

    /// Mutable model access for controlled transforms and semantic tests.
    pub fn database_mut(&mut self) -> &mut CoverageDatabase {
        &mut self.apply.db
    }

    /// Consume the parser and return the coverage database.
    #[must_use]
    pub fn into_database(self) -> CoverageDatabase {
        self.apply.into_database()
    }

    /// Return `true` when parsing stopped on hard-fail / stop policy.
    #[must_use]
    pub fn stopped(&self) -> bool {
        self.apply.stopped
    }

    /// Borrow the apply context (open section, policy).
    #[must_use]
    pub fn apply_context(&self) -> &ApplyContext {
        &self.apply
    }

    /// Feed a chunk of raw input bytes; return events for completed lines.
    pub fn feed(&mut self, bytes: &[u8]) -> Vec<ParseEvent> {
        let raw_lines = self.splitter.feed(bytes);
        self.process_raw_lines(raw_lines)
    }

    /// Finish the stream, flushing a final unterminated line if present.
    pub fn finish(&mut self) -> Vec<ParseEvent> {
        let mut events = Vec::new();
        if let Some(raw) = self.splitter.finish() {
            events.extend(self.process_raw_lines(vec![raw]));
        }
        events
    }

    /// Feed an already-delimited raw line (optional terminator included).
    pub fn feed_raw_line(&mut self, raw_line: &[u8]) -> ParseEvent {
        let normalized = normalize_logical_line(raw_line);
        self.apply_normalized(&normalized)
    }

    /// Feed a pre-normalized line (already chomped + trailing-`\s` stripped).
    pub fn feed_normalized_line(&mut self, normalized: &[u8]) -> ParseEvent {
        self.apply_normalized(normalized)
    }

    /// Parse an entire byte buffer to completion.
    pub fn parse_all(&mut self, bytes: &[u8]) -> Vec<ParseEvent> {
        let mut events = self.feed(bytes);
        events.extend(self.finish());
        events
    }

    /// Parse an entire buffer and return the coverage database.
    #[must_use]
    pub fn parse_database(bytes: &[u8]) -> CoverageDatabase {
        let mut p = Self::new();
        let _ = p.parse_all(bytes);
        p.into_database()
    }

    fn process_raw_lines(&mut self, raw_lines: Vec<RawLogicalLine>) -> Vec<ParseEvent> {
        let mut events = Vec::with_capacity(raw_lines.len());
        for raw in raw_lines {
            let normalized = raw.normalized();
            events.push(self.apply_normalized(&normalized));
        }
        events
    }

    fn apply_normalized(&mut self, normalized: &[u8]) -> ParseEvent {
        let class: LineClass = classify_line(normalized);
        let event = self.state.apply_classified(class);
        match apply_event(&mut self.apply, &mut self.state, event) {
            ApplyResult::Ok(ev) | ApplyResult::Ignorable(ev, _) => ev,
            ApplyResult::HardFail(diag) => {
                // Surface hard-fail as Malformed-shaped event while keeping diag
                // on state; callers inspect `stopped()` / diagnostics.
                ParseEvent::Malformed {
                    kind: diag.kind,
                    line: diag
                        .related
                        .unwrap_or_else(|| ferricov_model::ByteString::from_slice(b"")),
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::ParseEvent;

    #[test]
    fn streaming_multi_section_updates_tn_sf() {
        let input = b"\
TN:A\n\
SF:/m0/first.c\n\
DA:1,1\n\
end_of_record\n\
TN:B\n\
SF:/m0/next.c\n\
DA:2,1\n\
end_of_record\n";
        let mut p = StreamingParser::new();
        let events = p.parse_all(input);

        assert!(events.iter().any(|e| matches!(
            e,
            ParseEvent::TestNameChanged { test_name, .. }
                if test_name.as_bytes() == b"A"
        )));
        assert!(events.iter().any(|e| matches!(
            e,
            ParseEvent::SourceBound(b) if b.raw_path.as_bytes() == b"/m0/first.c"
        )));
        assert!(events
            .iter()
            .any(|e| matches!(e, ParseEvent::Terminator { .. })));
        assert_eq!(p.state().test_name().as_bytes(), b"B");
        assert_eq!(
            p.state().source().unwrap().raw_path.as_bytes(),
            b"/m0/next.c"
        );
        assert_eq!(p.state().source().unwrap().bound_test_name.as_bytes(), b"B");
        // DA lines are applied in CORE-006.
        assert!(events.iter().any(|e| matches!(
            e,
            ParseEvent::RecordApplied {
                tag: crate::classify::RecordTag::Da,
                ..
            }
        )));
        assert_eq!(p.database().len(), 2);
    }

    #[test]
    fn crlf_and_chunked_feed_preserve_bindings() {
        let mut p = StreamingParser::new();
        let chunk1 = b"TN:name\r";
        let chunk2 = b"\nSF:path/\xff\r\nend_of_record\n";
        let _ = p.feed(chunk1);
        let events = p.feed(chunk2);
        let _ = p.finish();
        assert_eq!(p.state().test_name().as_bytes(), b"name");
        assert_eq!(
            p.state().source().unwrap().raw_path.as_bytes(),
            b"path/\xff"
        );
        assert!(events
            .iter()
            .any(|e| matches!(e, ParseEvent::Terminator { .. })));
    }

    #[test]
    fn comment_vs_leading_space_hash() {
        let mut p = StreamingParser::new();
        let events = p.parse_all(b"#real comment\n #not-comment\nTN:x\n");
        assert!(matches!(events[0], ParseEvent::IgnoredComment));
        assert!(matches!(events[1], ParseEvent::Malformed { .. }));
        assert_eq!(p.state().test_name().as_bytes(), b"x");
        assert!(!p.state().diagnostics().is_empty());
    }

    #[test]
    fn does_not_panic_on_arbitrary_bytes() {
        let mut p = StreamingParser::new();
        let junk: Vec<u8> = (0u8..=255).collect();
        let _ = p.parse_all(&junk);
        let mut mixed = junk;
        mixed.extend_from_slice(b"\nTN:ok\nSF:a.c\nend_of_record\n");
        let mut p2 = StreamingParser::new();
        let _ = p2.parse_all(&mixed);
        assert_eq!(p2.state().test_name().as_bytes(), b"ok");
    }
}
