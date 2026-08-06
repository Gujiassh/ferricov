# M0 Tracefile Wave 2 Review Note

Status: lane implementation complete (Oracle/contract evidence only)  
Branch worktree: `/tmp/ferricov-trace-reader-wave2` (from `55af3cb`)  
Scope: M1-TF-001 / 004 / 006 / 008 / 012 / 015 / 016  
`product_compatibility_evidence`: **false** (unchanged)  
M1 / Ferricov parser-model: **not unlocked**

## Ownership

Lane-owned paths only:

- `compat/fixtures/m0-tracefiles/**` (wave2 fixtures, generator, capture pin, validators, tests, baseline/cases/manifest)
- `compat/tracefile/contract.py`, `compat/tracefile/v2.5.json`, `compat/tracefile/test_contract.py`
- `compat/schema/tracefile-contract.schema.json`
- this review note

Not modified: crates, behavior/diagnostics/installation lanes, shared `tasks.md`, README, docs/ssot.

## Evidence package

| Item | Value |
| --- | --- |
| Wave2 fixtures | 16 under `fixtures/wave2/` |
| Wave2 oracle cases | 37 (`WAVE2_CASE_IDS`) |
| Total fixtures / cases | 124 / 254 |
| Baseline file SHA-256 | `1fb07bd39932acf7edfc35b487b23ef504a226239e9de2b6e24ef70c0bfa46bb` |
| Cases SHA-256 | `20e4bc440d855d7c773bd37087c318a852e850534f3c7f71ab847f9291053a28` |
| Manifest SHA-256 | `808710631581d0426401d34a425c451607d11b1459486bb2fcadc37fef930bd8` |
| TF-030 registry SHA-256 | `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c` (unchanged) |
| Oracle pin | LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, image `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e` |

## Capture method

1. Regenerated fixtures/manifest/cases via `python3 generate.py`.
2. Selective Docker capture of **only** `--case-prefix wave2-` (37 cases) into `/tmp/ferricov-wave2-only-baseline.json`, then recaptured the two checksum cases after fixture fix.
3. Composed new `oracle-baseline.json` by **appending** wave2 observations in `oracle-cases.json` order while keeping all previous 217 observations byte-identical as JSON objects.
4. Did **not** use TF-030-gated `--merge-into` for wave2 (that path remains exact-15 TF-030 only).

Retained comparison vs HEAD baseline:

- `common=217 changed=0 removed=0 added=37`

Relative to the accepted wave1 217-observation set, wave2 is purely additive.

## Blocker → case binding

| Requirement | Fixture / case evidence |
| --- | --- |
| M1-TF-001 framing | `wave2-framing-blank*`, `wave2-framing-crlf-blank*`, `wave2-framing-no-final-newline-blank*`, `wave2-framing-trailing-ws*` |
| M1-TF-004 TN diff | `wave2-tn-diff*` (exact `,diff`, other comma suffixes, suffix after `,diff`, sanitization warning) |
| M1-TF-006 KF | `wave2-kf-parity*`, `wave2-kf-empty*` (SF rewrite, repeated-source additive, empty reject/ignore) |
| M1-TF-008 DA | `wave2-da-accumulate*`, `wave2-da-checksum-store*` (accumulate; checksum verify/store/rewrite vs no-verify drop) |
| M1-TF-012 summaries | `wave2-summary-forms*` (all eight tags, junk/missing-colon/nonnumeric/misplaced/suffixed forms recomputed) |
| M1-TF-015 terminators | `wave2-terminator-suffix*`, `wave2-terminator-dup*`, `wave2-terminator-missing*` |
| M1-TF-016 unknown input | `wave2-unknown-tags*`, `wave2-leading-ws-tag*`, `wave2-case-change*` (default hard fail + ignore-format recovery) |

Exact requirement bindings live in `compat/tracefile/contract.py` `EXACT_CASE_REQUIREMENTS` for all 37 wave2 case ids.

## Independent validators / reverse mutations

- Fixture byte anchors and rewrite/output fact anchors in `validate.py`.
- Focused reverse mutation suite: `Wave2TracefileMutationTests` in `test_validate.py`.
- Existing TF-030 mutation/merge gates remain green against the expanded baseline (merge baseline pin updated to new canonical SHA; TF-030 selection still exact 15).

## Verification run in lane

- `python3 validate.py` → validated 124 fixtures + pinned baseline
- `python3 -m unittest test_validate` → 47 tests OK
- `python3 -m compat.tracefile.contract --upstream-root /home/cc/code1/lcov-upstream-reference` → `TRACEFILE_CONTRACT_OK ... oracle_cases=254 product_compatibility=false`
- `python3 -m compat.tracefile.test_contract` → 20 tests OK
- `python3 compat/verify.py --skip-oracle` → run as part of lane closeout

## Residual risks

1. Wave2 capture used selective compose rather than full recapture of all 254 cases; retained 217 objects were verified equal to HEAD baseline, but a future full recapture could still surface nondeterministic stderr outside wave2 if environment drifts.
2. Companion IDs already partially covered elsewhere (bytes-* for CRLF/no-final-newline, checksum-* for M1-TF-035, wave1 features/order/repeat) are not duplicated; wave2 binds the remaining reader/state identities named above.
3. Remaining named TF blockers outside this wave (041/043/045/046/050/051/052/060/063/064, etc.) are still open.
4. No M0 go/no-go and no Ferricov parser/model authorization is implied by this lane.

## Acceptance for controller

Accept as **M0 Oracle/contract evidence only** for the seven named blockers above when:

- ownership boundaries hold,
- retained `common=217 changed=0 removed=0 added=37` holds,
- TF-030 registry/hash and product_compatibility_evidence remain false,
- tests/contract/verify gates above pass.
