# M0 CLI Preserve / Fail-Under-Branches Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes three primary plans on one pinned branch capture fixture:

- `command.geninfo.option.preserve`
- `command.geninfo.option.fail-under-branches`
- `command.lcov.option.preserve`

Fixture: `compat/fixtures/m0-cli-preserve-failbr-contract/` (`src/br.c`, `.gcno`, `.gcda`)

## Oracle relations

| Case | exit | effect |
| --- | ---: | --- |
| geninfo control | 0 | no intermediate gcov json |
| geninfo preserve | 0 | retains stable `*.gcov.json.gz` |
| geninfo failbr control (50) | 0 | branch criteria pass |
| geninfo fail-under-branches (101) | 1 | branch criteria fail |
| lcov capture control | 0 | no intermediate gcov json |
| lcov preserve | 0 | retains stable `*.gcov.json.gz` |

Compared dimensions: exit + filesystem (`exact-v1`). Stdout excluded for unstable temp paths.

## Explicit non-claims

Remaining CLI residuals stay open (debug, new-file-as-baseline, external, large-file,
compat-libtool, derive-func-data, geninfo history-script, perl2lcov preserve).

## Contract effect

- reviewed primary: 448 -> 451
- gaps: 83 -> 80
- product evidence empty; M1 unauthorized
