# M0 Remaining Residuals — Blocked Ledger

Status: **intentional signed N/A** (residual multi-agent program S5 closed)  
Integration tip: reviewed_primary **524**, gaps **7**, m1_authorized=false  
Sign-off: `m0-residual-s5-signed-na.md` · Audit: `m0-residual-s5-audit.md`

## Remaining primary gaps (7) — signed N/A

These stay public inventory entries. Do not hollow-close. Future work requires Oracle/toolchain change, approved normalizer, or a separate inventory applicability program with its own Critical audit.

### CLI (3)

| Target | Block reason |
| --- | --- |
| `command.geninfo.option.compat-libtool` | GCC12 intermediate JSON; `.libs` strip ineffective on trailing `/` dirs; no tree/exit delta |
| `command.lcov.option.compat-libtool` | same capture path |
| `command.perl2lcov.option.preserve` | only unstable parallel filter temp dirs; no exact-v1 seal |

### lcovrc (4)

| Target | Block reason |
| --- | --- |
| `lcovrc.rtl-file-extensions` | `%languageExtensions` populated but `is_language('rtl')` never called in public tools |
| `lcovrc.geninfo-compat-libtool` | same `.libs` strip no-op as CLI |
| `lcovrc.geninfo-gcov-all-blocks` | gcov 12 always intermediate; classic path rejects gcc-12 gcno |
| `lcovrc.geninfo-interval-update` | stdout/profile only; temp paths + timings not exact-v1 stable |

## Closed by residual lanes (31)

A1 + B4 + C3 + D6 + E6 + F11 = 31. See lane S2 audits and wave fragments `m0-residual-*-wave.json`.

## Policy

Do not hollow-close the 7. Prefer signed N/A (done for residual program) or future Oracle/toolchain change.

## Multi-agent program

- Plan: `m0-residual-multi-agent-plan.md` — **S5 closed**
- Standards: `m0-residual-execution-standards.md`
- S0 ACCEPT; S1 worktrees; S2 per-lane ACCEPT; S3 merge ACCEPT; S4 push ACCEPT; S5 signed N/A ACCEPT
