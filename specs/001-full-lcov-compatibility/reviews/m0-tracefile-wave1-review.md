# M0 Tracefile Wave 1 Review Note

Status: lane implementation complete (Oracle/contract evidence only)  
Branch worktree: `/tmp/ferricov-review-tracefile` (from `6a8a1d0`)  
Scope: M1-TF-002 / 003 / 005 / 014 / 020 / 023 / 027 / 028  
`product_compatibility_evidence`: **false** (unchanged)  
M1 / Ferricov parser-model: **not unlocked**

## Ownership

Lane-owned paths only:

- `compat/fixtures/m0-tracefiles/**` (wave1 fixtures, generator, capture pin, validators, tests, baseline/cases/manifest)
- `compat/tracefile/contract.py`, `compat/tracefile/v2.5.json`
- `compat/schema/tracefile-contract.schema.json`
- this review note

Not modified: crates, behavior/diagnostics/installation lanes, shared `tasks.md`, README, docs/ssot.

## Evidence package

| Item | Value |
| --- | --- |
| Wave1 fixtures | 15 under `fixtures/wave1/` |
| Wave1 oracle cases | 33 (`WAVE1_CASE_IDS`) |
| Total fixtures / cases | 108 / 217 |
| Baseline file SHA-256 | `c1f3617304918ab82ea84c8f5d6d8cfd2cd11be84e622eb0b8ee0b36506790b3` |
| Cases SHA-256 | `4edb30cf0462cd72abcc8b523b71f76e9002d9ae6c9e0c83b99e3f025f22b78a` |
| Manifest SHA-256 | `0f429afb7fed91371c2a3a31f6eddbf39f0e09bb8a35f0c492dacfab296091bd` |
| TF-030 registry SHA-256 | `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c` (unchanged) |
| Oracle pin | LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, image `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e` |

## Capture method

1. Regenerated fixtures/manifest/cases via `python3 generate.py`.
2. Selective Docker capture of **only** `--case-prefix wave1-` (33 cases) into `/tmp/ferricov-wave1-only-baseline.json`.
3. Composed new `oracle-baseline.json` by **appending** wave1 observations in `oracle-cases.json` order while keeping all previous 184 observations byte-identical as JSON objects.
4. Did **not** use TF-030-gated `--merge-into` for wave1 (that path remains exact-15 TF-030 only).

Retained comparison vs HEAD baseline:

- `common=184 changed=0 removed=0 added=33`

Relative to the pre-TF030 169-observation invariant plus the accepted TF-030 15-case addition, the previous 184 retained set is unchanged; wave1 is purely additive.

## Blocker → case binding

| Requirement | Fixture / case evidence |
| --- | --- |
| M1-TF-002 comments | `wave1-comments-core*`, `wave1-comments-leading-space*` (drop comments on write; leading-space `#` format reject; ignore-format recovery) |
| M1-TF-003 TN | `wave1-tn-names*`, `wave1-tn-forget.canonical` (empty TN, sanitization, forget-test-names merge) |
| M1-TF-005 SF | `wave1-sf-paths*`, `wave1-sf-empty*`, `wave1-sf-whitespace*` (path forms; empty/whitespace SF reject) |
| M1-TF-014 MCDC | `wave1-mcdc-core*`, `wave1-mcdc-u-modes*` (groups/indices/senses/comma expr/U modes) |
| M1-TF-020 order | `wave1-order-canonical*`, `wave1-order-permuted*` (canonical rewrite + equivalent semantic models) |
| M1-TF-023 repeats | `wave1-repeat-same-tn*`, `wave1-repeat-diff-tn-mcdc*` (same-TN additive; different-TN ownership) |
| M1-TF-027 features | `wave1-features-all.*` flag matrix (default function-only / all / no-function+branch+mcdc / branch-only / mcdc-only / lines-only) |
| M1-TF-028 summaries | `wave1-summary-payloads.canonical` (junk/repeated summaries recomputed, not trusted) |

Exact requirement bindings live in `compat/tracefile/contract.py` `EXACT_CASE_REQUIREMENTS` for all 33 wave1 case ids.

## Independent validators / reverse mutations

- Semantic closed validators for mcdc-core, order, same-TN repeat, diff-TN MCDC snapshots in `validate.py`.
- Output fact anchors for comment drop, TN forget rewrite, feature filters, summary recompute, U-clear mode, additive same-TN rewrite.
- Focused reverse mutation suite: `Wave1TracefileMutationTests` in `test_validate.py`.
- Existing TF-030 mutation/merge gates remain green against the expanded baseline (merge baseline pin updated to new canonical SHA; TF-030 selection still exact 15).

## Verification run in lane

- `python3 validate.py` → validated 108 fixtures + pinned baseline
- `python3 -m unittest test_validate` → 44 tests OK
- `python3 -m compat.tracefile.contract --upstream-root /home/cc/code1/lcov-upstream-reference` → `TRACEFILE_CONTRACT_OK ... oracle_cases=217 product_compatibility=false`
- `python3 -m compat.tracefile.test_contract` → 19 tests OK
- `python3 compat/verify.py --skip-oracle` → run as part of lane closeout

## Residual risks

1. Wave1 capture used selective compose rather than full recapture of all 217 cases; retained 184 objects were verified equal to HEAD baseline, but a future full recapture could still surface nondeterministic stderr outside wave1 if environment drifts.
2. Observed same-TN function/line additive counts (`FNA` alias hit 4 in semantic model vs rewritten `FNA:0,3,f`) are Oracle-observed and bound as facts; they are not yet a product compatibility claim.
3. Remaining named TF blockers outside this wave (041/043/045/046/050/051/052/060/063/064, etc.) are still open.
4. No M0 go/no-go and no Ferricov parser/model authorization is implied by this lane.

## Acceptance for controller

Accept as **M0 Oracle/contract evidence only** for the eight named blockers above when:

- ownership boundaries hold,
- retained `common=184 changed=0 removed=0 added=33` holds,
- TF-030 registry/hash and product_compatibility_evidence remain false,
- tests/contract/verify gates above pass.
