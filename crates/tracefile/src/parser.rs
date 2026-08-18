//! Streaming logical-line parser API.
//!
//! Feed arbitrary bytes (or pre-split lines). The parser splits, normalizes,
//! classifies, and updates binding state without panicking on arbitrary input.

use crate::classify::{classify_line, LineClass};
use crate::line::{normalize_logical_line, LineSplitter, RawLogicalLine};
use crate::state::{ParseEvent, ParserState};

/// Streaming LCOV logical-line parser (CORE-005 binding layer).
#[derive(Debug, Default, Clone)]
pub struct StreamingParser {
    splitter: LineSplitter,
    state: ParserState,
}

impl StreamingParser {
    /// Create a new parser with empty binding state.
    #[must_use]
    pub fn new() -> Self {
        Self {
            splitter: LineSplitter::new(),
            state: ParserState::new(),
        }
    }

    /// Borrow the binding state.
    #[must_use]
    pub fn state(&self) -> &ParserState {
        &self.state
    }

    /// Borrow the binding state mutably (for CORE-006 dispatch hooks).
    pub fn state_mut(&mut self) -> &mut ParserState {
        &mut self.state
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
    ///
    /// Useful for tests and for callers that split externally. Applies
    /// Oracle-equivalent chomp + trailing-`\s` normalization.
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
        self.state.apply_classified(class)
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
        assert!(events.iter().any(|e| matches!(e, ParseEvent::Terminator { .. })));
        assert_eq!(p.state().test_name().as_bytes(), b"B");
        assert_eq!(
            p.state().source().unwrap().raw_path.as_bytes(),
            b"/m0/next.c"
        );
        assert_eq!(
            p.state().source().unwrap().bound_test_name.as_bytes(),
            b"B"
        );
        // DA lines are stubs in CORE-005.
        assert!(events.iter().any(|e| matches!(
            e,
            ParseEvent::RecordStub {
                tag: crate::classify::RecordTag::Da,
                ..
            }
        )));
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
        assert_eq!(p.state().source().unwrap().raw_path.as_bytes(), b"path/\xff");
        assert!(events.iter().any(|e| matches!(e, ParseEvent::Terminator { .. })));
    }

    #[test]
    fn comment_vs_leading_space_hash() {
        let mut p = StreamingParser::new();
        let events = p.parse_all(b"#real comment\n #not-comment\nTN:x\n");
        assert!(matches!(events[0], ParseEvent::IgnoredComment));
        assert!(matches!(events[1], ParseEvent::Malformed { .. }));
        assert_eq!(p.state().test_name().as_bytes(), b"x");
        // Malformed line recorded a diagnostic.
        assert!(!p.state().diagnostics().is_empty());
    }

    #[test]
    fn does_not_panic_on_arbitrary_bytes() {
        let mut p = StreamingParser::new();
        let junk: Vec<u8> = (0u8..=255).collect();
        let _ = p.parse_all(&junk);
        // Also mixed with a valid TN/SF.
        let mut mixed = junk;
        mixed.extend_from_slice(b"\nTN:ok\nSF:a.c\nend_of_record\n");
        let mut p2 = StreamingParser::new();
        let _ = p2.parse_all(&mixed);
        assert_eq!(p2.state().test_name().as_bytes(), b"ok");
    }
}
