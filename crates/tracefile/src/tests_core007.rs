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
    };
    let output = write_canonical(&database, &context);
    let ordered = b"DA:2,1\nDA:10,1\nDA:9007199254740993,1\nDA:10000000000000000000,1";
    assert!(output
        .windows(ordered.len())
        .any(|window| window == ordered));
}
