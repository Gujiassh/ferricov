# M0 TF-030 Exact Numeric Matrix Controller Review

## Scope

This review records the intended TF-030 exact numeric Oracle matrix closure in
`compat/fixtures/m0-tracefiles/`. It does not authorize Ferricov parser/model
implementation and does not claim product compatibility. The earlier controller
`m0-tf030-audit-rework-spec.md`. The TF-030 M0 Oracle evidence closure is now accepted after the sixth independent Critical audit; this does not authorize Ferricov parser/model implementation or claim product compatibility.

Pinned Oracle identity:

- LCOV `v2.5` at `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- Docker image ID `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
- one stabilized full capture producing 93 fixtures and 184 cases
- retained final baseline SHA-256 `b586a1196d120126f618b56f5995b6a2cc9f3bd27b2c4ab10e0e27e7f955e09e`

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
  `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c`), not
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

## Current Audit Decision

**Accepted for M0 TF-030 Oracle evidence closure; product compatibility remains
false and M1 remains blocked.** The sixth fresh-context independent Critical
audit found no blockers. It reproduced the pre-Docker merge rejection matrix,
trusted-baseline-byte parsing, ordered 15-case selection, 90/90 observation
mutation rejections, 90/90 case/observation type mutations, five fresh Docker
captures for each threshold case with stable retained stderr hashes, the
56-row/112-evaluation matrix, the `common=169, changed=0, removed=0, added=15`
baseline delta, and the generated contract/Rust/Python/Perl gates.

This acceptance is limited to the M0 Oracle evidence and contract work in this
branch. It does not authorize Ferricov parser/model implementation, promote
Oracle observations to product evidence, or unlock M1.


## Independent Review Matrix

| Area | Status | Evidence |
| --- | --- | --- |
| Goal alignment | pass | M0 Oracle evidence only; no Ferricov parser/model changes |
| Old observation preservation | pass | pinned baseline comparison: common=169, changed=0, removed=0, added=15 |
| Fixture and companion identity | pass | retained hashes are bound; format-atoms bytes are compared to pinned upstream checkout |
| Exact matrix completeness | pass | 12 upstream rows + 4 FNA mirrors + 40 candidates, in both policy modes |
| Scalar, stored-value, and cache semantics | pass | exact registry equality plus all-row single-field mutation tests |
| Diagnostic/order/output policy | pass | independent observation registry binds stdout/stderr/output/exit; type-sensitive JSON equality rejects int/bool/float cross-type mutations |
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

- The sixth independent Critical audit found no remaining blocker in the scoped
  TF-030 Oracle evidence closure. Merge-tool validation is bound to the
  canonical baseline path, fixed baseline SHA-256
  `b586a1196d120126f618b56f5995b6a2cc9f3bd27b2c4ab10e0e27e7f955e09e`, exact
  ordered TF-030 selection, and a single trusted baseline byte snapshot.
- The remaining 18 named blockers and broader M1 readiness tasks remain open;
  this closure does not claim product compatibility or authorize M1.

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

The required verification set passed, together with the sixth independent
Critical audit's fresh Docker repetition, mutation, merge-integrity, baseline
comparison, Rust, Perl, and generated-contract evidence. This controller review
accepts the scoped TF-030 M0 Oracle evidence closure; it does not mark Ferricov
product compatibility or authorize M1.
