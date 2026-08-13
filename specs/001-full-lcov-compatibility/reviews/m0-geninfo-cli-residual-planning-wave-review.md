# M0 geninfo CLI Residual Planning Wave Review

Status: accepted after Critical audit rework

## Scope

Closes two geninfo primary plans on a pinned capture fixture:

- `command.geninfo.option.output-filename`
- `command.geninfo.option.no-checksum`

Suite: `compat/cases/m0-geninfo-cli-residual-contract.json`  
Fixture: `compat/fixtures/m0-geninfo-cli-residual-contract/` (`hello.c`, `.gcno`, `.gcda`)

## Comparison contract

Compared dimensions: **exit + filesystem** (`exact-v1`).

Stdout/stderr excluded: geninfo prints unstable temporary data-directory paths
and no approved normalizer exists.

### Pinned Oracle relations

| Case | exit | files | tree bytes | relation |
| --- | ---: | ---: | ---: | --- |
| control (`out.info`) | 0 | 4 | 532 | baseline |
| output-filename (`custom.info`) | 0 | 4 | 532 | same size, different path identity |
| checksum-control | 0 | 4 | 601 | larger content than default |
| no-checksum | 0 | 4 | 532 | tree identity equals control; smaller than checksum control |

## Explicit non-claims

debug, history-script, preserve, external, large-file, compat-libtool,
fail-under-branches remain open on this fixture.

## Contract effect

- reviewed primary: 444 -> 446
- gaps: 87 -> 85
- product evidence empty; M1 unauthorized

## Verification

```text
python3 -m unittest compat.cases.test_m0_geninfo_cli_residual_contract
python3 compat/behavior/validate.py --mode current
python3 compat/status/generate_m0_status.py
```
