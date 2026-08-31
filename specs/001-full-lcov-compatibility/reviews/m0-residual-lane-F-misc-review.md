# M0 Residual Lane F — misc residual lcovrc Review

Status: draft for Critical audit  
Lane branch: `m0-residual/lane-F-misc`  
Baseline integration SHA: `346f86f`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

## Scope

Closes 11 residual lcovrc misc keys on fixture
`compat/fixtures/m0-residual-f-misc-contract/`.

| Target | boundary | Oracle |
| --- | --- | --- |
| `lcovrc.check-data-consistency` | `check_data_consistency = 1` on inconsistent.info | exit 1 |
| `lcovrc.demangle-cpp` | `demangle_cpp = c++filt` on mangled FN symbols | exit 0, report tree delta |
| `lcovrc.derive-function-end-line-all-files` | `derive_function_end_line_all_files = 1` on source.py | exit 0, out.info FNL end |
| `lcovrc.expected-message-count` | `expected_message_count = unsupported:0` | exit 1 COUNT |
| `lcovrc.forget-testcase-names` | `forget_testcase_names = 1` on multi-TN input | exit 0, out.info TN collapsed |
| `lcovrc.info-file-pattern` | `info_file_pattern = *.nomatch` on directory | exit 0, empty aggregation |
| `lcovrc.lcov-json-module` | `lcov_json_module = Bogus::NoModule` + `--profile` | exit 2 |
| `lcovrc.select-script` | `select_script = /work/select_none.pm` | exit 0, smaller report tree |
| `lcovrc.split-char` | `split_char = @` with CLI `source,unsupported` | exit 255 |
| `lcovrc.suppress-function-aliases` | `suppress_function_aliases = 1` + merge aliases | exit 0, report tree delta |
| `lcovrc.trivial-function-threshold` | `trivial_function_threshold = 5` + `filter = trivial` | exit 0, empty-body FN erased |

Compared dimensions: exit + filesystem (`exact-v1`).  
Each sealed case re-run ≥2 times with identical `exit_code` and `file_tree_sha256`.

## Oracle differential table

| case | exit | file_count | file_tree_sha256 (prefix) |
| --- | ---: | ---: | --- |
| `m0-residual-f-misc-contract-control` | 0 | 38 | `388f8d0e84277d49…` |
| `m0-residual-f-misc-contract-check-data-consistency` | 1 | 26 | `340b8ac853b3b606…` |
| `m0-residual-f-misc-contract-demangle-cpp` | 0 | 38 | `c9350478ce8c95b8…` |
| `m0-residual-f-misc-contract-derive-function-end-line-all-files` | 0 | 26 | `a7a4c619bd0b47be…` |
| `m0-residual-f-misc-contract-expected-message-count` | 1 | 38 | `12251bbf5e984d42…` |
| `m0-residual-f-misc-contract-forget-testcase-names` | 0 | 26 | `3faabcb9a3c1e858…` |
| `m0-residual-f-misc-contract-info-file-pattern` | 0 | 26 | `1ba2c46c9716bad8…` |
| `m0-residual-f-misc-contract-lcov-json-module` | 2 | 38 | `56876e85e654d8a8…` |
| `m0-residual-f-misc-contract-select-script` | 0 | 34 | `2e2a3a17c8466437…` |
| `m0-residual-f-misc-contract-split-char` | 255 | 25 | `6319664365e019d7…` |
| `m0-residual-f-misc-contract-suppress-function-aliases` | 0 | 38 | `fc1910a346ad925a…` |
| `m0-residual-f-misc-contract-trivial-function-threshold` | 0 | 26 | `cf4d7b6459a2e565…` |

## Notes

- **demangle-cpp**: Oracle image includes `/usr/bin/c++filt`; mangled `_Z7myfunc2v` becomes `myfunc2()` in function HTML.
- **expected-message-count**: uses legal `type:count` form `unsupported:0` against the real unsupported warning emitted by derive-end-line path.
- **split-char**: demonstrates list splitting without claiming product behavior; matching separator form `source@unsupported` remains the legal ignore-errors pairing and is not broken by the key itself. The sealed case intentionally pairs `@` split_char with comma-joined CLI tokens so exit 255 is attributable to the split boundary.
- **select-script**: prior residual waves dropped this key for no tree delta; `select_none.pm` returns 0 for every coverpoint and produces a stable smaller report tree.

## Explicit non-claims

- `product_compatibility_evidence=false`
- M1 unauthorized; no Ferricov product crates modified
- Controller owns host-fragment strip, contract generate/pin, status snapshot, integration push
- Remaining residuals outside this lane stay open

## Tests

- `python3 -m unittest compat.cases.test_m0_residual_f_misc_contract -v`
- `python3 compat/cases/m0_residual_f_misc_contract.py`

## Deliverables

- Fixture: `compat/fixtures/m0-residual-f-misc-contract/`
- Suite: `compat/cases/m0-residual-f-misc-contract.json`
- Validator: `compat/cases/m0_residual_f_misc_contract.py`
- Unit tests: `compat/cases/test_m0_residual_f_misc_contract.py`
- Authored fragment: `compat/behavior/fragments/authored/m0-residual-f-misc-wave.json`
