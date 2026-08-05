# M0 TF-030 Exact Numeric Matrix Controller Review

## Scope

This review accepts the TF-030 exact numeric Oracle matrix slice in
`compat/fixtures/m0-tracefiles/`. It does not authorize Ferricov parser/model
implementation and does not claim product compatibility.

Pinned Oracle identity:

- LCOV `v2.5` at `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- Docker image ID `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
- one stabilized full capture producing 93 fixtures and 184 cases

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
- Policy cases cover default stop, ignore recovery, threshold stop, and
  canonical rewrite for format-atoms, FNA-mirror, and candidate fixtures.
- Comparison against `6a9a85d` yields common=169, changed=0, removed=0,
  added=15.
- Exact structured mapping includes `M1-TF-030` and `M0-TF-NUMERIC-001` for the
  exact-upstream anchors; product compatibility evidence remains `false`.
- Contract totals: fixtures=93, oracle_cases=184, semantic_snapshot_cases=23,
  exact executable requirement IDs include `M1-TF-030`.

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
python3 -m unittest compat/fixtures/m0-tracefiles/test_validate.py
python3 compat/tracefile/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/tracefile/test_contract.py
```

All commands pass in the accepted worktree state.
