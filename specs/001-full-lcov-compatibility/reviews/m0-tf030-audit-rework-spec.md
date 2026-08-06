# M0 TF-030 Audit Rework Specification

## Status

Accepted for the scoped M0 TF-030 Oracle evidence closure after the sixth
independent Critical audit. This document does not authorize M1 implementation
or claim product compatibility; all retained observations remain Oracle
reference evidence.

## Context

The original TF-030 matrix implementation and semantic registry passed the
matrix, row, scalar, stored-value, cache, baseline-preservation, and generated
contract checks. Independent review then found evidence-contract gaps in the
validator boundary:

1. stdout, stderr, and output identities can be refreshed in memory because
   validation checks self-supplied hashes rather than an independent expected
   byte registry;
2. semantic snapshot JSON accepts unknown top-level fields; and
3. the numeric format fixture records upstream provenance but does not compare
   its bytes directly with the pinned upstream checkout.

A committed blank line at EOF also fails `git diff --check` against `origin/main`.

## Scope

This rework is limited to M0 Oracle evidence and validation. It covers:

- the six TF-030 semantic snapshots and the 15 TF-030 policy/canonical cases;
- retained stdout, stderr, output, exit, and output-existence facts for those
  cases;
- semantic snapshot top-level shape and duplicate JSON-key handling;
- direct binding of `fixtures/numeric/format-atoms.info` to
  `$LCOV_SOURCE_ROOT/tests/lcov/format/format.info`; and
- mutation tests and generated contract/hash synchronization.

It does not implement or modify the Ferricov Rust parser, model, save behavior,
product compatibility evidence, or M1 authorization.

## Required Changes

### Independent Observation Bytes

Add the retained TF-030 observation facts to an independent, strict ASCII JSON
registry. The registry must be contract-bound by SHA-256 and must contain the
expected exit status, stdout identity, stderr identity, output identity, output
path, and output existence for every TF-030 policy/canonical/semantic case.

Validation must compare actual observation fields against this registry before
accepting refreshed self-hashes. Existing semantic category/order checks remain
necessary but are not sufficient. The registry must not be generated from the
candidate observation during validation.

### Closed Semantic Shape

The TF-030 semantic validator must reject unknown top-level JSON keys and must
pin the exact `oracle` object shape. Add mutation coverage for an unknown key,
unknown nested oracle key, and a duplicate JSON key whose spelling uses a JSON
escape sequence.

The Perl numeric-plan loader must decode object keys before duplicate detection;
raw escaped key text is not an acceptable identity.

### Direct Upstream Binding

Under `LCOV_SOURCE_ROOT` (defaulting to the sibling pinned checkout), require
that the upstream `tests/lcov/format/format.info` exists and is byte-identical
to the generated `numeric-format-atoms` fixture. Validate the declared SHA-256
against the upstream bytes and retain the source path/hash in the manifest and
contract bindings.

### Hygiene

Remove the EOF whitespace reported by:

```text
git diff --check origin/main...HEAD
```

## Acceptance Criteria

- A mutation of any TF-030 stdout/stderr/output byte is rejected even when its
  local SHA-256 and byte size are refreshed.
- A mutation of exit status, output existence, or output path is rejected.
- Unknown semantic top-level/nested keys and escaped duplicate plan keys are
  rejected.
- A mutation of the pinned upstream source fixture or a wrong upstream root is
  rejected before Oracle evidence is accepted.
- The 56-row matrix, all 112 policy evaluations, and the old 169 observations
  remain unchanged: `common=169 changed=0 removed=0 added=15`.
- `product_compatibility_evidence=false` and M1 blocked remain explicit.
- All relevant generated artifact hashes, diagnostics/resource downstream
  bindings, SSoT/spec/task/review files, and the sixth independent audit are
  synchronized.

## Verification

Run after implementation:

```text
LCOV_SOURCE_ROOT=/home/cc/code1/lcov-upstream-reference python3 compat/fixtures/m0-tracefiles/validate.py
python3 -m unittest compat.fixtures.m0-tracefiles.test_validate
PERL5LIB=/home/cc/code1/lcov-upstream-reference/lib perl -c compat/fixtures/m0-tracefiles/inspect_model.pl
python3 compat/tracefile/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat.tracefile.test_contract
python3 compat/diagnostics/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat.diagnostics.test_contract
python3 compat/resources/contract.py
python3 compat/resources/validate.py --result compat/resources/results/oracle-x86_64-linux-20260729/result.json
python3 compat/verify.py --skip-oracle
python3 -m compileall -q compat
cargo fmt --all --check
cargo check --workspace --all-targets --locked
FERRICOV_SKIP_DOCKER_E2E=1 cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
git diff --check origin/main...HEAD
```

The sixth independent Critical audit completed the required fresh review and
found no remaining blocker in this scoped rework. It reproduced the merge
integrity gates, prior reverse mutations, deterministic Docker repetitions,
56-row/112-evaluation closure, old-baseline delta, and generated contract
checks. The TF-030 M0 Oracle evidence closure is accepted; product compatibility
remains false and M1 remains blocked.


## Additional Blocker: selective merge integrity (fourth/fifth/sixth audit)

The fourth independent Critical audit found that `capture_oracle.py --merge-into`
could accept an untrusted retained baseline copy: a temp/mutated file with
refreshed local observation self-hashes could still be used as the merge target,
and partial or non-TF-030 selections could replace retained observations outside
the 15 TF-030 cases.

### Required repair (implemented and independently accepted)

1. Before any Docker capture or merge write, require `--merge-into` to resolve to
   the canonical `compat/fixtures/m0-tracefiles/oracle-baseline.json` path.
2. Require the merge input file bytes to equal the fixed expected baseline SHA-256
   (`b586a1196d120126f618b56f5995b6a2cc9f3bd27b2c4ab10e0e27e7f955e09e`) — do not
   trust observation self-hashes alone.
3. Require the selected merge set to be exactly the 15 `TF030_CASE_IDS` in registry
   order (no partial merge, no non-TF-030 ids).
4. Keep non-merge `--case-id` selective capture available for repeat determinism
   probes without merge.
5. Add reverse coverage that mutates one non-TF-030 stdout, refreshes its local
   hash, invokes selective TF-030 `--merge-into`, and proves rejection before any
   output is accepted.
6. Move all `--merge-into` validation before `inspect_image` / `inspect_program`.
7. Preserve explicit `--case-id` order; reject duplicate and out-of-order merge
   selections against exact `list(TF030_CASE_IDS)`.
8. Bind merge parse to the single trusted baseline byte snapshot returned by
   hash validation (do not re-read merge path for parse).

### Acceptance status

Merge-integrity repair is implemented and was accepted by the sixth independent
Critical audit: validation runs before any Docker introspection, selection
preserves explicit `--case-id` order and rejects duplicate/overlapping/unmatched
selectors, and merge parsing uses the single trusted baseline byte snapshot
returned by hash validation. This remains Oracle capture/tooling work, not
Ferricov product compatibility evidence. `product_compatibility_evidence`
remains false, M1 remains blocked, and the 18 broader tracefile blockers remain
open.
