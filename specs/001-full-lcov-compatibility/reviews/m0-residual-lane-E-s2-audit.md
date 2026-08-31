# M0 Residual Lane E — S2 Critical Audit

Status: **ACCEPT** (6/6; failure-surface seals)

## Scope

| Field | Value |
| --- | --- |
| Branch | `m0-residual/lane-E-parallel` @ `f461a81` |
| Targets | parallel, max-tasks-per-core, filter-chunk-size, filter-parallel, fork-fail-timeout, max-fork-fails |

## Checklist

| Area | Result |
| --- | --- |
| Goal / product false | **pass** |
| Ownership | **pass** |
| Substantive 6/6 | **pass** |
| Not pure wall-clock | **pass** (exit 1/255 + missing out.info / env parse fails) |
| Unit tests | **pass** (5/5) |

## Residual risks

- Three filter/parallel keys share one fail tree (exit 1); three ENV-expansion keys share another (exit 255). Honest but lower discrimination.
- Success-path scheduling still not sealed (documented).

## Merge queue

**GO for S3**.
