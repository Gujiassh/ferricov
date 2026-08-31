# M0 Go / No-Go Decision

Status: **GO (conditional) for M1 Tracefile Core v0.1**  
Date: 2026-08-18  
Approver: main-controller (workspace session)  
Source branch: `test/m0-tf030-exact-numeric-matrix`  
Source SHA at decision base (pre-GO tip): `331447f7d91b926e8b3536f8fca10a3c6b492ec2`  
Support matrix: [`m1-v0.1-support-matrix.md`](m1-v0.1-support-matrix.md)  
Prior revision: 2026-08-17 **NO-GO** (superseded by this GO revision)  
Related scope: [`reviews/m0-model-blocker-scope.md`](reviews/m0-model-blocker-scope.md)  
Related residual: [`reviews/m0-residual-s5-signed-na.md`](reviews/m0-residual-s5-signed-na.md)  
Related diagnostics: [`reviews/m0-diagnostics-wave3-review.md`](reviews/m0-diagnostics-wave3-review.md)

## Decision

**Result: GO**

Authorize **conditional** activation of M1 Tracefile Core for tasks
`M1-CORE-001` … `M1-CORE-009` only, under
[`m1-v0.1-support-matrix.md`](m1-v0.1-support-matrix.md).

This GO:

- **does** set process permission for bounded `crates/model` + `crates/tracefile` work,
- **does not** claim Ferricov product compatibility,
- **does not** hollow-close the 7 signed-N/A primaries,
- **does not** bind the 3 `*-FERRICOV-001` diagnostics IDs,
- **does not** clear `M1-MD-020` / `M1-TF-063` / `M1-TF-064` from `blocked_case_ids`,
- **does** authorize bounded `M1-CORE-009` property/fuzz work without resolving blocked rows,
- **does not** authorize `M1-CORE-010` / `M1-CORE-011`.

## Oracle and contract identity

| Item | Value |
| --- | --- |
| Upstream release | LCOV v2.5 |
| Upstream commit | `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` |
| Historical Oracle image pin | `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7` |
| Hosted CI reference (wave3 S4/S5) | https://github.com/Gujiassh/ferricov/actions/runs/32018428585 |
| product_compatibility_evidence | **false** (required to stay false under this GO) |
| m1_authorized | **true** (conditional; matrix-bounded) |

### Artifact hashes (at decision authorship tip)

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
| uncovered public entries (gaps) | **7** (signed N/A; excluded by matrix) |
| plan bindings primary_plans | 526 |
| diagnostics planned cases | 71 |
| diagnostics exact-bound planned | 68 |
| diagnostics unbound planned | **3** (`*-FERRICOV-001`; excluded by matrix) |
| diagnostics oracle observations | 217 |

## Activation criteria vs this GO

| Criterion | Treatment under this GO |
| --- | --- |
| Every public behavior substantive / `m0-ready` | **Waived for v0.1** via support-matrix exclusion A (7 signed N/A). `m0-ready` may still fail. |
| Coverage-model + grammar | **Accepted for CORE-001…009 bounded implementation**; blocked IDs remain open |
| `M1-MD-020` / `M1-TF-063` / `M1-TF-064` | **Explicitly excluded** by support matrix (not resolved) |
| Go/no-go artifact | **This GO revision** |
| Product compatibility evidence | **Must remain false** until CORE-010 case evidence |

## Unresolved exceptions (still open; excluded not closed)

### A. Behavior primary signed N/A (7)

See residual S5. Listed in support matrix exclusion A.

### B. Diagnostics product-parity unbound (3)

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

### C. Model decision blockers (3)

Remain in `blocked_case_ids`; deferred with CORE-009+ / product limits.

### D. Product evidence

All domain `product_compatibility_evidence` flags stay false.

## What M0 programs closed successfully

| Program | Result |
| --- | --- |
| Residual multi-agent S0–S5 | 31 sealed + 7 signed N/A @ 524/7 |
| Diagnostics wave3 S0–S5 | 9 Oracle PAR IDs bound; CI green `32018428585` |
| Resource `M0-RSRC-MEASURE-001` | 13-profile Oracle observation retained |
| TF-030 numeric matrix | Oracle reference closed; product still false |
| Model blocker scope | Documented; not resolved |
| Support matrix | `m1-v0.1-support-matrix.md` |

## Explicit authorizations and bans

### Authorized

1. Implement `M1-CORE-001` … `M1-CORE-009` per agent spec + support matrix; CORE-009 uses deterministic seeds and hard safety budgets.
2. Add focused tests/fixtures required by those tasks.
3. Keep Oracle differentials fail-closed; no identity relaxation.

### Banned under this GO

1. Setting any domain `product_compatibility_evidence=true` without CORE-010 review.
2. Hollow-closing the 7 signed-N/A primaries or binding FERRICOV IDs with Oracle-only seals.
3. Removing model blocked IDs without executable evidence.
4. Starting `M1-CORE-010` / `M1-CORE-011` without a later matrix revision.
5. Widening into CLI / lcovrc / report / capture / install ownership.
6. Copying Perl internal object layout.

## Supersession

The 2026-08-17 **NO-GO** revision is superseded. Historical NO-GO text is retained
in git history. Machine detection keys off the signature line below.

## Controller signature

**Result: GO**

Conditional M1 Tracefile Core activation for `M1-CORE-001`…`M1-CORE-009` under
`m1-v0.1-support-matrix.md`. CORE-009 is deterministic and budgeted. Product evidence remains false, CORE-010/011 remain unauthorized, and exclusions A–D remain open.


## 2026-08-31 CORE-009 Amendment

`reviews/m1-core-009-activation-review.md` authorizes CORE-009 only. No blocked ID, product-evidence flag, product resource boundary, differential gate, or performance gate changes.
