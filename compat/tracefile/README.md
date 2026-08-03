# LCOV 2.5 Tracefile Contract

This directory contains the standalone, fail-closed M0 inventory of LCOV 2.5
tracefile reader and writer behavior. It does not implement a parser and does
not provide Ferricov product-compatibility evidence.

The generated contract freezes:

- 20 known record tags and two lexical framing rules;
- all 15 record-matcher source lines in `TraceFile::_read_info`;
- all 18 canonical writer emission source lines, comprising 17 record tags and
  the explicit comment path;
- the reader-only `KF`, `FN`, and `FNDA` forms;
- all 21 per-record malformed fixtures, including the unknown-record fallback;
- all 42 retained fixtures and 63 pinned Oracle observations, including three VER fixtures, three state-ownership fixtures, and two semantic snapshots; and
- exact hashes for the corpus manifest, Oracle case manifest, and raw Oracle
  baseline.

The 63 observations remain reference-only. They comprise 42 default parses, 11 canonical rewrites, eight ignore-category recovery cases, and four state-ownership probes (two canonical rewrites and two semantic snapshots). Exact
arguments and raw stream/output bytes remain owned by
`compat/fixtures/m0-tracefiles/`; this contract binds their identities without
duplicating those evidence documents.

Validate the committed contract against a clean pinned upstream checkout:

```sh
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/tracefile/test_contract.py
```

Regenerate after an intentional reviewed contract change:

```sh
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference \
  --write
```

The broader proposed M1 grammar and model remain in
`specs/001-full-lcov-compatibility/`. This M0 inventory adds exact executable mappings for `M1-TF-007`, `M1-TF-021`,
`M1-TF-022`, and `M1-TF-026`, but 24 tracefile acceptance IDs still lack exact executable mappings
and M1 implementation remains unauthorized.
