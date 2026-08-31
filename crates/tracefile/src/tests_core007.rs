use crate::{write_canonical, SerializationContext, StreamingParser};

#[test]
fn canonical_writer_orders_families_recomputes_totals_and_is_stable() {
    let input = b"TN:t\nSF:src/a.c\nVER:v1\nDA:2,0\nDA:1,3,abc\nFNL:0,4,8\nFNA:0,2,zeta\nFNA:0,0,alpha\nBRDA:3,0,x,1\nBRDA:3,fU0,y,-\nMCDC:5,2,t,1,0,a\nMCDC:5,2,f,0,0,a\nLF:999\nLH:999\nend_of_record\n";
    let database = StreamingParser::parse_database(input);
    let context = SerializationContext {
        output_comments: vec!["generated".into()],
        ..Default::default()
    };
    let bytes = write_canonical(&database, &context);
    assert_eq!(bytes, b"#generated\nTN:t\nSF:src/a.c\nVER:v1\nFNL:0,4,8\nFNA:0,0,alpha\nFNA:0,2,zeta\nFNF:1\nFNH:1\nBRDA:3,0,x,1\nBRDA:3,fU0,y,-\nBRF:1\nBRH:1\nMCDC:5,2,t,1,0,a\nMCDC:5,2,f,0,0,a\nMCF:2\nMCH:1\nDA:1,3,abc\nDA:2,0\nLF:2\nLH:1\nend_of_record\n");
    assert_eq!(write_canonical(&database, &context), bytes);
}

#[test]
fn sections_come_only_from_line_testcase_membership_and_flags_omit_families() {
    let database = StreamingParser::parse_database(
        b"TN:t\nSF:x.c\nDA:1,1\nFNL:0,1\nFNA:0,1,f\nend_of_record\n",
    );
    let context = SerializationContext {
        function_coverage_enabled: false,
        branch_coverage_enabled: false,
        mcdc_coverage_enabled: false,
        checksum_output_enabled: false,
        output_comments: vec![],
        ..Default::default()
    };
    assert_eq!(
        write_canonical(&database, &context),
        b"TN:t\nSF:x.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
    );
}

#[test]
fn numeric_keys_sort_by_value_without_fixed_width_or_float_coercion() {
    let database = StreamingParser::parse_database(
        b"TN:t\nSF:x.c\nDA:10,1\nDA:2,1\nDA:9007199254740993,1\nDA:10000000000000000000,1\nend_of_record\n",
    );
    let context = SerializationContext {
        function_coverage_enabled: false,
        branch_coverage_enabled: false,
        mcdc_coverage_enabled: false,
        checksum_output_enabled: false,
        output_comments: vec![],
        ..Default::default()
    };
    let output = write_canonical(&database, &context);
    let ordered = b"DA:2,1\nDA:10,1\nDA:9007199254740993,1\nDA:10000000000000000000,1";
    assert!(output
        .windows(ordered.len())
        .any(|window| window == ordered));
}

#[test]
fn projection_controls_source_sort_and_provider_fills_only_missing_checksums() {
    let database = StreamingParser::parse_database(
        b"TN:z\nSF:a.c\nDA:1,1,stored\nDA:2,1\nend_of_record\nTN:a\nSF:a.c\nDA:3,1\nend_of_record\nTN:a\nSF:z.c\nDA:1,1\nend_of_record\n",
    );
    let before = database.clone();
    let projection = |source: &[u8]| {
        if source == b"a.c" {
            b"z-out.c".to_vec()
        } else {
            b"a-out.c".to_vec()
        }
    };
    let provider = |source: &[u8], line: &[u8]| Some([source, b"-", line].concat());
    let context = SerializationContext {
        source_path_projection: Some(&projection),
        optional_checksum_provider: Some(&provider),
        output_comments: vec![],
        ..Default::default()
    };
    let output = write_canonical(&database, &context);
    assert!(output.starts_with(b"TN:a\nSF:a-out.c\n"));
    let z_source = output
        .windows(b"SF:z-out.c".len())
        .position(|w| w == b"SF:z-out.c")
        .unwrap();
    let first_z_test = output
        .windows(b"TN:z\nSF:z-out.c".len())
        .position(|w| w == b"TN:z\nSF:z-out.c")
        .unwrap();
    assert!(
        z_source < first_z_test
            && output[..first_z_test]
                .windows(b"TN:a\nSF:z-out.c".len())
                .any(|w| w == b"TN:a\nSF:z-out.c")
    );
    assert!(output
        .windows(b"DA:1,1,stored".len())
        .any(|w| w == b"DA:1,1,stored"));
    assert!(output
        .windows(b"DA:2,1,z-out.c-2".len())
        .any(|w| w == b"DA:2,1,z-out.c-2"));
    assert_eq!(database, before);
    assert_eq!(write_canonical(&database, &context), output);
    let disabled = SerializationContext {
        checksum_output_enabled: false,
        source_path_projection: Some(&projection),
        ..Default::default()
    };
    assert!(!write_canonical(&database, &disabled)
        .windows(b",stored".len())
        .any(|w| w == b",stored"));
}

#[test]
fn branch_mcdc_non_utf8_and_round_trip_boundaries_are_canonical() {
    let input = b"TN:t\nSF:x\xff.c\nBRDA:10,9,0,1\nBRDA:10,2,0,1\nBRDA:10,2,1,0\nMCDC:3,10,t,1,0,a\nMCDC:3,U2,t,0,0,b\nDA:1,1\nend_of_record\n";
    let database = StreamingParser::parse_database(input);
    let output = write_canonical(&database, &SerializationContext::default());
    assert!(output
        .windows(b"SF:x\xff.c".len())
        .any(|w| w == b"SF:x\xff.c"));
    assert!(output
        .windows(b"BRDA:10,0,0,1\nBRDA:10,1,0,1\nBRDA:10,1,1,0".len())
        .any(|w| w == b"BRDA:10,0,0,1\nBRDA:10,1,0,1\nBRDA:10,1,1,0"));
    assert!(
        output
            .windows(
                b"MCDC:3,10,t,1,0,a\nMCDC:3,10,f,0,0,a\nMCDC:3,U2,t,0,0,b\nMCDC:3,2,f,0,0,b".len()
            )
            .any(|w| w
                == b"MCDC:3,10,t,1,0,a\nMCDC:3,10,f,0,0,a\nMCDC:3,U2,t,0,0,b\nMCDC:3,2,f,0,0,b")
    );
    let reparsed = StreamingParser::parse_database(&output);
    assert_eq!(
        write_canonical(&reparsed, &SerializationContext::default()),
        output
    );
}

#[test]
fn legacy_functions_serialize_only_as_current_records() {
    let database = StreamingParser::parse_database(
        b"TN:t\nSF:legacy.c\nFN:4,8,legacy\nFNDA:3,legacy\nDA:4,1\nend_of_record\n",
    );
    let output = write_canonical(&database, &SerializationContext::default());
    assert!(output
        .windows(b"FNL:0,4,8\nFNA:0,3,legacy".len())
        .any(|w| w == b"FNL:0,4,8\nFNA:0,3,legacy"));
    assert!(!output.windows(3).any(|w| w == b"FN:"));
    assert!(!output.windows(5).any(|w| w == b"FNDA:"));
}
