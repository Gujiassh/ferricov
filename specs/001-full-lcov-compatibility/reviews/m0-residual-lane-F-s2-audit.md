# M0 Residual Lane F — S2 Critical Audit

Status: **ACCEPT** (controller Critical audit)

## Scope

| Field | Value |
| --- | --- |
| Worktree | `/home/cc/code1/ferricov-m0-lane-F` |
| Branch | `m0-residual/lane-F-misc` @ `5564d97` |
| Baseline | `346f86f` |
| Targets | 11 misc lcovrc keys (full brief set) |

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Goal | **pass** | product_compatibility_evidence=false; planned |
| Ownership | **pass** | 31 files, all lane-F paths; no pin/contract |
| Target set | **pass** | fragment 11 primary ids match brief |
| Substantive | **pass** | reviewed+planned+suite_cases |
| Oracle image | **pass** | b02cc645… |
| Differentials | **pass** | 12 sealed cases; variants differ exit and/or tree vs control |
| Unit tests | **pass** | 5/5 OK |

## Residual risks

- Mix of success and honest failure surfaces (e.g. split-char exit 255, lcov-json-module exit 2, check-data-consistency exit 1). Acceptable if descriptions state failure boundary.
- demangle-cpp depends on c++filt in Oracle image (sealed successfully exit 0).
- Host fragments still hold these case ids until S3 strip.

## Merge queue

**GO for S3** after controller serial merge protocol.
