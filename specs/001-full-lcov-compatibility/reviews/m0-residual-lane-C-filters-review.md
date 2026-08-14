# M0 Residual Lane C — lcovrc Filters Review (draft)

Status: implementer draft for Critical lane audit  
Lane branch: `m0-residual/lane-C-filters`  
Baseline integration SHA: `346f86f`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

## Lane

- Letter: **C**
- Targets:
  - `lcovrc.filter-bitwise-conditional`
  - `lcovrc.filter-blank-aggressive`
  - `lcovrc.filter-lookahead`
- Fixture: `compat/fixtures/m0-residual-c-filters-contract/`
- Suite: `compat/cases/m0-residual-c-filters-contract.json`
- Authored wave: `compat/behavior/fragments/authored/m0-residual-c-filters-wave.json`

## Theme

Crafted C source (`src/edges.c`) with blank / bitwise / multi-line-call edges plus a hand-crafted
`src/edges.info` that injects BRDA/DA coverpoints on those edges. Each case runs:

```text
lcov --config-file <variant>.lcovrc --filter branch,blank --branch-coverage \
  -a src/edges.info -o out.info --ignore-errors source,unsupported,empty,...
```

Shared multi-config fixture: all four `.lcovrc` files are present in every case so tree deltas
come from `out.info` content, not missing config files.

## Oracle differential table

| Case id | Boundary | exit | file_count | file_tree_bytes | file_tree_sha256 (prefix) | vs control |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `…-control` | `filter_lookahead=10`, `filter_bitwise_conditional=0`, `filter_blank_aggressive=0` | 0 | 7 | 1820 | `16c8f1fe5dba5bb1…` | — |
| `…-bitwise-conditional` | `filter_bitwise_conditional=1` | 0 | 7 | 1860 | `a394c7234bb2a4fd…` | tree delta (keeps BRDA:10) |
| `…-blank-aggressive` | `filter_blank_aggressive=1` | 0 | 7 | 1812 | `cd42daeefb50bba7…` | tree delta (drops DA:21) |
| `…-lookahead` | `filter_lookahead=2` | 0 | 7 | 1860 | `1668a764b690c496…` | tree delta (keeps BRDA:15) |

Compared dimensions: **exit** + **filesystem** (`exact-v1`). Stdout/stderr recorded but not compared
(control/blank emit stable empty-branch warnings).

Seal environment: `HOME=/work LANG=C LC_ALL=C TZ=UTC PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0
SOURCE_DATE_EPOCH=946684800 TMPDIR=/work`. Each case re-run ≥2× with identical exit and tree hash.
`reverse_run.exit_code=23` planning convention.

## Plan binding

| Target | Plan id | review_status | evidence_status | suite_cases |
| --- | --- | --- | --- | --- |
| `lcovrc.filter-bitwise-conditional` | `case.acceptance.lcovrc.filter-bitwise-conditional` | reviewed | planned | control + bitwise-conditional |
| `lcovrc.filter-blank-aggressive` | `case.acceptance.lcovrc.filter-blank-aggressive` | reviewed | planned | control + blank-aggressive |
| `lcovrc.filter-lookahead` | `case.acceptance.lcovrc.filter-lookahead` | reviewed | planned | control + lookahead |

Source references inventory-aligned (`lcovrc` + `lib/lcovutil.pm`, repository `lcov-v2.5`).

## Non-claims

- `product_compatibility_evidence=false` on suite observations and plans
- No Ferricov product crate changes; M1 remains unauthorized
- No full `compat/behavior/generate.py` / plan-bindings pin update (controller merge only)
- Pre-existing host fragment `m0-lcovrc-wave1-repair-a.json` still owns the case ids until controller strip

## Tests

```bash
python3 -m unittest compat.cases.test_m0_residual_c_filters_contract -v
python3 compat/cases/m0_residual_c_filters_contract.py
```

Covers: production suite validator accept, argv/id mutations reject, oracle pins + control/variant
relation, fixture content hashes, plans reviewed/planned with suite_cases.

## Risks

1. **Hand-crafted `.info`**: BRDA/DA edges are injected to hit filter heuristics; not a pure gcov
   capture. Acceptable for config-key boundary sealing; product reimplementation must match filter
   semantics, not this exact fixture provenance.
2. **Path absolute `SF:/work/src/edges.c`**: Oracle seal mounts fixture at `/work`; re-seals must
   keep the same mount layout.
3. **Empty-branch stderr**: Control and blank-aggressive still warn about empty branch coverpoints;
   excluded from comparison dimensions deliberately.
4. **Host fragment collision**: Full contract regenerate will fail until controller strips these
   three case ids from `m0-lcovrc-wave1-repair-a.json`.

## Controller handoff

Merge lane branch → strip host fragments for the three case ids → `generate.py` → pin
`EXPECTED_PLAN_BINDINGS_SHA256` → status snapshot → Critical merge audit → push integration.
