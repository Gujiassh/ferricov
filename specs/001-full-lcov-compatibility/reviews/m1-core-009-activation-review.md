# M1-CORE-009 Activation Critical Review

Status: **GO — bounded CORE-009 only**
Date: 2026-08-31
Decision base: `origin/main` at `e9b137017f9d2332d2383b804f1cacd65496896c`
Risk: **Critical**

## Question

Can properties and fuzz harnesses start after accepted CORE-001…008 without
resolving exclusions A–D, clearing `M1-MD-020` / `M1-TF-063` / `M1-TF-064`,
or claiming Ferricov product evidence?

## Evidence Audited

- All CORE-001…008 controller reviews are accepted or accepted with bounded
  residual notes. CORE-008 supplies separate semantic/evidence snapshots and a
  fail-closed serializability classifier, so properties have stable oracles.
- `coverage-model.md` and `m1-tracefile-core-agent-spec.md` already name seven
  properties, nine fuzz targets, deterministic seed derivation, minimized
  regression retention, and finite CI/scheduled safety budgets.
- `compat/model/v2.5.json` still lists `M1-MD-020`, `M1-TF-063`, and
  `M1-TF-064` in `blocked_case_ids`; no contract sets product evidence true.
- Main CI for the decision base passed all hosted gates in run
  `33381171913` (`e9b1370`): https://github.com/Gujiassh/ferricov/actions/runs/33381171913.
  It runs workspace fmt/check/test/clippy and current contract validation but has
  no CORE-009 campaign. Adding bounded harness gates is
  therefore implementation work, not evidence already obtained.
- `M0-RSRC-MEASURE-001` is a single-run Oracle observation. Its measurements
  and the harness caps cannot select Ferricov product resource limits.

## Semantic Oracle

1. Deterministic seeds and fixed generators reproduce every property failure.
2. Every fuzz run is finite and constrained by explicit input, cardinality,
   time, and memory caps; a cap breach fails closed.
3. Minimized failures retain sufficient bytes, seed, operation, target, and
   snapshot evidence to replay permanently.
4. CORE-009 activation changes no product compatibility flag and makes no
   Oracle parity, resource-limit, or performance claim.
5. Blocked rows stay blocked until their own complete evidence and independent
   acceptance reviews exist.

## Scope Decision

| Area | Result | Reason |
| --- | --- | --- |
| CORE-001…008 prerequisite state | pass | Reviews provide implemented model/parser/writer/snapshot surfaces and stable local oracles. |
| Deterministic property work | authorized | Fixed seeds, case counts, shrink evidence, and replay are bounded and candidate-internal. |
| Named fuzz harnesses | authorized, bounded | Target/corpus mapping and finite smoke/scheduled budgets are development safety gates. |
| `M1-MD-020` closure | excluded | Activation alone is not the complete adversarial campaign or retained acceptance record. |
| `M1-TF-063` closure | excluded | Safety caps are not product limits or over-limit parity. |
| `M1-TF-064` closure | excluded | It stays blocked until the complete corpus, CI/scheduled executions, shrink/replay artifacts, and failures pass review. |
| CORE-010 differential closure | unauthorized | Requires a separate matrix revision and Oracle/product-evidence review. |
| CORE-011 performance | unauthorized | Correctness parity prerequisite is absent. |
| Product compatibility evidence | false, required | No applicable Ferricov-vs-Oracle case set has completed CORE-010. |

## Reverse Review

If a worker treats a 60-second smoke run as closing `M1-TF-064`, reports the
512 MiB cap as a product limit, clears any blocked ID, starts Oracle differential
closure, or flips product evidence, the support matrix and generated SSoT must
reject the claim. If a fuzz process lacks deterministic provenance or a finite
budget, it is outside this authorization.

## Decision

**GO** for `M1-CORE-009` only under the amended support matrix. Exclusions A–D
remain open, all three model/tracefile IDs remain blocked, product evidence
remains false, and CORE-010/011 remain unauthorized.

## Independent Critical Acceptance

Status: **ACCEPTED**
Accepted activation commit: `b5a3a0f`
Date: 2026-08-31

The independent Critical re-audit accepted the activation contract after the
machine JSON became the single normative authority, the Markdown projection
became byte-exact and generated, and exclusions A-D were bound to live contract
state.

Acceptance evidence:

- `python -m unittest compat.test_verify.M0StatusSnapshotTests`: 14 passed.
- `python -m py_compile compat/verify.py compat/test_verify.py compat/status/generate_m1_activation_block.py`: passed.
- `python compat/status/generate_m1_activation_block.py`: passed; immediate second generation was SHA-256 stable.
- `python compat/status/generate_m0_status.py`: passed; immediate second generation was SHA-256 stable.
- `git diff --check origin/main`: passed with no trailing whitespace.
- Branch worktree at acceptance: clean.

This acceptance authorizes only bounded `M1-CORE-009`. It does not clear
`M1-MD-020`, `M1-TF-063`, or `M1-TF-064`; does not authorize CORE-010/011; and
does not change `product_compatibility_evidence=false`.
