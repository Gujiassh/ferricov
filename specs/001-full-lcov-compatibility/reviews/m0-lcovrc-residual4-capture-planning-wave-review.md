# M0 lcovrc Residual4 + Capture Residual Planning Wave Review

Status: accepted after independent Critical audit

## Scope A — genhtml residual4 (3 keys)

Fixture: `compat/fixtures/m0-lcovrc-genhtml-residual4-contract/`

| Target | boundary | Oracle |
| --- | --- | --- |
| `lcovrc.genhtml-css-file` | `genhtml_css_file = missing.css` | exit 1 |
| `lcovrc.genhtml-date-bins` | `genhtml_date_bins = 1,7,30` | exit 255 without annotate-script |
| `lcovrc.genhtml-show-owner-table` | `genhtml_show_owner_table = 1` | exit 255 without annotate-script |

## Scope B — capture residual (7 keys)

Fixture: `compat/fixtures/m0-lcovrc-capture-residual-contract/`

| Target | boundary | Oracle |
| --- | --- | --- |
| `lcovrc.source-directory` | unused `/work/src` | exit 1 |
| `lcovrc.build-directory` | unused `/work/src` | exit 1 |
| `lcovrc.lcov-tmp-dir` | `/work/tmpx` | exit 2, no out.info |
| `lcovrc.erase-functions` | `main` | exit 1 empty functions |
| `lcovrc.mcdc-coverage` | `1` | exit 255 gcov lacks MC/DC |
| `lcovrc.geninfo-gcov-tool` | `/no/such/gcov` | exit 2 |
| `lcovrc.version-script` | `/work/ver.sh` | exit 0, tree delta |

Compared dimensions: exit + filesystem (`exact-v1`).

## Explicit non-claims

- No Ferricov product evidence; M1 unauthorized.
- Dropped unstable candidates: demangle (exit 127 without c++filt), select-script (no tree delta).
- Remaining open CLI blocked ledger unchanged.

## Contract effect

- reviewed primary: 478 -> 488
- gaps: 53 -> 43
