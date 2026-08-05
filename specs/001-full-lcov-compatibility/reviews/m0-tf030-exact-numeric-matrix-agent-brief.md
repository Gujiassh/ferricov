# M0 TF-030 Exact Numeric Matrix Agent Brief

## Assignment

Primary implementer: Grok 4.5 or the explicitly selected implementation agent.
Controller ownership remains in the main session.

Start from clean `main` at commit
`6a9a85dcf7d13f33244955e3ab5e66931ef62d28`. Implement the complete M0
Oracle-evidence closure required before `M1-TF-030` can receive an exact
structured mapping. This is one large development module with two reviewable
commits:

1. Split the oversized numeric corpus and validation responsibilities without
   changing any retained artifact bytes or any of the 169 existing Oracle
   observations.
2. Add the exact cross-family numeric matrix, capture the pinned Oracle once
   after stabilization, validate every semantic field, map `M1-TF-030`, and
   synchronize all generated contracts and durable specifications.

This assignment does not implement the Ferricov Rust parser or model. It does
not authorize M1, create Ferricov product evidence, claim compatibility, or
change any save, public CLI, installation, or persistence contract.

## Required Context

Read these files before editing:

- `AGENTS.md`
- `docs/ssot/project.md`
- `docs/ssot/compatibility-contract.md`
- `docs/ssot/performance-contract.md`
- `specs/001-full-lcov-compatibility/tracefile-grammar.md`
- `specs/001-full-lcov-compatibility/plan.md`
- `specs/001-full-lcov-compatibility/tasks.md`
- `specs/001-full-lcov-compatibility/reviews/m0-numeric-error-grok-controller-review.md`
- `compat/fixtures/m0-tracefiles/README.md`

Use the `behavior-compatible-rust-rewrite` skill. Work from observable Oracle
behavior, not from a Perl-to-Rust translation and not from inferred numeric
rules.

Run the workspace preparation and identity preflight:

```sh
python3 /home/cc/code1/dev-workbench/scripts/prepare_session.py \
  --repo-path /home/cc/code1/ferricov
git remote -v
git config user.name
git config user.email
git config --global user.name
git config --global user.email
git status --short
git worktree list --porcelain
```

The GitHub identity must remain `gujishh <baiaoshh@163.com>`. Use the existing
working tree; do not create a second Ferricov worktree. Create a local branch
named `test/m0-tf030-exact-numeric-matrix` from the required base. Do not push
without controller approval.

## Fixed Oracle Identity

- LCOV release: `v2.5`
- Source commit: `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- Docker image ID:
  `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
- LCOV executable SHA-256:
  `d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252`
- Container Perl: `5.36.0`
- Locale: `C.UTF-8`
- Network: disabled

Do not rebuild or replace the pinned image for this slice. Before any targeted
probe, verify the image and executable identities through the existing capture
helpers.

## Semantic Oracle

`M1-TF-030` requires verifiable statements for every atom:

1. The exact raw lexeme is bound to committed fixture bytes.
2. The applicable family is exactly one of `DA`, `FNDA`, `FNA`, or `BRDA`.
3. The pinned Perl runtime's `looks_like_number` decision is retained.
4. The numeric class is retained as one of `finite`, `positive_infinity`,
   `negative_infinity`, `nan`, `not_evaluated`, or `nonnumeric`.
5. Signed zero is represented losslessly; JSON numeric coercion must not erase
   the `-0` spelling.
6. The selected diagnostic category is exact: none, `format`, `negative`, or
   `excessive`.
7. Threshold comparison uses strict `value > excessive_count_threshold`.
8. Ignore recovery is explicit: format/negative become semantic zero;
   excessive values remain retained.
9. Aggregate and testcase model values are equal and independently asserted.
10. Canonical rewritten record bytes are exact.
11. Stdout, stderr category/order/severity, exit status, continuation point,
    and output existence are exact for each policy run.

A parser-regex test, a canonical output hash, or a whole-snapshot hash alone
does not close these invariants.

## Source Anchors

Verify current lines before relying on them, because the source reference must
bind the actual pinned file text:

- `tests/lcov/format/format.info:4-39`: exact upstream atoms and ordering
- `lib/lcovutil.pm:3936-3955`: numeric validation and diagnostic selection
- `lib/lcovutil.pm:4125-4165`: `BRDA` count validation and `-` state
- `lib/lcovutil.pm:4987-4998`: excessive threshold and suppression behavior
- `lib/lcovutil.pm:9103-9137`: `DA` parsing
- `lib/lcovutil.pm:9181-9187`: `FNDA` parsing
- `lib/lcovutil.pm:9202-9213`: `FNA` parsing
- `lib/lcovutil.pm:9217-9246`: `BRDA` parsing
- `lib/lcovutil.pm:9328-9363`: digit-only MC/DC parsing boundary
- `lib/lcovutil.pm:9553-9679`: canonical function, branch, MC/DC, and line output

## Required Matrix

### Exact Upstream Atoms

Reuse `fixtures/numeric/format-atoms.info`; do not modify its bytes or any
existing case. Add row-level evidence for:

| Family | Atom | No-threshold category | Threshold 1,000,000 category | Recovery |
| --- | --- | --- | --- | --- |
| `DA` | `-3` | `negative` | `negative` | zero |
| `DA` | `1.a0e+19` | `format` | `format` | zero |
| `DA` | `1.0e+19` | none | `excessive` | retain value |
| `FNDA` | `-2` | `negative` | `negative` | zero |
| `FNDA` | `1.5eb+20` | `format` | `format` | zero |
| `FNDA` | `1.5e+20` | none | `excessive` | retain value |
| `FNDA` | `-0` | none | none | retain signed zero |
| `BRDA` | `-1` | `negative` | `negative` | zero |
| `BRDA` | `-` | none | none | never evaluated |
| `BRDA` | `1.67+20` | `format` | `format` | zero |
| `BRDA` | `1.67e+20` | none | `excessive` | retain value |
| `BRDA` | `-0` | none | none | retain signed zero |

### Current FNA Mirror

Add `fixtures/numeric/tf030-fna-exact-mirror.info`. Mirror the four function
count atoms through current `FNL`/`FNA` records with stable unique indices and
aliases:

- `-2`
- `1.5eb+20`
- `1.5e+20`
- `-0`

The fixture must contain a valid line sentinel and canonical summaries so an
ignored malformed function entry cannot turn the entire source into an empty
coverage error. Do not reuse one FNL index for multiple atoms.

### Cross-Family Candidate Matrix

Add `fixtures/numeric/tf030-candidate-matrix.info`. Cover every candidate in
all four `looks_like_number` families:

| Atom | Expected class | Special policy |
| --- | --- | --- |
| `0` | `finite` | zero, no diagnostic |
| `+1` | `finite` | positive finite |
| `1.5` | `finite` | decimal finite |
| `1e3` | `finite` | exponent finite |
| `Inf` | `positive_infinity` | excessive only when threshold enabled |
| `+Inf` | `positive_infinity` | excessive only when threshold enabled |
| `-Inf` | `negative_infinity` | negative before threshold handling |
| `Infinity` | `positive_infinity` | excessive only when threshold enabled |
| `NaN` | `nan` | numeric, neither negative nor excessive |
| `nan` | `nan` | numeric, neither negative nor excessive |

Use one deterministic source section per family, stable line/index/block
locators, unique aliases, word-only TN values, and a valid line sentinel where
the family otherwise has no line data. Fixture order must make continuation
observable: ordinary finite values first, positive infinities next, NaNs next,
and `-Inf` last. Do not infer one family's behavior from another family.

### Declarative Row Plans

Add strict ASCII JSON companions:

- `fixtures/numeric/tf030-format-atoms-plan.json`
- `fixtures/numeric/tf030-fna-mirror-plan.json`
- `fixtures/numeric/tf030-candidate-plan.json`

Each row must include only declarative identity and locator data:

```json
{
  "id": "candidate.da.plus_one",
  "family": "DA",
  "lexeme": "+1",
  "source": "src/tf030-candidate-da.c",
  "testcase": "tf030_candidate_da",
  "locator": {"line": 2}
}
```

The plan must not contain hand-authored Oracle outcomes. The inspector derives
classification and the parsed model supplies stored values. The generator and
validator must prove that every plan row maps to exactly one record in the
fixture and that every intended matrix record maps to exactly one row. Bind
all companion bytes through the manifest, case `additional_fixtures`, capture
observation SHA-256 fields, and validator checks.

Before container execution, `capture_oracle.py` must load every referenced
numeric plan with the existing strict ASCII JSON rules and reject non-RFC
constants, duplicate object keys, a non-object root, or non-ASCII bytes. The
container inspector must never be the first component to discover an invalid
plan.

## Phase A: Behavior-Preserving Module Split

The current files exceed the workspace size limit:

- `compat/fixtures/m0-tracefiles/generate.py`: about 2,935 lines
- `compat/fixtures/m0-tracefiles/validate.py`: about 2,076 lines

Create these focused modules:

- `corpus_model.py`: `Fixture`, `ascii_bytes`, and shared byte metadata types
- `corpus_numeric.py`: numeric constants, numeric fixture builders, numeric
  summary/detail case builders, and numeric closure checks
- `validation_common.py`: strict JSON, byte identities, semantic input/stderr
  checks, and generic count/function/branch/MC/DC store assertions
- `validation_numeric.py`: numeric snapshot validators, numeric policy
  validators, and the numeric semantic registry

Keep `generate.py` and `validate.py` as script entry points and orchestration
layers. Re-export existing names used by `capture_oracle.py`,
`test_validate.py`, and external contract code so the first commit does not
force caller churn.

Required split invariants:

- `generate.build_fixtures()`, `generate.build_manifest()`,
  `generate.build_oracle_cases()`, `generate.write_corpus()`, and
  `generate.data_metadata()` remain callable.
- Numeric summary cases remain in their current relative position.
- Numeric detail/canonical/snapshot cases remain in their current relative
  position.
- No existing fixture, manifest, case, baseline, tracefile contract,
  diagnostics contract, or resource artifact byte changes.
- All 169 existing case objects and observation objects remain identical and
  ordered.
- Avoid generic plugin registries or dynamic discovery. Four explicit modules
  are sufficient.

Before the split, record SHA-256 for:

```text
compat/fixtures/m0-tracefiles/manifest.json
compat/fixtures/m0-tracefiles/oracle-cases.json
compat/fixtures/m0-tracefiles/oracle-baseline.json
compat/fixtures/m0-tracefiles/inspect_model.pl
compat/tracefile/v2.5.json
compat/diagnostics/v2.5.json
compat/resources/v2.5.json
compat/resources/results/oracle-x86_64-linux-20260729/result.json
```

Generate into a temporary directory after the split:

```sh
tmpdir=$(mktemp -d /tmp/ferricov-tf030-structure.XXXXXX)
python3 compat/fixtures/m0-tracefiles/generate.py --output-root "$tmpdir"
cmp "$tmpdir/manifest.json" compat/fixtures/m0-tracefiles/manifest.json
cmp "$tmpdir/oracle-cases.json" compat/fixtures/m0-tracefiles/oracle-cases.json
python3 compat/fixtures/m0-tracefiles/validate.py
python3 -m unittest -q compat/fixtures/m0-tracefiles/test_validate.py
git diff --check
```

Do not run the Oracle capture in Phase A. Commit only after every recorded hash
is unchanged. Suggested commit:

```text
refactor: split numeric tracefile corpus modules
```

## Phase B: Inspector Extension

Extend `inspect_model.pl` only behind a new explicit option:

```text
--numeric-plan <strict-json-path>
```

Default invocation must remain byte-identical for all 17 existing semantic
snapshots. Numeric-plan mode adds a top-level `numeric_atoms` array while
retaining the existing complete model snapshot.

Each derived atom row must contain:

- `id`, `family`, `lexeme`, `source`, `testcase`, and locator copied from the
  bound plan
- `looks_like_number`
- `numeric_class`
- `negative`
- `threshold_enabled`
- `threshold_text`
- `greater_than_threshold`
- `category`
- `recovery`
- lossless stored value `{ "class": ..., "text": ..., "negative_zero": ... }`
- aggregate model value
- testcase model value

Use `Scalar::Util::looks_like_number` from the pinned Perl runtime. Do not
reimplement it with a regex. Use numeric comparisons only after a positive
`looks_like_number` result. Represent all nonfinite values and signed zero as
JSON strings/objects so `JSON::PP` cannot emit non-RFC constants or erase sign.
For `BRDA` only, the exact `-` lexeme is the never-evaluated state and must be
classified before ordinary numeric validation: it has
`looks_like_number=false`, class `not_evaluated`, no diagnostic category, and
zero hits.

Fail closed on duplicate plan IDs, duplicate locators, unknown families,
missing records, extra matrix records, plan/fixture lexeme mismatch, missing
aggregate/testcase values, and non-ASCII plan JSON. Any nonempty stderr line
must still match the declared semantic diagnostic policy.

Update and bind the inspector SHA only after its behavior is final. First prove
all existing semantic snapshot outputs remain byte-identical by running the old
cases in targeted temporary capture mode.

## Phase C: Exact Case Set

Add these new cases. Names are part of the acceptance contract.

### Existing Format Fixture

- `numeric-format-atoms.tf030.semantic-snapshot`
- `numeric-format-atoms.tf030-threshold.semantic-snapshot`

The first uses `--numeric-plan` with `--ignore format,negative`. The second also
uses `--excessive-threshold 1000000` and ignores
`format,negative,excessive`. Existing default-stop, staged-ignore,
keep-going, explicit stop-on-error, canonical, and semantic cases remain
unchanged and become part of the final `M1-TF-030` mapping only after the new
row-level assertions pass.

### FNA Mirror Fixture

- `numeric-tf030-fna-mirror.default-stop`
- `numeric-tf030-fna-mirror.ignore-negative-stop-format`
- `numeric-tf030-fna-mirror.ignore-negative-format.canonical`
- `numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot`
- `numeric-tf030-fna-mirror.threshold-default-stop`
- `numeric-tf030-fna-mirror.threshold-ignore-all.canonical`
- `numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot`

Required sequence:

- default stops on `-2` with output absent
- ignoring `negative` reaches and stops on `1.5eb+20` format failure
- ignoring `negative,format` succeeds without threshold, coercing the first
  two invalid values to zero while preserving `1.5e+20` and `-0`
- with threshold 1,000,000 and only negative/format ignored, the run stops on
  `1.5e+20` as excessive
- ignoring all three categories succeeds and retains the excessive value

### Candidate Fixture

- `numeric-tf030-candidates.default-stop`
- `numeric-tf030-candidates.ignore-negative.canonical`
- `numeric-tf030-candidates.ignore-negative.semantic-snapshot`
- `numeric-tf030-candidates.threshold-default-stop`
- `numeric-tf030-candidates.threshold-ignore-all.canonical`
- `numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot`

Required sequence:

- without a threshold, all candidates except `-Inf` are accepted without a
  diagnostic; `-Inf` selects `negative` and default stop leaves output absent
- ignoring `negative` coerces only `-Inf` to zero and writes output
- with threshold 1,000,000, the first positive infinity selects `excessive`
  before the final negative infinity is reached
- ignoring `negative,excessive` writes output, retains positive infinities,
  keeps both NaN spellings, and coerces `-Inf` to zero

The planned total is 15 new cases and six new semantic snapshots. If targeted
Oracle probes show a different required case count, stop and update this brief
with the evidence before changing the scope.

## Phase D: Validator And Mutation Coverage

Add table-driven validators in `validation_numeric.py`. Assert every row in
both aggregate and testcase views. Do not accept subset checks.

Required direct mutations:

1. fixture SHA and each plan companion SHA
2. plan row order, duplicate ID, duplicate locator, missing row, and extra row
3. family and exact lexeme
4. `looks_like_number`
5. numeric class
6. signed-zero text/sign metadata
7. category and recovery decision
8. threshold enabled/text/comparison
9. aggregate stored value
10. testcase stored value
11. aggregate/testcase cache totals
12. stderr severity/category/order/count
13. exit status
14. output existence
15. canonical record bytes for every family/atom

Use `subTest` or generated named cases so a failure identifies the atom,
family, view, and field. Mutation tests must prove the validator rejects one
field change while all byte identities are refreshed; testing stale hashes
alone is insufficient.

Add reverse tests for legal delimiter data where relevant. In particular,
function aliases and branch expressions must retain comma-bearing or sign
characters without being mistaken for matrix metadata separators.

## Phase E: Targeted Probes And One Final Capture

Do not repeatedly run the 169+ case full capture while editing.

1. Stabilize fixture generation, plans, inspector, cases, and validators.
2. Generate a temporary cases document containing only the 15 new cases plus
   all pre-existing semantic snapshot cases.
3. Capture that temporary set to `/tmp`; do not overwrite the retained
   baseline.
4. Inspect raw stdout, stderr, exits, output bytes, and semantic JSON.
5. Encode the observed invariants and make all mutation tests pass.
6. Freeze the inspector and recompute its expected SHA.
7. Run one final full capture into `oracle-baseline.json`.

Before the final capture, preserve the accepted baseline from Git:

```sh
git show 6a9a85d:compat/fixtures/m0-tracefiles/oracle-baseline.json \
  > /tmp/ferricov-tf030-baseline-before.json
python3 compat/fixtures/m0-tracefiles/capture_oracle.py
```

After capture, compare by case ID. All 169 common case objects, including raw
stdout/stderr/output identities and Oracle metadata, must be byte-equivalent.
Expected result: `changed=0`, `removed=0`, `added=15`. Record the exact command
and output in the controller review. A common-case change blocks acceptance;
do not normalize or rewrite it away.

## Phase F: Contract And SSoT Synchronization

Only after all semantic validators pass:

1. Add the exact new case IDs to `EXACT_CASE_REQUIREMENTS` for
   `M1-TF-030`.
2. Bind the relevant existing format-atoms policy/canonical cases to
   `M1-TF-030` and `M0-TF-NUMERIC-001`.
3. Bind FNA mirror and candidate cases to `M1-TF-030`; do not add opportunistic
   mappings to `M1-TF-031` through `M1-TF-036`.
4. Keep every observation `oracle_reference`.
5. Keep `product_compatibility_evidence=false` and all Ferricov product
   evidence arrays empty.
6. Keep M1 blocked by the remaining M0 project gates.
7. Regenerate tracefile and diagnostics contracts through their generators;
   never hand-edit generated JSON.
8. Update schemas and count assertions from generated truth.
9. Regenerate resource bindings/results if SSoT line references move.
10. Update `tracefile-grammar.md`, `plan.md`, `tasks.md`,
    `docs/ssot/project.md`, `docs/ssot/compatibility-contract.md`, and the
    tracefile README with exact final counts and boundaries.
11. Add `reviews/m0-tf030-exact-numeric-matrix-controller-review.md` with the
    semantic oracle, findings, rework, old-case comparison, commands, hashes,
    mapping decision, and residual risks.

Do not rewrite historical review counts as current facts. Add a historical
snapshot note when an older review must remain readable.

## Required Verification

Run Python modules in separate processes where noted because this workspace
has top-level module-name collisions between different contract packages.

```sh
python3 compat/fixtures/m0-tracefiles/validate.py
python3 -m unittest -q compat/fixtures/m0-tracefiles/test_validate.py
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest -q compat/tracefile/test_contract.py
python3 compat/diagnostics/contract.py
python3 -m unittest -q compat/diagnostics/test_contract.py
python3 -m unittest -q compat/behavior/test_validate.py
python3 -m unittest -q compat/resources/test_contract.py
python3 -m unittest -q compat/resources/test_exercise.py
python3 compat/behavior/validate.py --mode current
python3 compat/verify.py --skip-oracle
python3 -m unittest -q compat/test_verify.py
python3 -m compileall -q compat
PERL5LIB=/home/cc/code1/lcov-upstream-reference/lib \
  perl -c compat/fixtures/m0-tracefiles/inspect_model.pl
cargo fmt --all --check
cargo check --workspace --all-targets --locked
FERRICOV_SKIP_DOCKER_E2E=1 \
  cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
git diff --check
```

Also rerun the rewrite readiness inventory and record, but do not attempt to
close unrelated property/fuzz/benchmark gaps in this slice:

```sh
python3 /home/cc/.skill/behavior-compatible-rust-rewrite/scripts/audit_rewrite_repo.py \
  /home/cc/code1/ferricov
```

## Controller Review Protocol

Classify this as `Critical`: it changes Oracle evidence, numeric semantics,
diagnostic categories, exact mappings, and generated contracts.

The independent reviewer must mark each area `pass`, `not applicable`, or
`blocked`:

- goal alignment
- old observation preservation
- fixture and companion identity
- exact matrix completeness
- Perl classification correctness
- signed-zero and nonfinite JSON safety
- threshold and recovery semantics
- aggregate/testcase parity
- canonical output bytes
- diagnostic stream/order/severity/count
- output existence and exit policy
- module responsibility and file size
- exact mapping truthfulness
- generated contract synchronization
- product evidence remains false
- M1 remains unauthorized

Reverse review is mandatory. Assume one atom was misclassified or one old
observation changed and identify the exact validator/mutation/comparison that
would catch it.

When review finds a defect, return it to the original implementation agent
with a concrete failing invariant. Do not open a replacement implementation
lane unless the original agent is unavailable or the scope materially changes.

## Commit And Delivery Plan

Use two coherent English commits:

```text
refactor: split numeric tracefile corpus modules
test: close the TF-030 Oracle numeric matrix
```

Before each commit, inspect `git diff --cached --stat`, run `git diff --check`,
and verify no unrelated files are staged. Do not amend after controller review
unless explicitly instructed. Do not push without controller approval.

Write a dev-workbench checkpoint after Phase A and after final controller
acceptance. The final checkpoint must record:

- base branch and SHA
- implementation branch
- both commit SHAs
- pinned Oracle identity
- fixture/case/snapshot totals
- old/new baseline comparison
- exact mapped requirement IDs
- verification commands and results
- push state
- next blocker and next step

## Stop Conditions

Stop and report before proceeding if any of these occurs:

- an existing fixture or existing case must change to make the new matrix pass
- a common baseline observation changes
- the pinned image or executable hash differs
- the candidate matrix reveals a new category or ordering not represented here
- `inspect_model.pl` default-mode bytes change
- exact mapping would require weakening a validator
- a generated contract cannot be synchronized without changing product
  evidence or M1 authorization
- a data/schema/public behavior change outside Oracle evidence appears necessary

Do not add fallback logic, compatibility aliases, normalizers, or silent
coercions to bypass a stop condition.

## Definition Of Done

The assignment is complete only when:

- Phase A is independently byte-stable and committed
- all exact and candidate matrix cells have raw and semantic Oracle evidence
- all 15 new cases are captured and validated
- all 169 old observations are unchanged by case ID
- row-level mutation tests fail closed for every required semantic field
- `M1-TF-030` has truthful exact structured mappings
- `product_compatibility_evidence` remains false
- M1 remains explicitly blocked by the remaining project gates
- all focused, contract, resource, behavior, Rust, Perl, and diff gates pass
- controller review and dev-workbench checkpoints are durable
- the implementation branch is clean

The final report must lead with unresolved findings. If none remain, state that
the M0 Oracle requirement is accepted while Ferricov product parity and M1
authorization remain out of scope.
