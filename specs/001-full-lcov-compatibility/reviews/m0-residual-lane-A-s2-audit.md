# M0 Residual Lane A — S2 Critical Audit

Status: **ACCEPT** (partial: 1/4)

## Scope

| Field | Value |
| --- | --- |
| Branch | `m0-residual/lane-A-cli-hard` @ `eaee249` |
| Closed | `command.geninfo.option.history-script` |
| Honest blocked | compat-libtool (geninfo+lcov), perl2lcov.preserve |

## Checklist

| Area | Result |
| --- | --- |
| Goal / product false | **pass** |
| Ownership | **pass** |
| Substantive plan for history-script | **pass** |
| Differential | **pass** (history.loaded marker filesystem delta) |
| Unit tests | **pass** (5/5) |
| Hollow close of blocked 3 | **pass** (omitted from wave with evidence) |

## Merge queue

**GO for S3** for history-script only. Keep three blocked CLI keys on residual ledger.
