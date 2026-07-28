# M0 Configuration Contract Review

## Decision

Accepted as Critical Oracle qualification and behavior-planning evidence. The
slice adds 22 executable configuration cases to the retained correctness
baseline and reviews six additional public primary targets. It does not execute
a Ferricov candidate, claim product compatibility, or unlock M1.

## Semantic Oracle

Every configuration case must preserve all of these invariants:

1. The exact process exit code matches the authored case expectation.
2. The `branches....:` summary line is present or absent as declared.
3. Stderr is empty where declared and contains every required diagnostic
   fragment otherwise.
4. Raw stdout, stderr, filesystem, timeout, cleanup, image, executable, user,
   and effective-environment evidence remains retained and hash-bound.
5. `$HOME/.lcovrc` wins over `$LCOV_HOME/etc/lcovrc`; LCOV_HOME is used only
   when HOME does not select a file; explicit files bypass discovery.
6. Suite-level `{workdir}` placeholders resolve before execution and validation.
7. All behavior-plan bindings remain `planned` with empty evidence arrays.

## Reviewed Scope

| Suite | Cases | Purpose |
| --- | ---: | --- |
| `m0-config-contract-base` | 18 | Explicit files, order, flags, RC, includes, discovery controls, and failures |
| `m0-config-contract-env` | 2 | Single and multiple environment expansion |
| `m0-config-contract-home-first` | 1 | HOME precedence over LCOV_HOME |
| `m0-config-contract-lcov-home` | 1 | LCOV_HOME fallback |
| **Total** | **22** | **Exact raw Oracle observations** |

The aggregate correctness contract contains seven suites and 148 cases: the
existing 126 CLI cases plus these 22 configuration cases. Eight authored
configuration-semantic planning slices contain 67 exact bindings and cover
`branch_coverage`, `config_file`, `--branch-coverage`, `--config-file`,
`--ignore-errors`, `--no-branch-coverage`, `--rc`, and `--summary`. Six of those
targets advance from unreviewed to reviewed primary coverage.

## Evidence

Two independent 148-case captures against immutable image
`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
passed semantic replay. The 22-case exit/branch/stderr signature was identical
across both captures. Replay adds no configuration normalization.

The first attempted capture exposed a runner defect: suite-level HOME and
LCOV_HOME values retained literal `{workdir}` tokens. The runner and validator
now resolve suite overrides through the same placeholder rule, with a focused
Rust regression test. The failed temporary capture is not retained as accepted
evidence.

The Oracle also confirms that a relative include closes the parent filehandle,
emits `readline() on closed filehandle HANDLE`, and prevents later parent
assignments from applying. The diagnostics contract records this pinned defect.

## Risk Review

| Area | Result | Evidence |
| --- | --- | --- |
| Goal alignment | pass | Configuration discovery and precedence move from prose to executable M0 cases without starting implementation. |
| User-visible timing | not applicable | No Ferricov runtime exists or changes in this slice. |
| Architecture and boundaries | pass | CLI generation, configuration generation, aggregation, raw capture, and semantic validation remain separate responsibilities. |
| Data and evidence contracts | pass | Suite schema is unchanged; seven suite hashes, 148 unique IDs, immutable identities, and false product evidence are fail-closed. |
| Implementation quality | pass | The new generator is separate from the existing 1,943-line CLI generator; focused mutation tests cover partition, environment, links, and semantics. |
| Verification and evolution | pass | Two captures, semantic replay, raw validation, reverse semantic mutations, Rust tests, behavior tests, and current-mode validation pass. |

## Residual Risk

The 22 cases cover configuration discovery and precedence foundations, not all
153 public `lcovrc` entries or every consumer. M0 retains 462 public primary
review gaps. Ferricov product evidence remains zero, and M1 stays gated.
