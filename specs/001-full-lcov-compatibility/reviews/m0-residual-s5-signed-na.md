# M0 Residual Program — S5 Signed N/A Closeout

Status: **SIGNED** (controller)  
Date: 2026-08-14  
Integration tip: `test/m0-tf030-exact-numeric-matrix@d7420f1`  
Metrics: reviewed_primary **524**, uncovered_public_entries **7**, m1_authorized **false**  
Oracle pin: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

## Program gates

| Step | Verdict | Evidence |
| ---: | --- | --- |
| S0 Spec package | ACCEPT | standards + multi-agent plan + lane briefs |
| S1 Worktrees | ACCEPT | six lane worktrees from shared baseline |
| S2 Per-lane | ACCEPT | A partial 1/4; B 4/5; C 3/3; D 6/9; E 6/6; F 11/11 |
| S3 Serial merge | ACCEPT | `m0-residual-s3-merge-audit.md` → 524/7 |
| S4 Push | ACCEPT | origin tip `d7420f1` |
| S5 Signed N/A | **this document** | 7 intentional residuals; no hollow close |

## Closed by residual program (31)

A1 + B4 + C3 + D6 + E6 + F11 = 31 substantive primary plans with suite-bound exact-v1 exit and/or filesystem differentials. Authored waves under `compat/behavior/fragments/authored/m0-residual-*-wave.json`.

## Signed N/A residuals (7)

Controller sign-off: these remain **public inventory** entries that require future Oracle/toolchain or normalizer work. They are **not** closed as reviewed+planned suite plans. Metrics correctly retain `uncovered_public_entries=7`. Hollow cmd_line-only or description-only reviewed plans are forbidden.

### CLI (3)

| Target | Signed N/A reason | Probe evidence |
| --- | --- | --- |
| `command.geninfo.option.compat-libtool` | On GCC 12 intermediate JSON capture, libtool strip is skipped when `current_working_directory` is present; when absent, `split_filename` yields trailing `/` so `$base =~ s/\.libs$//` never matches. Control vs `--compat-libtool` / `--no-compat-libtool` produce identical exit and `out.info` tree hashes. | Lane A review `m0-residual-lane-A-cli-hard-review.md` |
| `command.lcov.option.compat-libtool` | Same capture path as geninfo (`lcov --capture` forwards). No tree/exit delta. | Lane A review |
| `command.perl2lcov.option.preserve` | Without parallel filter temps, control vs preserve are tree-identical. With forced parallel + branch filter, preserve keeps `filter_dat*` dirs whose random suffix is not exact-v1 stable; exit/stdout/stderr identical. No approved temp-name normalizer for residual planning. | Lane A review |

### lcovrc (4)

| Target | Signed N/A reason | Probe evidence |
| --- | --- | --- |
| `lcovrc.rtl-file-extensions` | `%languageExtensions` / `set_extensions('rtl', …)` populate, but no public tool (`lcov`/`geninfo`/`genhtml`/converters) calls `is_language('rtl', …)`. Restricting extensions yields identical exit and filesystem trees (genhtml only changes `report/cmd_line`, which residual policy does not accept alone). | Lane B review + `probe-evidence-rtl-blocked.json` |
| `lcovrc.geninfo-compat-libtool` | Same `.libs` strip no-op class as CLI compat-libtool on this Oracle. | Lane D review |
| `lcovrc.geninfo-gcov-all-blocks` | `-a`/`--all-blocks` only on classic non-intermediate branch path. Gcov 12.2 always intermediate; forcing intermediate off is upgraded back or rejects gcc-12 `.gcno` (`Overlong record`). Key is a no-op for exit/filesystem on pin. | Lane D review |
| `lcovrc.geninfo-interval-update` | Only mutates progress interval (stdout with unstable `geninfo_datXXXX` temp paths) and profile timings. `out.info` identical across values; no stable exact-v1 dimension. | Lane D review |

## Explicit non-claims

1. This sign-off does **not** set inventory `applicability=not_applicable` for the seven public entries.
2. This sign-off does **not** author hollow `reviewed` acceptance plans without suite_cases.
3. `product_compatibility_evidence` remains false domain-wide.
4. `m1_authorized` remains false.
5. This is residual **multi-agent program** close, not full M0 exit review.

## Residual program DoD mapping

| Criterion | Result |
| --- | --- |
| uncovered==0 **or** explicit N/A with controller sign-off | **met via signed N/A** (gaps remain 7 in live metrics) |
| validate.py green after regenerate | met @ `d7420f1` |
| blocked ledger empty or only intentional N/A | **intentional N/A only** (this document + ledger) |
| M0 exit review artifact | **deferred** — separate process gate; blockers remain (diagnostics 12 unbound PAR-*, model MD-020/TF-063/TF-064, product evidence, exit review missing) |
| m1_authorized=false | met |

## Next tracks (ordered)

1. **Diagnostics wave3** — bind 12 unbound planned PAR-* IDs (Oracle reference; product false)
2. Model blockers M1-MD-020 / M1-TF-063 / M1-TF-064 (decision, not residual planning)
3. M0 exit review artifact when process gate is ready (still no auto M1)

## Controller signature

Signed by main-controller session for residual multi-agent program S5. Independent S5 audit: `m0-residual-s5-audit.md` (**ACCEPT**).
