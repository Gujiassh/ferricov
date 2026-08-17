# M0 Model Blocker Scope — M1-MD-020 / M1-TF-063 / M1-TF-064

Status: **SCOPED (controller)**  
Date: 2026-08-17  
Source tip: `test/m0-tf030-exact-numeric-matrix@b0b9970`  
Contracts: `compat/model/v2.5.json`, `coverage-model.md`, `tracefile-grammar.md`  
Oracle image pin (historical capture): `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

## Purpose

Record an explicit, reviewable scope for the three remaining model decision
blockers so M0 exit review can be honest without:

- implementing Ferricov product limits,
- claiming product compatibility,
- or hollow-closing fuzz / resource-boundary cases as “done”.

This document does **not** remove the IDs from `blocked_case_ids`. They remain
blocked in the live model contract until M1 executable work lands.

## Live contract state

| Field | Value |
| --- | --- |
| `compat/model/v2.5.json` `blocked_case_ids` | `M1-MD-020`, `M1-TF-063`, `M1-TF-064` |
| `fuzz_execution_phase` | `M1-only` |
| `product_compatibility_evidence` | false |
| Model row `M1-MD-020` status | blocked |
| Model row reason | adversarial fuzz execution remains M1-only |
| Bindings on `M1-MD-020` | `M1-TF-063`, `M1-TF-064` |

## Blocker definitions

### M1-MD-020 — adversarial model / fuzz decision

| Item | Scope |
| --- | --- |
| Decision | Adversarial size, allocation, malformed nesting, and model invariant fuzzing |
| Required bindings | `M1-TF-062` (deterministic scale profiles, Oracle-observed lower bounds), `M1-TF-063`, `M1-TF-064`, `M0-RSRC-MEASURE-001`, named `M1-FZ-*` targets |
| What M0 already has | 13-profile `M0-RSRC-MEASURE-001` retained Oracle observation; deterministic scale profile definitions in grammar; harness budgets in coverage-model |
| What remains M1-only | Executable adversarial fuzz campaigns, shrink/replay corpus, CI 60s + scheduled 15m budgets as **product-facing** execution, any Ferricov invariant failure surface |
| Explicit non-claim | Resource profiles are **accepted lower bounds**, not product limits or causal performance gates |

### M1-TF-063 — product resource boundary / parity

| Item | Scope |
| --- | --- |
| Decision | Exact size/cardinality profiles vs any Ferricov product limit, over-limit diagnostic/exit/model state, and reviewed safety deviation |
| Oracle status | Oracle acceptance of the measured profiles is observed |
| What remains blocked | Ferricov product boundary selection, over-limit diagnostics, and parity against those boundaries |
| Prerequisite | M1 product candidate exists; optional reviewed resource-safety deviation if intentionally differs from accepted Oracle input |
| Explicit non-claim | M0 MUST NOT invent product limits from harness budgets or single-run RSS/time samples |

### M1-TF-064 — executable fuzz corpus

| Item | Scope |
| --- | --- |
| Decision | Corpus seeds from every record/legacy/prefix/state/hard-failure case mapped to all named `M1-FZ-*` targets, with shrink/replay artifacts and budgeted execution |
| What M0 already has | Named fuzz target inventory and safety budgets in coverage-model / agent spec |
| What remains blocked | Executable corpus generation, seed→target mapping retention, CI/scheduled fuzz runs against a Ferricov parser |
| Explicit non-claim | Listing named `M1-FZ-*` IDs is planning identity only |

## Disposition for M0 exit

| ID | M0 disposition | May M1 start with this open? |
| --- | --- | --- |
| `M1-MD-020` | **explicitly excluded from M0 completion**; remains decision_blocker | Only if M1 support matrix excludes adversarial fuzz from v0.1 **and** records that exclusion in go/no-go |
| `M1-TF-063` | **explicitly excluded from M0 completion**; product limit selection deferred | Same — M1 core may proceed only after go/no-go names the deferred boundary work |
| `M1-TF-064` | **explicitly excluded from M0 completion**; executable fuzz deferred | Same — parser may start only with fuzz marked post-core or gated |

Recommended M1 v0.1 support-matrix language (for go/no-go, not product code):

1. **In scope for M1-CORE-001…008:** byte/model/parse/write parity against Oracle-bound cases that are not in `blocked_case_ids`.
2. **Deferred (post-core / M1-CORE-009+):** adversarial fuzz execution (`M1-MD-020` / `M1-TF-064`) and product resource-limit selection (`M1-TF-063`).
3. **Still forbidden until parity evidence:** setting any domain `product_compatibility_evidence=true` without Ferricov-vs-Oracle evidence.

## What would resolve each blocker later

| ID | Resolution evidence required |
| --- | --- |
| `M1-MD-020` | Executable fuzz campaigns bound to model row; fail-closed invariant reports; no product claim without parity phase |
| `M1-TF-063` | Documented product limit table + Oracle comparison or reviewed safety deviation + tests for over-limit diagnostics |
| `M1-TF-064` | Seed corpus hashes, target map, shrink artifacts, CI budget runs with retained failures |

## Review checklist (phase 2)

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Scope only; no product implementation |
| Contract honesty | **pass** | IDs remain in `blocked_case_ids` |
| No hollow close | **pass** | Does not mark model rows resolved |
| No Perl copy / differential relaxation | **pass** | N/A — docs only |
| M1 still gated | **pass** | Explicit activation prerequisites remain |

## Verdict

**ACCEPT** model-blocker scope for use by M0 go/no-go. Blockers stay live until
M1 executable work; M0 may record them as intentional deferred decisions.

