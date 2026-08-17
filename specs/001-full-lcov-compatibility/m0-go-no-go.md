# M0 Go / No-Go Decision

Status: **NO-GO for M1 activation**  
Date: 2026-08-17  
Approver: main-controller (workspace session)  
Source branch: `test/m0-tf030-exact-numeric-matrix`  
Source SHA: `b0b9970ac248a552d48aa9ace665ad5f06f55554`  
Planned path (coverage-model): this file  
Related scope: `reviews/m0-model-blocker-scope.md`  
Related residual: `reviews/m0-residual-s5-signed-na.md`  
Related diagnostics: `reviews/m0-diagnostics-wave3-review.md`

## Decision

**NO-GO** — do **not** set `m1_authorized=true`, do **not** start
`crates/` product implementation, and do **not** claim Ferricov product
compatibility.

M0 planning / Oracle-reference work for the current residual and diagnostics
programs is **closed at the program level**. Activation of M1 Tracefile Core
remains blocked by the residual and gate list below.

## Oracle and contract identity

| Item | Value |
| --- | --- |
| Upstream release | LCOV v2.5 |
| Upstream commit | `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` |
| Historical Oracle image pin (launchers / retained evidence) | `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7` |
| Hosted CI (wave3 S4/S5) | https://github.com/Gujiassh/ferricov/actions/runs/32018428585 |
| product_compatibility_evidence | **false** (all domain contracts) |
| m1_authorized | **false** |

### Artifact hashes (at decision tip)

| Path | SHA-256 |
| --- | --- |
| `compat/model/v2.5.json` | `d450054cf967c39b5314d5c31fd4a7e781f532302a1f3961847e12d959683b73` |
| `compat/model/m1-model.json` | `2cb8238e9c4324a48fee14fdb1974a7fddd70f9ee61e74592384833fa7b26106` |
| `compat/diagnostics/v2.5.json` | `9d604c7d6d1ecde4cc27a579414193a11ca1972f0e49dc7a74e516e875aac64e` |
| `compat/behavior/contract.json` | `093f57ba54472a46bbf4f6e801c548db735a6a8cb97d4209645460dac7b95104` |
| `compat/behavior/plan-bindings.json` | `89f5591814d3b8e3adf0cea4fe152e5262773c17eedfdd49963099b9ec63b1af` |
| `compat/resources/results/oracle-x86_64-linux-20260729/result.json` | `97db3a1b5b5cc116914bfdeac582d73060057310559b2f4d6a769c14d0ea2d07` |

## Live M0 metrics (must match snapshot)

| Metric | Value |
| --- | --- |
| public inventory entries | 531 |
| reviewed primary coverage | 524 |
| uncovered public entries (gaps) | **7** |
| plan bindings primary_plans | 526 |
| diagnostics planned cases | 71 |
| diagnostics exact-bound planned | 68 |
| diagnostics unbound planned | **3** (`*-FERRICOV-001`) |
| diagnostics oracle observations | 217 |
| wave3 observations | 11 |

## Activation criteria vs current state

Criteria from `m1-tracefile-core-agent-spec.md` / coverage-model:

| Criterion | Required | Current | Met? |
| --- | --- | --- | --- |
| Every public behavior has a substantive planned case group | `m0-ready` / uncovered==0 **or** honest signed residual with exit approval | 7 signed-N/A unreviewed primaries remain | **NO** for m0-ready zero-gap; residual signed N/A accepted at program level only |
| `validate.py --mode m0-ready` | pass | fails while gaps=7 (by design) | **NO** |
| Coverage-model + grammar approved for M1 | approved contracts | contracts exist; model still has blocked_case_ids | **PARTIAL** — usable for planning, not full M1 approval |
| `M1-MD-020` / `M1-TF-063` / `M1-TF-064` resolved **or** explicitly excluded | scope recorded | scoped in `m0-model-blocker-scope.md`; still blocked in contract | **SCOPED, NOT RESOLVED** |
| Go/no-go artifact written | this file | written | **YES (artifact exists)** |
| Product compatibility evidence | required for compatibility claims | false | **NO claim** |

## Unresolved exceptions (carry into any future GO)

### A. Behavior primary signed N/A (7)

See `reviews/m0-residual-s5-signed-na.md`. Not hollow-closed.

| Target |
| --- |
| `command.geninfo.option.compat-libtool` |
| `command.lcov.option.compat-libtool` |
| `command.perl2lcov.option.preserve` |
| `lcovrc.rtl-file-extensions` |
| `lcovrc.geninfo-compat-libtool` |
| `lcovrc.geninfo-gcov-all-blocks` |
| `lcovrc.geninfo-interval-update` |

### B. Diagnostics product-parity unbound (3)

Oracle pairs bound in wave3; Ferricov parity IDs remain unbound by contract:

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

### C. Model decision blockers (3)

Scoped, not resolved — `reviews/m0-model-blocker-scope.md`:

- `M1-MD-020` — adversarial fuzz execution remains M1-only
- `M1-TF-063` — Ferricov product resource boundary / parity
- `M1-TF-064` — executable fuzz corpus + budgets

### D. Product evidence gate

No domain contract may set `product_compatibility_evidence=true` until
Ferricov-vs-Oracle parity evidence exists for that domain.

## What M0 programs closed successfully

| Program | Result |
| --- | --- |
| Residual multi-agent S0–S5 | 31 sealed + 7 signed N/A @ metrics 524/7 |
| Diagnostics wave3 S0–S5 | 9 Oracle PAR IDs bound (+11 obs); CI green `32018428585` |
| Resource `M0-RSRC-MEASURE-001` | 13-profile Oracle observation retained |
| TF-030 numeric matrix | Oracle reference closed; product still false |

## Explicit non-authorization

1. This NO-GO is **not** permission to implement `crates/{model,tracefile,ops,report,cli}`.
2. This NO-GO is **not** a product compatibility claim.
3. Writing this artifact removes only the process gap “no go/no-go file exists”;
   it does **not** clear residual, model, diagnostics, or product blockers.
4. A future **GO** requires a new signed revision of this document with
   `result: GO`, tip SHA, and an explicit M1 support matrix that either
   resolves or names exclusions for every remaining blocker.

## Future GO checklist (minimum)

- [ ] `uncovered_public_entries == 0` **or** inventory applicability program Critical-accepted for remaining 7
- [ ] `python3 compat/behavior/validate.py --mode m0-ready` passes (or successor mode documenting signed residuals)
- [ ] Model blockers resolved **or** M1 support matrix excludes them with owner + milestone
- [ ] Diagnostics FERRICOV IDs bound under product parity **or** explicitly deferred with owner
- [ ] At least one path to product evidence defined (still may stay false at M1 start if parity is the M1 goal)
- [ ] Fresh CI green on the GO tip
- [ ] New GO signature + SHA

## Controller signature

**Result: NO-GO for M1 activation.**  
M0 residual + diagnostics wave3 programs: closed.  
M1: remains gated.

