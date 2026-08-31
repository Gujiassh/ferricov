# M0 CLI Genhtml Hard Residual Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes two primary plans on residual genhtml inputs:

- `command.genhtml.option.debug`
- `command.genhtml.option.new-file-as-baseline`

Fixture: `compat/fixtures/m0-cli-genhtml-hard2-contract/`
(`control.lcovrc`, `input.info`, `input2.info`, `source.c`)

## Oracle relations

| Case | exit | effect |
| --- | ---: | --- |
| debug control | 0 | report without `--debug` in cmd_line |
| `--debug` | 0 | report/cmd_line includes `--debug` (tree 46795 vs 46787) |
| baseline control | 0 | differential report without new-file-as-baseline |
| `--new-file-as-baseline` | 0 | distinct sealed report tree (55217 vs 55194) |

Compared dimensions: exit + filesystem (`exact-v1`).
Stderr excluded for debug (DEBUG memory counters unstable under exact-v1).

## Explicit non-claims

- No Ferricov product compatibility evidence.
- Remaining open CLI residuals after this wave:
  - `command.geninfo.option.history-script` (no filesystem delta with minimal history script)
  - `command.geninfo.option.compat-libtool` / `command.lcov.option.compat-libtool` (default libtool mode already ON; no distinct oracle tree)
  - `command.perl2lcov.option.preserve` (needs Devel::Cover DB fixture not yet sealed)

## Contract effect

- reviewed primary: 457 -> 459
- gaps: 74 -> 72
- product evidence empty; M1 unauthorized
