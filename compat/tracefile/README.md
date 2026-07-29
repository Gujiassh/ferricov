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
- all 36 retained fixtures and 52 pinned Oracle observations; and
- exact hashes for the corpus manifest, Oracle case manifest, and raw Oracle
  baseline.

The 52 observations remain reference-only. They comprise 36 default parses,
eight canonical rewrites, and eight ignore-category recovery cases. Exact
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
`specs/001-full-lcov-compatibility/`. This M0 inventory does not resolve the 28
tracefile acceptance IDs that still lack exact executable mappings and does
not authorize M1 implementation.
