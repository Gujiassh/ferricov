# M0 Numeric And Error Oracle Controller Review

## Scope

This review accepts the numeric/error/checksum Oracle-evidence slice in
`compat/fixtures/m0-tracefiles/`. It does not authorize Ferricov parser/model
implementation and does not claim product compatibility.

Pinned Oracle identity:

- LCOV `v2.5` at `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- Docker image ID recorded in `manifest.json`
- one stabilized full capture producing 88 fixtures and 169 cases

## Controller Acceptance

- Fixture generation and manifest validation pass for 88 fixtures.
- Oracle case generation and baseline validation pass for 169 ordered cases.
- The baseline binds primary and companion fixture bytes by SHA-256.
- Strict JSON validation rejects non-RFC constants, duplicate keys, non-ASCII
  bytes, and semantic identity drift.
- Semantic snapshots validate ordered `input`/`inputs`, complete aggregate and
  testcase projections, signed zero, output existence, and classified stderr.
- Numeric error policy cases cover default stop, ignore recovery, keep-going,
  explicit `stop_on_error=0/1`, excessive-count suppression, FNL/FN recovery,
  malformed numeric fields, negative values, signed zero, and checksum sources.
- Common observations retained from the preceding 84- and 101-case baselines
  are unchanged by case ID and raw stream/output identity.
- `product_compatibility_evidence` remains `false`.

## Review Findings And Rework

The initial delegated implementation was not accepted as delivered. Review
found stale fixture/case counts, weak semantic assertions, permissive JSON
parsing, missing fixture SHA binding, incomplete output/stderr policies, and
missing function suppression and explicit stop-on-error probes. Rework added
the fail-closed validator, companion-source binding, strict inspector output,
mutation tests, and the missing Oracle cases. The controller regenerated the
contract and reran the focused gates after each repair.

## Deliberate Boundary

`M1-TF-030` remains blocked and is not an exact structured mapping. The current
evidence does not provide the requirement's complete cross-family exact atom
matrix across `DA`, `FNDA`, `FNA`, and `BRDA`, with all required spellings,
semantic classes, retained values, thresholds, and canonical rewrites. The
existing numeric observations remain useful Oracle references but must not be
presented as closure of that requirement.

Exact structured mappings are limited to `M1-TF-031` through `M1-TF-036` for
the covered malformed, negative/zero, threshold/suppression, invalid-field,
checksum, and error-policy cases. They are Oracle byte/diagnostic evidence, not
full model-shape closure: the current inspector snapshots do not cover every
successful `FNDA`, `BRDA`, and `MCDC` recovery path. These mappings do not set
`ferricov_parity=pass`.

## Residual Risks

- `compat/fixtures/m0-tracefiles/validate.py` is about 2,076 lines and should
  be split by responsibility before the numeric lane grows further.
- The remaining named tracefile blockers in `tracefile-grammar.md` are still
  open, and M1 remains blocked by the project-level gates.
- No Ferricov implementation was exercised in this slice.

## Verification

```text
python3 compat/fixtures/m0-tracefiles/validate.py
python3 -m unittest compat/fixtures/m0-tracefiles/test_validate.py
python3 compat/tracefile/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/tracefile/test_contract.py
```

All commands pass in the accepted worktree state.
