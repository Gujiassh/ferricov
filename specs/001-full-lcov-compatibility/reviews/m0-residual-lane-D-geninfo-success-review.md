# M0 Residual Lane D — geninfo success-path lcovrc Review (draft)

Status: implementer draft for Critical lane audit  
Lane branch: `m0-residual/lane-D-geninfo-success`  
Baseline integration SHA: `346f86f`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

## Lane

- Letter: **D**
- Fixture: `compat/fixtures/m0-residual-d-geninfo-success-contract/`
- Suite: `compat/cases/m0-residual-d-geninfo-success-contract.json`
- Authored wave: `compat/behavior/fragments/authored/m0-residual-d-geninfo-success-wave.json`

### Closed targets (6)

| Target | Boundary | Differential |
| --- | --- | --- |
| `lcovrc.geninfo-auto-base` | `geninfo_auto_base = 0` vs `1` | filesystem (SF path rewrite on multi-dir + intermediate-text gcov) |
| `lcovrc.geninfo-capture-all` | `geninfo_capture_all = 1` vs control `0` | filesystem (adds lone `.gcno` source) |
| `lcovrc.geninfo-compat` | `geninfo_compat = not_a_mode=on` | exit 255 vs control 0 (unknown mode error surface) |
| `lcovrc.geninfo-follow-symlinks` | `geninfo_follow_symlinks = 1` vs control `0` | filesystem (follows `src/via` into `hidden/`) |
| `lcovrc.geninfo-unexecuted-blocks` | `geninfo_unexecuted_blocks = 1` vs `0` | filesystem (DA count adjusted for unexecuted_block) |
| `lcovrc.no-exception-branch` | `no_exception_branch = 1` vs `0` | filesystem (exception BRDA dropped under `--branch-coverage`) |

### Blocked targets (3) — evidence

| Target | Why blocked on Oracle `b02cc645…` |
| --- | --- |
| `lcovrc.geninfo-compat-libtool` | Libtool path strip uses `s/\.libs$//` on `split_filename` dirs that retain a trailing `/` (`/path/.libs/`), so the substitution never matches. Control `geninfo_compat_libtool=0` and `=1` produce identical SF paths and exit codes on intermediate and graphfile paths. Same class of no-delta as CLI `compat-libtool` residual. |
| `lcovrc.geninfo-gcov-all-blocks` | `-a`/`--all-blocks` is only pushed when branch coverage is on **and** intermediate format is off. Gcov 12.2 always selects intermediate (json); forcing `geninfo_intermediate=0` is upgraded back to intermediate with an unsupported warning. Classic non-intermediate path also rejects gcc-12 `.gcno` format (`Overlong record`). Net: key is a no-op for filesystem/exit on this Oracle. |
| `lcovrc.geninfo-interval-update` | Only changes progress `intervalLength` (stdout) and `--profile` interval field. Stdout embeds unstable `geninfo_datXXXX` temp paths; profile JSON embeds wall-clock timings. `out.info` content is identical across `5` vs `80`. No stable exact-v1 dimension. |

## Oracle differential table

| Case id | exit | file_count | file_tree_bytes | file_tree_sha256 (prefix) | vs paired control |
| --- | ---: | ---: | ---: | --- | --- |
| `…-control` | 0 | 31 | 4978 | `b1244b465ff64b6d…` | — |
| `…-capture-all` | 0 | 31 | 5067 | `fa8d850bcac6359e…` | tree delta |
| `…-follow-symlinks` | 0 | 31 | 5068 | `64e6444094e368c3…` | tree delta |
| `…-compat` | 255 | 30 | 4891 | `bfef66597384a4ef…` | exit + tree (no out.info) |
| `…-auto-base-on` | 0 | 31 | 4985 | `cfa6b1fb301f7f0b…` | pair control for auto-base |
| `…-auto-base` | 0 | 31 | 4989 | `4410a8cc58228911…` | tree delta vs auto-base-on |
| `…-unexecuted-blocks-off` | 0 | 31 | 4981 | `22e1561243166cd4…` | pair control for unexecuted |
| `…-unexecuted-blocks` | 0 | 31 | 4981 | `cfd3fa447c378ee4…` | tree delta (same size, different content) |
| `…-exception-control` | 0 | 31 | 5149 | `31667c516c63032c…` | pair control for no-exception |
| `…-no-exception-branch` | 0 | 31 | 5093 | `8787f0a23ae9aeef…` | tree delta |

Compared dimensions: **exit** + **filesystem** (`exact-v1`). Stdout/stderr recorded in observations but not compared (temp-path / filter notes).

Seal environment: `HOME=/work LANG=C LC_ALL=C TZ=UTC PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0 SOURCE_DATE_EPOCH=946684800 TMPDIR=/work`. Each case re-run ≥2× with identical `exit_code` and `file_tree_sha256`. `reverse_run.exit_code=23` planning convention.

Shared multi-config fixture: all variant `.lcovrc` files (and both fake-gcov helpers) are present in every case so tree deltas come from outputs/exit, not missing config files.

## Plan binding

| Target | Plan id | review_status | evidence_status | suite_cases |
| --- | --- | --- | --- | --- |
| `lcovrc.geninfo-auto-base` | `case.acceptance.lcovrc.geninfo-auto-base` | reviewed | planned | auto-base + auto-base-on |
| `lcovrc.geninfo-capture-all` | `case.acceptance.lcovrc.geninfo-capture-all` | reviewed | planned | control + capture-all |
| `lcovrc.geninfo-compat` | `case.acceptance.lcovrc.geninfo-compat` | reviewed | planned | control + compat |
| `lcovrc.geninfo-follow-symlinks` | `case.acceptance.lcovrc.geninfo-follow-symlinks` | reviewed | planned | control + follow-symlinks |
| `lcovrc.geninfo-unexecuted-blocks` | `case.acceptance.lcovrc.geninfo-unexecuted-blocks` | reviewed | planned | unexecuted-blocks-off + unexecuted-blocks |
| `lcovrc.no-exception-branch` | `case.acceptance.lcovrc.no-exception-branch` | reviewed | planned | exception-control + no-exception-branch |

Source references inventory-aligned (`lcovrc` / `lib/lcovutil.pm`, repository `lcov-v2.5`).

## Fixture notes

- **capture-all / follow**: real gcc-12 coverage under `src/` (+ `hidden/` via relative symlink `src/via`).
- **auto-base**: `fake-gcov-text` emits intermediate-text `file:src/hello.c` without json `current_working_directory`, so `find_base_from_source` runs; `auto_base=0` keeps base at `ab/obj` (`SF:…/obj/src/hello.c`) while `=1` walks to `ab` (`SF:…/ab/src/hello.c`).
- **unexecuted-blocks**: `fake-gcov-json` emits stable JSON with `unexecuted_block: true` and `count: 5` on a non-branch line (real gcov 12 rarely yields empty branches with nonzero unexecuted counts when `-b` is implied by function coverage).
- **no-exception-branch**: real C++ `throw`/`catch` under `ex/` with `--branch-coverage`.
- **geninfo-compat**: invalid mode string; honest error-surface seal (exit 255).

## Non-claims

- `product_compatibility_evidence=false` on suite observations and plans
- No Ferricov product crate changes; M1 remains unauthorized
- No full `compat/behavior/generate.py` / plan-bindings pin update (controller merge only)
- Pre-existing host fragments still own the case ids until controller strip:
  - `m0-lcovrc-wave1-repair-b.json` (auto-base, capture-all, compat, compat-libtool, follow-symlinks, gcov-all-blocks)
  - `m0-lcovrc-blocked-wave.json` (interval-update)
  - `m0-lcovrc-capture-wave.json` (unexecuted-blocks)
  - `m0-lcovrc-filter-wave.json` (no-exception-branch)
- Three blocked targets remain open (see table)

## Tests

```bash
python3 -m unittest compat.cases.test_m0_residual_d_geninfo_success_contract -v
python3 compat/cases/m0_residual_d_geninfo_success_contract.py
```

Covers: production suite validator accept, argv/id mutations reject, oracle pins + control/variant relation, fixture content hashes, plans reviewed/planned with suite_cases.

## Risks

1. **Fake gcov helpers**: auto-base and unexecuted-blocks use fixture-local gcov stand-ins to reach code paths that modern gcov-12 intermediate JSON short-circuits. Acceptable for config-key boundary sealing; product reimplementation must match the key semantics, not the helper provenance.
2. **Absolute SF paths `/work/...`**: Oracle seal mounts fixture at `/work`; re-seals must keep the same mount layout and recompile coverage objects inside that layout.
3. **geninfo-compat is error-surface**: seals parse/reject of unknown modes, not a success-path libtool/hammer/split_crc tree delta (those remain no-delta under intermediate JSON).
4. **Host fragment collision**: full contract regenerate will fail until controller strips the six closed case ids from their current host fragments.

## Controller handoff

Merge lane branch → strip host fragments for the six closed case ids → `generate.py` → pin `EXPECTED_PLAN_BINDINGS_SHA256` → status snapshot → Critical merge audit → push integration. Leave three blocked ids on the residual ledger.
