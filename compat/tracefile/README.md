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
- all 88 retained fixtures and 169 pinned Oracle observations, including three
  VER fixtures, three state-ownership fixtures, function-record probes, branch-record
  probes, numeric/error/checksum probes, and 17 semantic snapshots; and
- exact hashes for the corpus manifest, Oracle case manifest, and raw Oracle
  baseline.

The 169 observations remain reference-only. They comprise 86 default parses, 37
canonical rewrites, 29 ignore-category recovery cases, and 17 semantic snapshots
(two state-ownership probes, three function-record probes, three branch-record
probes, and nine numeric/error probes). Exact arguments and raw stream/output
bytes remain owned
by `compat/fixtures/m0-tracefiles/`; this contract binds their identities without
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
`specs/001-full-lcov-compatibility/`. This M0 inventory adds exact executable
mappings for `M1-TF-007`, `M1-TF-009`, `M1-TF-011`, `M1-TF-013`, `M1-TF-021`,
`M1-TF-022`, `M1-TF-024`, `M1-TF-025`, `M1-TF-026`, and `M1-TF-031` through
`M1-TF-036`. `M1-TF-030` remains intentionally unmapped: the current corpus
does not prove the required cross-family exact atom matrix. All observations remain
Oracle-only, 19 named tracefile blockers remain, and M1 implementation remains
unauthorized.
