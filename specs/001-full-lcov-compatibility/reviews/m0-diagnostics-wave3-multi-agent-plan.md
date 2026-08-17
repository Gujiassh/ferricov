# M0 Diagnostics Wave3 — Multi-Agent Execution Plan

Status: **active** (controller)  
Date: 2026-08-17  
Baseline: `test/m0-tf030-exact-numeric-matrix@206d412`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`  
Parent: `m0-diagnostics-wave3-plan.md`  
Standards: reuse wave1/wave2 provenance; residual execution standards where applicable

## Goal

Bind Oracle-observable diagnostics/parallel planned IDs that remain unbound after wave2.
Keep product evidence false and M1 gated.

### Bind targets (Oracle wave3a)

| Lane | Planned IDs |
| --- | --- |
| A geninfo-child matrix | `PAR-GENINFO-CHILD-STOP-001`, `PAR-GENINFO-CHILD-EXIT-ORACLE-001`, `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001`, `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` |
| B fault injectors | `PAR-CHILD-SIGNAL-001`, `PAR-FORK-RETRY-001`, `PAR-PAYLOAD-CORRUPT-001`, `PAR-UNKNOWN-CHILD-001`, `PAR-PARENT-DEATH-001` |

### Must remain unbound (contract hard rule)

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

Do not place these IDs in any `oracle_observations.planned_case_ids`.

## Non-goals

- Ferricov product differential / `product_compatibility_evidence=true`
- Closing the 7 signed-N/A behavior primary gaps
- Resolving `M1-MD-020` / `M1-TF-063` / `M1-TF-064`
- Setting `m1_authorized=true`
- Editing residual lane history branches

## Program gates

| Step | Owner | Pass |
| ---: | --- | --- |
| S0 | controller | this plan + lane briefs + skeleton ACCEPT |
| S1 | controller | two wave3 worktrees from same baseline SHA; clean residual worktrees removed |
| S2 | lane A/B implementers | capture + cases for owned IDs; independent Critical audit ACCEPT |
| S3 | controller | serial merge into integration; wave3 index + contract hooks; regenerate diagnostics + m0 status |
| S4 | controller | push integration; hosted CI green |
| S5 | controller | review note lists each of 12 IDs as bound or explicit residual; FERRICOV remain unbound |

## File ownership (no cross-edit)

| Path | Owner |
| --- | --- |
| `compat/diagnostics/wave3/scripts/lane_a_cases.py` | Lane A |
| `compat/diagnostics/wave3/fixtures/lane-a/**` | Lane A |
| `compat/diagnostics/wave3/cases/par-geninfo-child-*/**` | Lane A (after capture) |
| `compat/diagnostics/wave3/scripts/lane_b_cases.py` | Lane B |
| `compat/diagnostics/wave3/fixtures/lane-b/**` | Lane B |
| `compat/diagnostics/wave3/cases/par-child-signal-*/**`, `par-fork-retry-*/**`, `par-payload-corrupt-*/**`, `par-unknown-child-*/**`, `par-parent-death-*/**` | Lane B |
| `compat/diagnostics/wave3/scripts/capture_wave3.py` | controller skeleton; lanes may only import their lane module |
| `compat/diagnostics/contract.py` wave3 section | **controller only** (S3) |
| `compat/diagnostics/v2.5.json` | **controller only** via regenerate |
| `docs/ssot/m0-status.snapshot.json` | **controller only** via generate |
| reviews / briefs / audits | respective owners |

## Delivery shape

```
compat/diagnostics/wave3/
  scripts/
    capture_wave3.py      # shared harness (wave2-compatible)
    lane_a_cases.py       # CASE_SPECS for lane A
    lane_b_cases.py       # CASE_SPECS for lane B
  fixtures/
    lane-a/ ...
    lane-b/ ...
  cases/<case-id>/reference/{stdout,stderr}.bin + result.json
  result.json             # controller merges after both lanes capture
specs/.../reviews/
  m0-diagnostics-wave3-lane-A-brief.md
  m0-diagnostics-wave3-lane-B-brief.md
  m0-diagnostics-wave3-lane-A-review.md
  m0-diagnostics-wave3-lane-B-review.md
  m0-diagnostics-wave3-review.md   # controller closeout
```

## Provenance (mandatory, copy wave2)

- Image `sha256:b02cc...`, network none, user 1000:1000, workdir `/work`
- `env -i` with only declared variables; stdin `DEVNULL`
- Named container force cleanup; docker-ps observer errors fail closed
- Host timeout maps to exit `124` with `timed_out=true` when watchdog is the oracle
- Retain raw stdout/stderr bins, file tree, execution_manifest
- `evidence_status=oracle_reference`, `product_compatibility_evidence=false`

## Acceptance metrics

After S3:

- `python3 -m unittest compat.diagnostics.test_contract` green
- Unbound planned IDs drop from 12 toward residual floor of the 3 `*-FERRICOV-001` IDs
  (plus any Oracle IDs honestly blocked with documented harness limit)
- `docs/ssot/m0-status.snapshot.json` diagnostics.unbound_planned_cases updated
- No product evidence fields set true
- `m1_authorized` remains false

## Residual program cleanup (done before S1)

- Removed worktrees: `ferricov-m0-lane-A` … `F` (origin residual branches retained)
- Canonical worktree: `/home/cc/code1/ferricov` @ `206d412`
