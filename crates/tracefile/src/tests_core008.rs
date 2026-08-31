use crate::{
    IgnorePolicy, SemanticSnapshot, Serializability, SerializationContext, SerializationError,
    StreamingParser,
};

fn parsed(bytes: &[u8]) -> StreamingParser {
    let mut parser = StreamingParser::new();
    parser.parse_all(bytes);
    parser
}

#[test]
fn snapshot_is_stable_and_covers_arbitrary_numeric_and_provenance_bytes() {
    let parser = parsed(b"TN:t-\xff\nSF:s\xff.c\nDA:1,-0\nDA:2,NaN\nDA:3,Inf\nend_of_record\n");
    let context = SerializationContext::default();
    let first = SemanticSnapshot::capture(&parser, &context);
    let second = SemanticSnapshot::capture(&parser, &context);
    assert!(first.semantically_equal(&second));
    assert!(matches!(
        first.serializability,
        Serializability::Serializable(_)
    ));
    assert!(!first.parser_state.diagnostics().is_empty());
}

#[test]
fn equality_distinguishes_similar_counts_diagnostics_and_lazy_family_presence() {
    let one = SemanticSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    let signed_zero = SemanticSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,-0\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(!one.semantically_equal(&signed_zero));

    let clean = SemanticSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    let diagnosed = SemanticSnapshot::capture(
        &parsed(b"unknown\nTN:t\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert_eq!(clean.database, diagnosed.database);
    assert_ne!(clean, diagnosed);

    let with_function_family = SemanticSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nFNL:0,1\nFNA:0,0,f\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert_ne!(clean, with_function_family);
}

#[test]
fn snapshot_retains_inflight_indexes_order_and_stop_policy() {
    let mut parser = StreamingParser::with_policy(IgnorePolicy::Stop);
    parser.parse_all(b"TN:t\nSF:x\nFNL:7,10\nFNA:7,1,z\nBRDA:2,9,x,1\nunknown\n");
    let snapshot = SemanticSnapshot::capture(&parser, &SerializationContext::default());
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
    let snapshot = SemanticSnapshot::capture(&parser, &SerializationContext::default());
    assert!(matches!(
        snapshot.serializability,
        Serializability::Nonserializable(SerializationError::BranchExpressionAbsent {
            edge_index: 0,
            ..
        })
    ));
    let numeric_expression = SemanticSnapshot::capture(
        &parsed(b"TN:t\nSF:x\nBRDA:1,0,0,1\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(matches!(
        numeric_expression.serializability,
        Serializability::Serializable(_)
    ));
    assert_ne!(snapshot, numeric_expression);
}
