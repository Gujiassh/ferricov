# M0 TF-030 Exact Numeric Matrix Controller Review

## Scope

This review accepts the TF-030 exact numeric Oracle matrix slice in
`compat/fixtures/m0-tracefiles/`. It does not authorize Ferricov parser/model
implementation and does not claim product compatibility. The acceptance below
is the final controller audit after rework of the initial worker result; the
worker commit alone was not accepted because several independent scalar and
cache mutations still passed its validator.

Pinned Oracle identity:

- LCOV `v2.5` at `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- Docker image ID `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
- one stabilized full capture producing 93 fixtures and 184 cases
- retained final baseline SHA-256 `a04d26a29d548ebbf594a38dda3200c4c3e8e1c5b25afd3651568e15909c7689`

## Controller Acceptance

- Module split preserved retained artifact bytes and the 169 old Oracle
  observations before the matrix expansion.
- The 56-row four-family matrix is closed: 12 exact upstream format atoms,
  four current-FNA mirrors, and 40 candidate rows.
- Numeric plans are strict ASCII JSON companions bound by SHA-256 through
  `additional_fixtures` / `--numeric-plan`.
- Semantic snapshots assert ordered row identity, `looks_like_number`, Perl/B
  scalar-flag projections, category, threshold, retention/coercion, aggregate
  and testcase model values, and classified stderr.
- Semantic snapshots are checked against the contract-bound
  `tf030-semantic-registry.json` (SHA-256
  `8a353e6429889bef3b1d66dbbcd31776d36eea0382ad951e64a27935362cb16d`), not
  only against row shape or self-derived classifications. The registry fixes
  all row fields, every executed Perl/B scalar projection and flag, stored
  aggregate/testcase values, and aggregate/testcase source cache facts.
- The mutation suite iterates all 56 rows in both policy modes and rejects
  single-field changes to row identity, lexemes, fixture/source/testcase
  bindings, raw records/ordinals/locators, scalar flags/stages, value class,
  category/recovery/threshold facts, stored values, and cache totals.
- Policy cases cover default stop, ignore recovery, threshold stop, and
  canonical rewrite for format-atoms, FNA-mirror, and candidate fixtures.
- The tracefile schema and generated `v2.5.json` now bind five retained
  artifacts, including the semantic registry. The resource contract/result was
  regenerated only to rebind its generated grammar line-reference offsets;
  no resource observation or product limit was changed.
- Comparison against `6a9a85d` yields common=169, changed=0, removed=0,
  added=15.
- Exact structured mapping includes `M1-TF-030` and `M0-TF-NUMERIC-001` for the
  exact-upstream anchors; product compatibility evidence remains `false`.
- Contract totals: fixtures=93, oracle_cases=184, semantic_snapshot_cases=23,
  exact executable requirement IDs include `M1-TF-030`.
- Generated diagnostics downstream now contains 121 Oracle references (62
  fatal and 34 ignore-one tracefile/control observations) after rebinding the
  expanded 184-case baseline; all remain reference-only.

## Independent Review Matrix

| Area | Status | Evidence |
| --- | --- | --- |
| Goal alignment | pass | M0 Oracle evidence only; no Ferricov parser/model changes |
| Old observation preservation | pass | pinned baseline comparison: common=169, changed=0, removed=0, added=15 |
| Fixture and companion identity | pass | manifest/case/baseline/inspector/plan hashes and registry hash are contract-bound |
| Exact matrix completeness | pass | 12 upstream rows + 4 FNA mirrors + 40 candidates, in both policy modes |
| Scalar, stored-value, and cache semantics | pass | exact registry equality plus all-row single-field mutation tests |
| Diagnostic/order/output policy | pass | ordered stderr and stop/output-absence tests; full baseline validation |
| Module responsibility and file size | pass | numeric registry loading remains in `validation_numeric.py`; no product boundary crossed |
| Generated contracts | pass | tracefile and resource contracts regenerate and validate |
| Product evidence | pass | `product_compatibility_evidence=false` |
| M1 authorization | pass | M1 implementation remains blocked; TF-030 mapping is Oracle reference evidence only |

## Rework Record

The initial worker result (`0f13e61`) preserved the correct aggregate counts but
was rejected by reverse review: independent flips of scalar flags, semantic row
fields, and synchronized aggregate/testcase cache totals could still be
accepted. The final controller rework added a pinned semantic registry and
mutation coverage for every row and cache fact. The registry was derived from
the pinned six-snapshot baseline and is itself bound by the generated tracefile
contract, so changing either the retained observations or the expected semantic
facts fails a contract or validator gate.

## Deliberate Boundary

- This is Oracle-only M0 evidence. No Ferricov product parser or model work is
  authorized.
- Remaining named tracefile blockers stay open (18 after removing `M1-TF-030`
  from the unmapped set).
- M1 implementation remains blocked by project-level gates.
- MC/DC digit-boundary coverage remains under `M1-TF-031` and is outside this
  module's atom matrix.

## Residual Risks

- Full-corpus recapture was performed once after stabilization; future fixture
  edits require another pinned capture and hash rebinding.
- Inspector `--numeric-plan` extraction depends on coerced aggregate lookup
  after ignore-path classification; keep mutation coverage for row order,
  category, plan hash, and stop/canonical outputs.
- The remaining 18 named blockers and broader M1 readiness tasks remain open.

## Verification

```text
python3 compat/fixtures/m0-tracefiles/validate.py
python3 -m unittest compat.fixtures.m0-tracefiles.test_validate
python3 compat/tracefile/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat.tracefile.test_contract
python3 compat/resources/contract.py
python3 compat/resources/validate.py --result compat/resources/results/oracle-x86_64-linux-20260729/result.json
python3 compat/verify.py --skip-oracle
python3 -m compileall -q compat
```

The commands above pass in the final audited worktree. Rust, pinned Perl, and
full Docker recapture gates are recorded separately below when they require
those toolchains.
