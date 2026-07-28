# Compatibility Harness

This directory owns the pinned upstream Oracle, generated public-surface
inventory, fixtures, normalizers, and differential evidence.

No output difference may be normalized unless the rule is documented in
`docs/ssot/compatibility-contract.md` and tested independently.

Generate the candidate upstream inventory from the pinned checkout and help
snapshots with:

```bash
cargo run -p ferricov-oracle --bin inventory -- \
  /path/to/lcov-v2.5 compat/upstream/help compat/inventory/review \
  compat/inventory/v2.5.json
```

The v2 inventory treats the pinned parser definitions as canonical candidates,
then adds help and manual references without promoting documentation-only text
to accepted behavior. It records exact source lines, explicit aliases,
positionals, classification, applicability, review status, and runtime
dependencies. Each command also records its parser family, abbreviation, case,
prefix, ordering, short-option cluster, POSIX, and exact-only behavior with
pinned source references. Review output comes from identity-bound shards under
`inventory/review`; generated extraction cannot silently overwrite it.

All 584 entries are reviewed. The 394 command candidates comprise 346 public
options, 41 generated tokens, and 7 internal definitions. The generated tokens
are observed under both parser profiles: the default profile resolves 9 unique
abbreviations, rejects 2 ambiguous forms, and rejects 30 unknown forms; the
POSIX profile rejects all 41 as unknown. Generation rejects a dirty upstream
checkout.

The generated list is still an omission-detection input. `public` means that a
reviewed parser or installed surface is in scope; it does not mean Ferricov
implements the behavior. `generated_token` entries preserve rejected or
abbreviated documentation spellings without promoting them to public options.
Implementation, behavior planning, and evidence live in `behavior/contract.json`.

`python3 compat/verify.py --skip-oracle` validates the schema and semantic
contract without Docker or network access. Full verification additionally
checks every referenced upstream/help file and line, runs six parser-policy
probes plus all 82 generated-token/profile probes in network-disabled Oracle
containers, and requires byte-stable inventory regeneration from the pinned
checkout and review overlay. These are Oracle contract checks, not Ferricov
product evidence.

## Oracle Correctness Baseline

The M0 CLI contract has a retained raw Oracle baseline with 126 cases under
[`correctness/baselines/m0-cli-oracle-v2.5/`](correctness/baselines/m0-cli-oracle-v2.5/).
It records immutable image and executable identities, the exact clean
environment, execution user, raw streams, filesystem snapshots, timeout and
cleanup evidence. The baseline is validated by:

```bash
python3 compat/correctness/validate.py
python3 -m unittest compat/correctness/test_validate.py
```

An independently recorded replay passed semantic comparison. Timing and image
identity are excluded from that replay comparison, and the random Perl
`geninfo` tempfile token is normalized only for replay semantics; the retained
raw stderr remains unchanged. This is Oracle qualification evidence, not
Ferricov product compatibility evidence.

The pinned upstream test map is generated and validated separately:

```bash
python3 compat/inventory/tests/validate.py \
  --upstream-root /path/to/lcov-v2.5
```

It covers and reviews all 205 files under upstream `tests/`, retains content
hashes and the tests-tree identity, and distinguishes behavior drivers, harness
infrastructure, fixtures, and internal coverage.

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
