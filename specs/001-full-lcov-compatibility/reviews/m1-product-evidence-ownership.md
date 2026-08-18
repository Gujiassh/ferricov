# Who Can Give `product_compatibility_evidence`?

Status: **SSoT ownership note**  
Date: 2026-08-18  
Linked: `m1-v0.1-support-matrix.md` exclusion D, `m0-go-no-go.md`, CORE-010

## Short answer

| Role | Can flip the flag? | What they actually do |
| --- | --- | --- |
| Human owner (you) | **Authorize** broader claims / release language | Decide when a domain may claim compatibility |
| Main controller (this agent session) | **Sign** the case-by-case review that permits a domain flag | Inspect diffs, replay tests/Oracle gates, write acceptance |
| Implementation worker / CORE-010 lane | **Produce** Ferricov-vs-Oracle evidence artifacts | Run differentials, write manifests, propose flag changes |
| Oracle-only M0 planning | **Cannot** | Reference evidence ≠ product evidence |
| Chat summary / verbal "LGTM" | **Cannot** | Explicitly rejected by agent-spec Controller Acceptance |

Nobody "gives" product evidence by declaration. Evidence is **earned** by
Ferricov-vs-Oracle execution, then **accepted** by controller review, then the
domain contract flag may flip under that review.

## Pipeline (honest order)

1. **CORE-001…008** — build model/parser/writer that can run cases.
2. **CORE-010** — for each applicable in-scope case: run Ferricov and pinned
   Oracle; retain streams/status/filesystem (+ semantic snapshot where required);
   review every difference; sync evidence manifests.
3. **Controller Critical review** — accept or reject that case set; residual
   exclusions (A–C) stay out of the claim.
4. **Only then** — set `product_compatibility_evidence=true` on the **specific
   domain contract(s)** that the evidence covers (not a global marketing claim).
5. Support-matrix / go-no-go revision if the claim widens past v0.1 exclusions.

## What exists today

- All domain contracts: `product_compatibility_evidence=false`
- Snapshot gate: conditional GO forbids product true until CORE-010
- Oracle observations in `compat/`: reference only

## Non-claims

- Landing CORE-001/002 does not create product evidence.
- Binding FERRICOV IDs with Oracle-only seals does not create product evidence.
- Performance numbers without correctness parity do not create product evidence.

## Controller signature

Ownership note accepted. Proceed CORE-002…008; do not flip product flags.
