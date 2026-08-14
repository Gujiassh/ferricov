# M0 Residual Lane A — CLI hard review (draft)

Status: implementer draft for controller merge  
Lane branch: `m0-residual/lane-A-cli-hard`  
Baseline integration SHA: `346f86f`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
`product_compatibility_evidence=false`

## Closed targets (1)

| Target | Suite cases | Control tree | Variant tree | Delta |
| --- | --- | --- | --- | --- |
| `command.geninfo.option.history-script` | `...-geninfo-history-control` / `...-geninfo-history-script` | exit 0, 14 files, `fda604f45bc9a729f6c80e3bf32396ef3f9ec1a11eb014c8daf5b11d56148dd3` | exit 0, 15 files, `5725a1e6865cf7ad9c7cfd3622f6fcd047c9aa459f7f7deb6840fd7fad33e070` | filesystem: variant retains stable `history.loaded` marker written by `HistoryProbe.pm` constructor |

Comparisons: `exit` + `filesystem` (`exact-v1`). Stdout excluded (not sealed). Two Oracle re-runs produced identical tree hashes.

Fixture: `compat/fixtures/m0-residual-a-cli-hard-contract/` (multi-gcda `src/{a,b,c,main}.*` + `HistoryProbe.pm`).

## BLOCKED targets (3)

### `command.geninfo.option.compat-libtool` / `command.lcov.option.compat-libtool`

**Reason:** No stable exit or filesystem differential between `--compat-libtool`, `--no-compat-libtool`, and default on Oracle GCC 12 intermediate JSON capture.

Probe notes (Oracle image above, 2026-08-14):

1. Compiled classic libtool layout (`hello.c` in parent, objects/`*.gcda`/`*.gcno` under `.libs/`).
2. `geninfo .libs --compat-libtool` and `geninfo .libs --no-compat-libtool` both wrote identical `out.info` (same `SF:` absolute path, same tree hash).
3. Root cause in Oracle `geninfo` intermediate path: when gcov JSON supplies `current_working_directory`, libtool strip is skipped. When JSON basedir is absent, `split_filename` yields a directory with trailing `/`, so `$base =~ s/\.libs$//` does not match `.libs/`.
4. `lcov --capture` forwards the same geninfo capture path; same no-delta result.
5. Forced text-intermediate gcov wrapper and `--initial` graph-only paths also failed to produce an on/off SF rewrite under auto-base off.

Honest policy: leave unbound; do not hollow-close with argv-only plans.

### `command.perl2lcov.option.preserve`

**Reason:** Only filesystem effect found is retention of an empty parallel-filter temp directory with a **randomized** `filter_datXXXX` name under `lcov_tmp_dir`, which is unstable across re-runs and cannot seal under `exact-v1` filesystem comparison.

Probe notes:

1. Minimal Devel::Cover DB (existing `m0-perl2lcov-contract` and a 60-module synthetic DB) with/without `--preserve` produce identical trees when no parallel filter temp is created.
2. With `LCOV_FORCE_PARALLEL=1`, `--filter branch`, `--parallel 2`, and `lcov_tmp_dir` fixed: control removes the temp dir; preserve keeps `filter_dat*` empty dirs whose suffix changes every run (`filter_datgOz2`, `filter_datffeI`, `filter_datIlup`, …).
3. Exit/stdout/stderr are identical (exit 0) for control vs preserve on that path.
4. No stable-named intermediate artifact analogous to geninfo `*.gcov.json.gz` was observed for perl2lcov.

Honest policy: leave unbound until a stable intermediate retention surface exists.

## Non-claims

- No Ferricov product implementation or product evidence.
- No full behavior-contract regenerate / plan-bindings pin bump (controller-owned).
- No strip of host fragments (controller-owned).

## Local validation

```bash
python3 -m unittest compat.cases.test_m0_residual_a_cli_hard_contract -v
python3 compat/cases/m0_residual_a_cli_hard_contract.py
```

## Deliverable paths

- Fixture: `compat/fixtures/m0-residual-a-cli-hard-contract/`
- Suite: `compat/cases/m0-residual-a-cli-hard-contract.json`
- Module: `compat/cases/m0_residual_a_cli_hard_contract.py`
- Tests: `compat/cases/test_m0_residual_a_cli_hard_contract.py`
- Wave: `compat/behavior/fragments/authored/m0-residual-a-cli-hard-wave.json`
- Review: this file
