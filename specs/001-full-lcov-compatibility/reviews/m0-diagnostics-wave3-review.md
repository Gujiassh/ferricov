# M0 Diagnostics Wave3 — Controller Closeout

Status: **S3 integrated; S4 CI fix in progress**  
Date: 2026-08-17  
Integration tip: `test/m0-tf030-exact-numeric-matrix` (see git for SHA after push)  
Baseline skeleton: `60b7a5e`  
Lane A: `7b85dbc` (Critical **ACCEPT_WITH_NOTES**)  
Lane B: `1b6d91c` (Critical **ACCEPT_WITH_NOTES**)

## Bound planned IDs (9 Oracle)

| ID | Lane | Exit / notes |
| --- | --- | --- |
| `PAR-GENINFO-CHILD-STOP-001` | A | exit 1; no PID -1; byte-stable |
| `PAR-GENINFO-CHILD-EXIT-ORACLE-001` | A | exit 124 timed_out; status-7 + PID -1; stderr SHA volatile |
| `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001` | A | exit 124 timed_out; warnings + PID -1; stderr SHA volatile |
| `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` | A | exit 124 timed_out; empty streams; byte-stable |
| `PAR-CHILD-SIGNAL-001` | B | 3-case matrix SIGTERM / SIGKILL / exit15 |
| `PAR-FORK-RETRY-001` | B | finite retry then terminal failure |
| `PAR-PAYLOAD-CORRUPT-001` | B | non-Storable dump rejected |
| `PAR-UNKNOWN-CHILD-001` | B | positive unknown PID |
| `PAR-PARENT-DEATH-001` | B | exit 143; no payload (not child parent-class transcript) |

## Must remain unbound (contract)

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

Live status: `docs/ssot/m0-status.snapshot.json` diagnostics.unbound_planned_cases = **3** (only FERRICOV pairs).

## Metrics

- diagnostics oracle_observations: **217** (was 206; +11 wave3)
- wave3_observations: **11**
- product_compatibility_evidence: **false**
- m1_authorized: **false**
- behavior primary gaps: **7** signed N/A (unchanged)

## Controller actions (S3)

1. Merged lane A then lane B with no-ff merges; rebuilt combined `wave3/result.json`.
2. Wired `compat/diagnostics/contract.py` + schema for wave3 kinds, counts, artifact hash.
3. Regenerated `compat/diagnostics/v2.5.json` and `docs/ssot/m0-status.snapshot.json`.
4. Extended `compat.diagnostics.test_contract` (58 tests OK).

## Residual notes (from Critical audits)

- Parent-death proves external kill + no payload, not full child `parent` diagnostic string.
- Fork-retry proves finite budget; terminal form may be `unknown process -1`.
- SIGKILL path uses fork/OOM wording, not `signal 9` text.
- Keep/ignore1 raw stderr hashes are snapshot-volatile; prefer semantic predicates on re-capture.
- Contract tests recompute stream hashes from sealed bins (snapshot identity).

## S4 hosted CI

- Branch `test/m0-tf030-exact-numeric-matrix` is not on the default `push: main` CI path; use `workflow_dispatch`.
- First dispatch run `32015991275` failed on two pre-existing branch debt items (not wave3 capture bugs):
  1. Oracle Evidence: `compat/verify.py` invoked TF-030 fixture pin check without `LCOV_SOURCE_ROOT` / sibling upstream tree.
  2. Behavior Contract: hard-coded residual totals still asserted 443/88 after residual program closed to 524/7.
- Fix slice:
  1. resolve/export `LCOV_SOURCE_ROOT` early in `compat/verify.py`, clone upstream in Oracle Evidence job;
  2. refresh behavior unit-test pins to live totals (524/7, plan bindings 526, wave1 filter 385/378/7);
  3. install host Perl deps (`libcapture-tiny-perl` et al.) for `inspect_model.pl` unit tests on both Behavior and Oracle jobs;
  4. refresh residual-era case contract tests that still expected hollow unreviewed status for closed IDs (`lcov-list-truncate-max`, lcov operation residuals except signed-N/A `compat-libtool`);
  5. materialize temporary harness launchers from rebuilt `ferricov/lcov-oracle:v2.5` image ID (historical launcher digests are capture pins, not live CI layer IDs);
  6. `compat/verify-guards.sh` rewrites launchers to the live local Oracle image before self-identity/duplicate guards.

## Non-claims

- No Ferricov product compatibility.
- No M1 authorization.
- No hollow close of the 7 behavior primary residuals.
