# M0 Residual Lane E — parallel lcovrc planning wave review

Status: implementer draft for Critical audit  
Baseline: `346f86f`  
Branch: `m0-residual/lane-E-parallel`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

## Scope

Fixture: `compat/fixtures/m0-residual-e-parallel-contract/`  
Suite: `compat/cases/m0-residual-e-parallel-contract.json`  
Wave: `compat/behavior/fragments/authored/m0-residual-e-parallel-wave.json`

Workload: multi-file `lcov -a … --filter blank` (55 info files) with shared multi-config fixture.

| Target | boundary | Oracle |
| --- | --- | --- |
| `lcovrc.parallel` | `parallel = 2` + invalid chunk under filter parallel + `treat_warning_as_error = 1` | exit 1, no `out.info` |
| `lcovrc.lcov-filter-parallel` | `lcov_filter_parallel = 1` enables invalid-chunk format error path | exit 1, no `out.info` |
| `lcovrc.lcov-filter-chunk-size` | `lcov_filter_chunk_size = notanumber` | exit 1, no `out.info` |
| `lcovrc.max-tasks-per-core` | `max_tasks_per_core = $ENV{MISSING_MAX_TASKS_PER_CORE}` | exit 255 usage |
| `lcovrc.fork-fail-timeout` | `fork_fail_timeout = $ENV{MISSING_FORK_FAIL_TIMEOUT}` | exit 255 usage |
| `lcovrc.max-fork-fails` | `max_fork_fails = $ENV{MISSING_MAX_FORK_FAILS}` | exit 255 usage |

Control: `control.lcovrc` → exit 0, writes `out.info`.

Compared dimensions: exit + filesystem (`exact-v1`). Each sealed case re-run ≥2× with identical exit and `file_tree_sha256`.

## Seal notes

- Success-path parallel / max-tasks / fork-timeout values only change scheduling or sleep; no stable exit/filesystem delta on identical multi-config trees.
- `max_tasks_per_core = 0` under genhtml `--parallel` hangs (no stable seal).
- `max_fork_fails = 0` with forced simplify-script child failure still exits 1 via `callback` (same as default max), so not a max-fork-fails differential.
- For the three ENV-expansion cases, the sealed surface is the documented per-key RC `$ENV{NAME}` usage error (exit 255), not wall-clock fork/retry timing.

## Explicit non-claims

- `product_compatibility_evidence=false`
- M1 unauthorized; no product crate changes
- Controller owns host-fragment strip, `generate.py`, plan-bindings pin, integration push

## Tests

```
python3 -m unittest compat.cases.test_m0_residual_e_parallel_contract -v
python3 compat/cases/m0_residual_e_parallel_contract.py
```

## Blocked

None of the six Lane E targets are omitted from the wave.
