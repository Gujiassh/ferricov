# M0 Conditional GO Package — Controller Critical Review

Status: **ACCEPT**  
Date: 2026-08-18  
Subject: support matrix + conditional GO + snapshot/agent-spec wiring

## Scope reviewed

- `specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md`
- `specs/001-full-lcov-compatibility/m0-go-no-go.md` (GO revision)
- `compat/verify.py` / `compat/status/generate_m0_status.py`
- `docs/ssot/m0-status.snapshot.json`
- `m1-tracefile-core-agent-spec.md`, `tasks.md`, `docs/ssot/project.md`
- prior phase reviews: `m1-v0.1-support-matrix-review.md`, `m0-exit-go-conditional-review.md`

## Semantic oracle

1. Conditional GO unlocks only `M1-CORE-001`…`M1-CORE-008`.
2. Exclusions A–D remain visible; they are not hollow-closed.
3. `m1_authorized=true` requires GO signature + ACTIVE matrix + product evidence false.
4. Product evidence cannot be true under this GO.
5. CORE-009/011 and CLI/lcovrc/report/capture widening stay banned.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Honest path: authorize bounded work, keep residuals open |
| User-visible / process flow | **pass** | Snapshot, agent-spec, tasks, project prose agree on conditional GO |
| Architecture / ownership | **pass** | model/tracefile only; matrix forbids CLI/report/capture |
| Data contracts | **pass** | product evidence stays false; blocked_case_ids retained |
| Implementation quality | **pass** | verify.py detects GO/matrix; blockers get activation_treatment |
| Verification | **pass** | regenerate + unit tests for authorize / inactive-matrix fail-closed |
| Reverse review | **pass** | Inactive matrix → m1_authorized false; product true forbidden |

## Evidence

- Live `build_m0_status_snapshot`: `m1_authorized=True`, product false, exclusion treatments present.
- Regenerated `docs/ssot/m0-status.snapshot.json` matches live contracts.
- Unit tests: authorize path + inactive-matrix fail-closed.

## Residual risks (accepted)

- `m0-ready` still fails on 7 signed N/A — expected under matrix waiver.
- FERRICOV parity and model fuzz/limit work remain future programs.
- Starting crates/ still requires following agent-spec ownership; GO is permission, not delivery.

## Verdict

**ACCEPT** conditional GO package. Safe to commit/push. Do not start CORE-009/011 or claim product compatibility from this package alone.
