# M0/M1 Blocker Feasibility — Can We Fill The Four Gaps?

Status: **LEDGER** (controller)  
Date: 2026-08-18  
Tip: `test/m0-tf030-exact-numeric-matrix@4268d84`  
Question: can the four activation exclusions be "supplemented / closed" now?

## Short answer

| Blocker class | Can fill *now*? | Honest disposition |
| --- | --- | --- |
| A. 7 signed N/A primaries | **No** as suite seals; **maybe later** via applicability / normalizer / toolchain | Keep uncovered=7; optional re-probe only |
| B. 3 `*-FERRICOV-001` | **No** until Ferricov geninfo-child product exists | Keep unbound; Oracle twins already sealed |
| C. `M1-MD-020` / `TF-063` / `TF-064` | **No** for v0.1 core; **yes later** as CORE-009+ after parser exists | Stay in `blocked_case_ids` |
| D. `product_compatibility_evidence` | **No** until CORE-010 case evidence | Stay false; flip only case-by-case |

What *can* be done now is the path that makes D (and later B/C) possible:
implement `M1-CORE-001`…`008`, then differential closure.

## A. Seven signed N/A

Evidence: `reviews/m0-residual-s5-signed-na.md` + lane A/B/D probes.

| Target | Why still not sealable on pinned Oracle | What would make it closable |
| --- | --- | --- |
| `command.geninfo.option.compat-libtool` | No exit / `out.info` tree delta under GCC-12 intermediate capture | Different compiler/capture path that exercises `.libs` strip, or inventory applicability revision with controller approval |
| `command.lcov.option.compat-libtool` | Same capture forward path | Same |
| `command.perl2lcov.option.preserve` | Only unstable `filter_dat*` temp dirs; no approved temp-name normalizer | Approved normalizer + residual policy change, or applicability N/A |
| `lcovrc.rtl-file-extensions` | No public tool calls `is_language('rtl')` | New public surface that reads RTL language extensions, or applicability N/A |
| `lcovrc.geninfo-compat-libtool` | Same `.libs` no-op class | Same as CLI compat-libtool |
| `lcovrc.geninfo-gcov-all-blocks` | Classic non-intermediate only; gcc-12 intermediate | Older gcov classic path fixture, or applicability N/A |
| `lcovrc.geninfo-interval-update` | stdout/profile only; not exact-v1 stable | New compared dimension with approved normalizer, or applicability N/A |

**Forbidden now:** hollow `reviewed` plans without suite deltas; inventing normalizers without controller approval; flipping inventory to N/A without explicit owner decision.

**Action this slice:** reaffirm keep-open; optional smoke re-probe only if cheap. No metric claim of zero gaps.

## B. Three FERRICOV diagnostics IDs

| ID | Current | Fill now? |
| --- | --- | --- |
| `PAR-GENINFO-CHILD-EXIT-FERRICOV-001` | Unbound; Oracle twin bound in wave3 | **No** — needs Ferricov child-exit product path |
| `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001` | Same | **No** |
| `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001` | Same | **No** |

Binding with Oracle-only observations would fake product parity. Correct sequence:
implement geninfo-child (post CORE-001…008 / capture work) → run Ferricov vs Oracle → bind.

## C. Model decision blockers

| ID | Fill now? | Earliest honest program |
| --- | --- | --- |
| `M1-MD-020` | No | CORE-009 after parser/model exist |
| `M1-TF-063` | No | After product limit table chosen + over-limit tests |
| `M1-TF-064` | No | CORE-009 corpus + CI budgets against Ferricov parser |

Listing fuzz target names is already done (planning). Executable campaigns are not.

## D. Product compatibility evidence

| Gate | Fill now? | Rule |
| --- | --- | --- |
| Domain `product_compatibility_evidence=true` | **No** | Requires Ferricov-vs-Oracle case evidence under CORE-010 review |
| Marketing / drop-in claim | **No** | Forbidden under support matrix |

## What we *will* do under "fill what we can"

1. Keep A–D open and visible (already matrix-excluded).
2. Start `M1-CORE-001` primitives in `crates/model` — prerequisite for later C/D.
3. Do not pretend any of A–D closed by this work.

## Controller signature

Feasibility ledger accepted. Proceed to CORE-001; do not hollow-close A–D.
