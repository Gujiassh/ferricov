use crate::{
    EvidenceSnapshot, IgnorePolicy, Serializability, SerializationContext, SerializationError,
    SourceProvenance, StreamingParser,
};
use ferricov_model::{ByteString, SourceIdentity};

fn parsed(bytes: &[u8]) -> StreamingParser {
    let mut parser = StreamingParser::new();
    parser.parse_all(bytes);
    parser
}

#[test]
fn snapshot_is_stable_and_covers_arbitrary_numeric_and_provenance_bytes() {
    let parser = parsed(b"TN:t-\xff\nSF:s\xff.c\nDA:1,-0\nDA:2,NaN\nDA:3,Inf\nend_of_record\n");
    let context = SerializationContext::default();
    let first = EvidenceSnapshot::capture(&parser, &context);
    let second = EvidenceSnapshot::capture(&parser, &context);
    assert!(first.semantically_equal(&second));
    assert!(matches!(
        first.serializability,
        Serializability::Serializable(_)
    ));
    assert!(!first.parser_state.diagnostics().is_empty());
}

#[test]
fn equality_distinguishes_similar_counts_diagnostics_and_lazy_family_presence() {
    let one = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    let signed_zero = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,-0\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(!one.semantically_equal(&signed_zero));

    let clean = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    let diagnosed = EvidenceSnapshot::capture(
        &parsed(b"unknown\nTN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert_eq!(clean.semantic.database, diagnosed.semantic.database);
    assert!(clean.semantically_equal(&diagnosed));
    assert_ne!(clean, diagnosed);

    let with_function_family = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nFNL:0,1\nFNA:0,0,f\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert_ne!(clean, with_function_family);
}

#[test]
fn snapshot_retains_inflight_indexes_order_and_stop_policy() {
    let mut parser = StreamingParser::with_policy(IgnorePolicy::Stop);
    parser.parse_all(b"TN:t\nSF:x\nFNL:7,10\nFNA:7,1,z\nBRDA:2,9,x,1\nunknown\n");
    let snapshot = EvidenceSnapshot::capture(&parser, &SerializationContext::default());
    assert!(snapshot.stopped);
    assert_eq!(snapshot.ignore_policy, IgnorePolicy::Stop);
    let open = snapshot.open_section.expect("in-flight section retained");
    assert!(open.fnl_index.contains_key(&7));
    assert_eq!(
        open.branches.lines().next().unwrap().1.blocks()[0].model_position(),
        0
    );
}

#[test]
fn accepted_absent_branch_expression_has_typed_nonserializable_classification() {
    let parser = parsed(b"TN:t\nSF:x\nBRDA:1,0,,1\nDA:1,1\nend_of_record\n");
    let snapshot = EvidenceSnapshot::capture(&parser, &SerializationContext::default());
    assert!(matches!(
        snapshot.serializability,
        Serializability::Nonserializable(SerializationError::BranchExpressionAbsent {
            edge_index: 0,
            ..
        })
    ));
    let numeric_expression = EvidenceSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nBRDA:1,0,0,1\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(matches!(
        numeric_expression.serializability,
        Serializability::Serializable(_)
    ));
    assert_ne!(snapshot, numeric_expression);
}

#[test]
fn evidence_captures_unfinished_splitter_bytes_and_deterministic_finish() {
    let untouched = StreamingParser::new();
    let untouched_snapshot =
        EvidenceSnapshot::capture(&untouched, &SerializationContext::default());
    let mut partial = StreamingParser::new();
    assert!(partial.feed(b"TN:x").is_empty());
    let buffered = EvidenceSnapshot::capture(&partial, &SerializationContext::default());
    assert!(untouched_snapshot.semantically_equal(&buffered));
    assert_ne!(untouched_snapshot, buffered);
    assert_eq!(buffered.splitter.buffered, b"TN:x");
    let events = partial.finish();
    assert_eq!(events.len(), 1);
    assert_eq!(partial.state().test_name().as_bytes(), b"x");
    let finished = EvidenceSnapshot::capture(&partial, &SerializationContext::default());
    assert!(finished.splitter.buffered.is_empty());
    assert_ne!(buffered, finished);
}

#[test]
fn evidence_provenance_distinguishes_diagnostic_path_ignored_by_model_identity() {
    let left = SourceIdentity::from_display_path("x").with_diagnostic_path("raw-a");
    let right = SourceIdentity::from_display_path("x").with_diagnostic_path("raw-b");
    assert_eq!(left, right);
    let left_evidence = SourceProvenance {
        lookup_key: ByteString::from_slice(left.lookup_key().as_bytes()),
        diagnostic_path: left.diagnostic_path().cloned(),
    };
    let right_evidence = SourceProvenance {
        lookup_key: ByteString::from_slice(right.lookup_key().as_bytes()),
        diagnostic_path: right.diagnostic_path().cloned(),
    };
    assert_ne!(left_evidence, right_evidence);
}
