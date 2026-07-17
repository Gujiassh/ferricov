# Compatibility Harness

This directory owns the pinned upstream Oracle, generated public-surface
inventory, fixtures, normalizers, and differential evidence.

No output difference may be normalized unless the rule is documented in
`docs/ssot/compatibility-contract.md` and tested independently.

Generate the candidate upstream inventory from the pinned checkout and help
snapshots with:

```bash
cargo run -p ferricov-oracle --bin inventory -- \
  /path/to/lcov-v2.5 compat/upstream/help compat/inventory/v2.5.json
```

The generated list is an omission-detection input. Each entry still requires
manual classification and behavioral differential cases.

## Differential Runner

Suites and implementation launchers are versioned JSON documents. Run the
harness self-test with the pinned Oracle on both sides:

```bash
cargo run -p ferricov-oracle --bin differential -- \
  compat/cases/harness-self-test.json \
  compat/launchers/lcov-v2.5-oracle.json \
  compat/launchers/lcov-v2.5-oracle.json \
  /tmp/ferricov-harness-self-test
```

This suite is marked `harness_self_test` and cannot count as compatibility
evidence. A suite marked `compatibility` rejects reference and candidate
launchers that resolve to the same executable SHA-256, even when the launcher
name or container image differs. Each run uses a fresh working directory,
receives an independent fixture copy, and retains actual implementation
identities, raw stdout, stderr, exit status, timings, and a file tree with
content hashes, raw path bytes, Unix metadata, and hardlink relationships.

The reverse test intentionally compares the Oracle with a failing executable
inside the same Docker environment.
It must produce a non-zero process status while retaining failure artifacts:

```bash
cargo run -p ferricov-oracle --bin differential -- \
  compat/cases/harness-reverse-test.json \
  compat/launchers/lcov-v2.5-oracle.json \
  compat/launchers/different-oracle.json \
  /tmp/ferricov-harness-reverse-test
```

Only normalizers registered in `normalizers.md` may be used. Harness results
must validate against `schema/differential-result.schema.json` before they are
accepted as evidence.
