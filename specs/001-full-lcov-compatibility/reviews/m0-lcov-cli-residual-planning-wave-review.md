# M0 lcov CLI Residual Planning Wave Review

Status: accepted after independent Critical re-audit

## Scope

Closes two lcov primary plans:

- `command.lcov.option.zerocounters` — cli-option boundary `--zerocounters`
- `command.lcov.option.fail-under-branches` — cli-option boundary `--fail-under-branches 101`

Suite: `compat/cases/m0-lcov-cli-residual-contract.json`  
Fixture: full tree under `compat/fixtures/m0-lcov-cli-residual-contract/`:

- `src/hello.c`, `src/hello.gcno`, `src/hello.gcda`
- `branch/base.info`, `branch/br.c`

Oracle worktree = full fixture minus `oracle-observations.json`.

## Oracle relations

| Case | exit | includes `src/hello.gcda` | Effect |
| --- | ---: | --- | --- |
| zero-control (`--version`) | 0 | yes | non-destructive control |
| zerocounters | 0 | **no** | deletes coverage data files under `src/` |
| failbr-control (threshold 50) | 0 | yes (untouched) | summary passes |
| fail-under-branches (threshold 101) | 1 | yes (untouched) | branch criteria fail |

Compared dims: zerocounters exit+filesystem; fail-under-branches all four exact-v1.

## Explicit non-claims

compat-libtool, derive-func-data, external, large-file, preserve remain open.

## Contract effect

- reviewed primary: 446 -> 448
- gaps: 85 -> 83
- product evidence empty; M1 unauthorized
