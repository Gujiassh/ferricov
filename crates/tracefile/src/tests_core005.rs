//! Focused M1-CORE-005 acceptance tests (logical-line pipeline).

use crate::classify::{classify_line, LineClass, RecordTag};
use crate::line::{normalize_logical_line, LineEnding, LineSplitter};
use crate::parser::StreamingParser;
use crate::state::{sanitize_tn_base, ParseEvent, ParserState, SourceTag};

#[test]
fn chomp_crlf_lf_byte_preservation() {
    assert_eq!(normalize_logical_line(b"SF:/a\n"), b"SF:/a");
    assert_eq!(normalize_logical_line(b"SF:/a\r\n"), b"SF:/a");
    assert_eq!(normalize_logical_line(b"SF:/a  \t\r\n"), b"SF:/a");
    // Interior bytes including NULs survive.
    assert_eq!(normalize_logical_line(b"SF:a\0b\n"), b"SF:a\0b");
}

#[test]
fn comment_column_zero_vs_leading_space() {
    assert!(matches!(classify_line(b"#comment"), LineClass::Comment));
    assert!(matches!(
        classify_line(b" #not-comment"),
        LineClass::Unclassified { .. }
    ));

    let mut p = StreamingParser::new();
    let events = p.parse_all(b"#ok\n #not\n");
    assert!(matches!(events[0], ParseEvent::IgnoredComment));
    assert!(matches!(events[1], ParseEvent::Malformed { .. }));
}

#[test]
fn tn_empty_name_and_diff_suffix() {
    let mut state = ParserState::new();
    state.apply_classified(classify_line(b"TN:"));
    assert!(state.test_name().is_empty());

    state.apply_classified(classify_line(b"TN:name"));
    assert_eq!(state.test_name().as_bytes(), b"name");

    state.apply_classified(classify_line(b"TN:name,diff"));
    assert_eq!(state.test_name().as_bytes(), b"name,diff");
}

#[test]
fn sf_and_kf_bind_arbitrary_path_bytes() {
    let mut state = ParserState::new();
    state.apply_classified(classify_line(b"TN:t"));
    state.apply_classified(classify_line(b"SF:dir/\xff\x80.bin"));
    let src = state.source().unwrap();
    assert_eq!(src.tag, SourceTag::Sf);
    assert_eq!(src.raw_path.as_bytes(), b"dir/\xff\x80.bin");
    assert_eq!(src.identity.display_path().as_bytes(), b"dir/\xff\x80.bin");
    assert_eq!(src.bound_test_name.as_bytes(), b"t");

    state.apply_classified(classify_line(b"KF:other\0path"));
    let src = state.source().unwrap();
    assert_eq!(src.tag, SourceTag::Kf);
    assert_eq!(src.raw_path.as_bytes(), b"other\0path");
}

#[test]
fn end_of_record_terminator_detection() {
    match classify_line(b"end_of_record") {
        LineClass::Terminator { unconsumed } => assert!(unconsumed.as_bytes().is_empty()),
        other => panic!("{other:?}"),
    }
    match classify_line(b"end_of_record;junk") {
        LineClass::Terminator { unconsumed } => {
            assert_eq!(unconsumed.as_bytes(), b";junk");
        }
        other => panic!("{other:?}"),
    }
}

#[test]
fn non_utf8_path_bytes_survive_streaming() {
    let mut p = StreamingParser::new();
    p.parse_all(b"TN:x\nSF:p/\xff/\xfe\nend_of_record\n");
    assert_eq!(
        p.state().source().unwrap().raw_path.as_bytes(),
        b"p/\xff/\xfe"
    );
}

#[test]
fn streaming_feed_updates_tn_sf_state() {
    let snippet = b"\
TN:A\r\n\
SF:/m0/late-tn.c\n\
DA:1,1\n\
TN:B\n\
# comment\n\
end_of_record\n";
    let mut p = StreamingParser::new();
    // Chunked feed.
    let mut events = p.feed(&snippet[..7]);
    events.extend(p.feed(&snippet[7..]));
    events.extend(p.finish());

    assert_eq!(p.state().test_name().as_bytes(), b"B");
    let src = p.state().source().unwrap();
    assert_eq!(src.raw_path.as_bytes(), b"/m0/late-tn.c");
    // Late TN does not rebind the SF-bound test name.
    assert_eq!(src.bound_test_name.as_bytes(), b"A");
    assert!(p.state().source_open());
    assert!(events.iter().any(|e| matches!(e, ParseEvent::Terminator { .. })));
    assert!(events.iter().any(|e| matches!(e, ParseEvent::IgnoredComment)));
    assert!(events.iter().any(|e| matches!(
        e,
        ParseEvent::RecordStub {
            tag: RecordTag::Da,
            ..
        }
    )));
}

#[test]
fn sanitize_tn_base_matches_perl_ascii_w() {
    let (out, changed) = sanitize_tn_base(b"has space");
    assert!(changed);
    assert_eq!(out, b"has_space");
    let (out, changed) = sanitize_tn_base(b"valid_name");
    assert!(!changed);
    assert_eq!(out, b"valid_name");
}

#[test]
fn splitter_line_endings() {
    let mut s = LineSplitter::new();
    let lines = s.feed(b"a\r\nb\nc\r");
    let last = s.finish();
    assert_eq!(lines[0].ending, LineEnding::Crlf);
    assert_eq!(lines[1].ending, LineEnding::Lf);
    assert_eq!(last.unwrap().ending, LineEnding::Cr);
}
