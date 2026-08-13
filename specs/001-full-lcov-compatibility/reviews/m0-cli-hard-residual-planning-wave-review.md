# M0 CLI Hard Residual Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes three primary plans on one pinned hello capture fixture:

- `command.geninfo.option.large-file`
- `command.lcov.option.large-file`
- `command.geninfo.option.debug`

Fixture: `compat/fixtures/m0-cli-hard-residual-contract/` (`src/hello.c`, `.gcno`, `.gcda`)

## Oracle relations

| Case | exit | effect |
| --- | ---: | --- |
| geninfo control | 0 | writes out.info |
| geninfo `--large-file (` | 2 | invalid regexp; no out.info |
| lcov capture control | 0 | writes out.info |
| lcov `--large-file (` | 2 | invalid regexp; no out.info |
| geninfo debug control | 0 | empty stderr; same tree as debug |
| geninfo `--debug` | 0 | non-empty stable DEBUG stderr; same tree |

Compared dimensions:
- large-file cases: exit + filesystem (`exact-v1`)
- debug cases: exit + stderr + filesystem (`exact-v1`); stdout excluded

## Explicit non-claims

- No Ferricov product compatibility evidence.
- Remaining open CLI residuals: genhtml debug, genhtml new-file-as-baseline,
  geninfo history-script, geninfo/lcov compat-libtool, perl2lcov preserve.
- large-file is sealed as invalid-regexp failure surface, not as parallel
  large-file scheduling success path.
- compat-libtool remains open because default libtool mode is already ON and
  current fixtures did not produce a distinct filesystem oracle delta.

## Contract effect

- reviewed primary: 454 -> 457
- gaps: 77 -> 74
- product evidence empty; M1 unauthorized
