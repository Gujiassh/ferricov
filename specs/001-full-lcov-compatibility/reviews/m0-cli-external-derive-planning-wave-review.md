# M0 CLI External / No-External / Derive-Func-Data Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes five primary plans on one pinned external-header capture fixture:

- `command.geninfo.option.external`
- `command.geninfo.option.no-external`
- `command.lcov.option.external`
- `command.lcov.option.no-external`
- `command.lcov.option.derive-func-data`

Fixture: `compat/fixtures/m0-cli-external-derive-contract/`
(`proj/main.c` + `.gcno`/`.gcda`, `external_headers/h.h` outside the capture directory)

## Oracle relations

| Case | exit | effect |
| --- | ---: | --- |
| lcov --external | 0 | out.info includes external SF (tree 890 B) |
| lcov --no-external | 0 | external SF dropped (tree 791 B) |
| geninfo --external | 0 | same tree as lcov --external |
| geninfo --no-external | 0 | same tree as lcov --no-external |
| lcov capture control | 0 | writes out.info |
| lcov --derive-func-data | 1 | geninfo rejects unknown option; no out.info |

Compared dimensions: exit + filesystem (`exact-v1`). Stdout excluded for unstable temp paths.

## Explicit non-claims

- No Ferricov product compatibility evidence (`product_compatibility_evidence=false`).
- Remaining hard CLI residuals stay open (debug, new-file-as-baseline, large-file,
  compat-libtool, geninfo history-script, perl2lcov preserve, and any residual
  without sealed honest Oracle effects).
- `derive-func-data` is sealed as an Oracle failure surface under v2.5 capture
  forwarding, not as successful function-data derivation.

## Contract effect

- reviewed primary: 451 -> 454
- gaps: 80 -> 77
- product evidence empty; M1 unauthorized
