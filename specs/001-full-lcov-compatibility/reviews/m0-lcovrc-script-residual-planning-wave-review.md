# M0 lcovrc Script Residual Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes five residual script-related config keys on residual genhtml inputs:

| Target | boundary | Oracle |
| --- | --- | --- |
| `lcovrc.genhtml-annotate-script` | `/work/ann.sh` | exit 0, large report tree delta |
| `lcovrc.context-script` | missing path | exit 2 |
| `lcovrc.criteria-script` | missing path | exit 1 |
| `lcovrc.simplify-function` | missing path | exit 1 |
| `lcovrc.unreachable-script` | missing path | exit 0, small tree delta |

Fixture: `compat/fixtures/m0-lcovrc-script-residual-contract/`

Compared dimensions: exit + filesystem (`exact-v1`).

## Contract effect

- reviewed primary: 488 -> 493
- gaps: 43 -> 38
- product evidence empty; M1 unauthorized
