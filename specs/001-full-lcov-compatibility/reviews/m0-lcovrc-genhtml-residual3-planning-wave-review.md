# M0 lcovrc Genhtml Residual3 Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes four residual config keys:

- `lcovrc.compact-summary-tables` (`compact_summary_tables = 0`)
- `lcovrc.fail-under-lines` (`fail_under_lines = 101` → exit 1)
- `lcovrc.fail-under-branches` (`fail_under_branches = 101`)
- `lcovrc.lcov-list-truncate-max` (`lcov_list_truncate_max = 1`)

Fixture: `compat/fixtures/m0-lcovrc-genhtml-residual3-contract/`

## Oracle relations

| Case | exit | note |
| --- | ---: | --- |
| control | 0 | baseline report |
| compact-summary-tables | 0 | tree delta |
| fail-under-lines | 1 | threshold fail + tree delta |
| fail-under-branches | 0 | tree delta (no branch data to fail) |
| list-truncate-max | 0 | tree delta |

Compared dimensions: exit + filesystem (`exact-v1`).

## Contract effect

- reviewed primary: 474 -> 478
- gaps: 57 -> 53
- product evidence empty; M1 unauthorized
