use crate::{
    ContractClassification, ContractNonSerializableReason, EvidenceSnapshot, IgnorePolicy,
    NonSerializableReason, Serializability, SerializationContext, SerializationError,
    SourceBinding, SourceBindingProvenance, SourceProvenance, SourceTag, StreamingParser,
};
use ferricov_model::{
    ByteString, CoverageCount, FunctionTable, LineKey, SourceIdentity, TestName, TotalState,
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
    let first = EvidenceSnapshot::capture(&parser, &context);
    let second = EvidenceSnapshot::capture(&parser, &context);
    assert!(first.semantically_equal(&second));
    assert!(matches!(
        first.serializability,
        Serializability::Serializable(_)
    ));
    assert_eq!(
        first.attempted_output.as_ref(),
        match &first.serializability {
            Serializability::Serializable(bytes) => Some(bytes),
            _ => None,
        }
    );
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
fn accepted_absent_branch_expression_has_typed_non_serializable_classification() {
    let parser = parsed(b"TN:t\nSF:x\nBRDA:1,0,,1\nDA:1,1\nend_of_record\n");
    let snapshot = EvidenceSnapshot::capture(&parser, &SerializationContext::default());
    assert!(matches!(
        snapshot.serializability,
        Serializability::NonSerializable(NonSerializableReason::Writer(
            SerializationError::BranchExpressionAbsent { edge_index: 0, .. }
        ))
    ));
    assert!(snapshot.attempted_output.is_none());
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

    let binding = SourceBinding {
        tag: SourceTag::Sf,
        identity: left,
        raw_path: ByteString::from_slice(b"raw-input"),
        bound_test_name: TestName::new("t"),
    };
    assert_eq!(
        SourceBindingProvenance::from(&binding),
        SourceBindingProvenance {
            raw_path: ByteString::from_slice(b"raw-input"),
            diagnostic_path: Some(ByteString::from_slice(b"raw-a")),
        }
    );
}

fn assert_contract_non_serializable(
    case: &str,
    parser: &StreamingParser,
    expected: ContractNonSerializableReason,
) {
    assert_eq!(
        crate::classify_contract(parser, &SerializationContext::default()),
        ContractClassification::NonSerializable(expected),
        "{case} declarative classifier"
    );
    assert!(
        matches!(
            EvidenceSnapshot::capture(parser, &SerializationContext::default()).serializability,
            Serializability::NonSerializable(NonSerializableReason::Contract(reason))
                if reason == expected
        ),
        "{case}"
    );
    let snapshot = EvidenceSnapshot::capture(parser, &SerializationContext::default());
    assert!(snapshot.attempted_output.is_none(), "{case} forced through writer");
}

#[test]
fn classification_rejects_semantics_not_reconstructed_by_canonical_output() {
    let mut aggregate_divergence = parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n");
    let key = aggregate_divergence
        .database()
        .iter()
        .next()
        .unwrap()
        .0
        .clone();
    aggregate_divergence
        .database_mut()
        .get_mut(&key)
        .unwrap()
        .aggregate_mut()
        .lines_mut()
        .insert(LineKey::from_lexeme("9"), CoverageCount::from_lexeme("7"));
    assert_contract_non_serializable(
        "aggregate divergence",
        &aggregate_divergence,
        ContractNonSerializableReason::AggregateTestcaseDivergence,
    );

    let mut lazy_family = parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n");
    let key = lazy_family.database().iter().next().unwrap().0.clone();
    lazy_family
        .database_mut()
        .get_mut(&key)
        .unwrap()
        .testcases_mut()
        .insert_functions(TestName::new("function-only"), FunctionTable::new());
    assert_contract_non_serializable(
        "lazy family",
        &lazy_family,
        ContractNonSerializableReason::FamilyWithoutLineMembership,
    );

    let mut populated_family = parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n");
    let key = populated_family.database().iter().next().unwrap().0.clone();
    let mut functions = FunctionTable::new();
    functions
        .insert_alias_at(
            LineKey::from_lexeme("8"),
            "omitted",
            CoverageCount::from_lexeme("3"),
        )
        .unwrap();
    populated_family
        .database_mut()
        .get_mut(&key)
        .unwrap()
        .testcases_mut()
        .insert_functions(TestName::new("function-only"), functions);
    assert_contract_non_serializable(
        "populated family omitted without line membership",
        &populated_family,
        ContractNonSerializableReason::FamilyWithoutLineMembership,
    );

    let mut totals = parsed(b"TN:t\nSF:x\nDA:1,1\nend_of_record\n");
    let key = totals.database().iter().next().unwrap().0.clone();
    totals
        .database_mut()
        .get_mut(&key)
        .unwrap()
        .set_observable_totals(TotalState::from_payload("cached"));
    assert_contract_non_serializable(
        "observable totals",
        &totals,
        ContractNonSerializableReason::ObservableTotals,
    );

    let late_tn = parsed(b"TN:A\nSF:x\nDA:1,1\nMCDC:2,1,t,1,0,a\nTN:B\nend_of_record\n");
    assert_contract_non_serializable(
        "late TN MC/DC",
        &late_tn,
        ContractNonSerializableReason::FamilyWithoutLineMembership,
    );

    let repeated_close = parsed(
        b"TN:t\nSF:x\nDA:10,1\nDA:20,2\nend_of_record\nTN:t\nSF:x\nDA:10,3\nDA:30,4\nend_of_record\n",
    );
    assert_eq!(
        crate::classify_contract(&repeated_close, &SerializationContext::default()),
        ContractClassification::BlockedOracleUnknown
    );
    let repeated = EvidenceSnapshot::capture(&repeated_close, &SerializationContext::default());
    assert_eq!(repeated.serializability, Serializability::BlockedOracleUnknown);
    assert!(repeated.attempted_output.is_none());
}

#[test]
fn attempted_output_survives_post_write_semantic_rejection() {
    let parser = parsed(b"TN:t\nSF:x\n");
    assert_eq!(
        crate::classify_contract(&parser, &SerializationContext::default()),
        ContractClassification::Serializable
    );
    let evidence = EvidenceSnapshot::capture(&parser, &SerializationContext::default());
    assert!(matches!(
        evidence.serializability,
        Serializability::NonSerializable(NonSerializableReason::RoundTripSemanticMismatch)
    ));
    assert_eq!(evidence.attempted_output.unwrap().as_bytes(), b"");
}

#[test]
fn blocked_oracle_unknown_is_distinct_from_decided_classifications() {
    assert_ne!(
        Serializability::BlockedOracleUnknown,
        Serializability::NonSerializable(NonSerializableReason::RoundTripSemanticMismatch)
    );
    assert_ne!(
        Serializability::BlockedOracleUnknown,
        Serializability::Serializable(ByteString::from_slice(b""))
    );
}

#[test]
fn tn_provenance_is_explicit_for_current_active_open_and_testcase_contexts() {
    let open = parsed(b"TN:a-b\nSF:x\nDA:1,1\n");
    let evidence = EvidenceSnapshot::capture(&open, &SerializationContext::default());
    assert_eq!(evidence.current_test_name_provenance.identity.as_bytes(), b"a_b");
    assert_eq!(
        evidence.current_test_name_provenance.unsanitized.as_ref().map(ByteString::as_bytes),
        Some(b"a-b".as_slice())
    );
    assert_eq!(
        evidence.active_test_name_provenance.as_ref().unwrap().unsanitized.as_ref().map(ByteString::as_bytes),
        Some(b"a-b".as_slice())
    );
    assert_eq!(
        evidence.open_test_name_provenance.as_ref().unwrap().unsanitized.as_ref().map(ByteString::as_bytes),
        Some(b"a-b".as_slice())
    );

    let closed = EvidenceSnapshot::capture(
        &parsed(b"TN:a-b\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(closed.testcase_name_provenance.iter().all(|entry| {
        entry.test_name.identity.as_bytes() == b"a_b"
            && entry.test_name.unsanitized.as_ref().map(ByteString::as_bytes)
                == Some(b"a-b".as_slice())
    }));

    let clean = EvidenceSnapshot::capture(
        &parsed(b"TN:a_b\nSF:x\nDA:1,1\nend_of_record\n"),
        &SerializationContext::default(),
    );
    assert!(closed.semantically_equal(&clean));
    assert_ne!(closed.current_test_name_provenance, clean.current_test_name_provenance);
    assert_ne!(closed.testcase_name_provenance, clean.testcase_name_provenance);
}
