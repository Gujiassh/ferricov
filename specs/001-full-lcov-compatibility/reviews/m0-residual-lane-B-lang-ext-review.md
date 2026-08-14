# M0 Residual Lane B — Language Extensions Review (draft)

Status: implementer draft (planning-only)  
Lane branch: `m0-residual/lane-B-lang-ext`  
Baseline: `346f86f`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
`product_compatibility_evidence=false`

## Targets

| Target | Status | Suite case (variant) | Control delta |
| --- | --- | --- | --- |
| `lcovrc.c-file-extensions` | sealed (planned) | `…-c-file-extensions` | tree differs |
| `lcovrc.java-file-extensions` | sealed (planned) | `…-java-file-extensions` | tree differs |
| `lcovrc.python-file-extensions` | sealed (planned) | `…-python-file-extensions` | tree differs |
| `lcovrc.perl-file-extensions` | sealed (planned) | `…-perl-file-extensions` | tree differs |
| `lcovrc.rtl-file-extensions` | **blocked** | n/a | no honest exit/filesystem delta |

## Fixture design

Path: `compat/fixtures/m0-residual-b-lang-ext-contract/`

- Crafted multi-SF `input.info` with five sources under `/work/src/`:
  `sample.c`, `Sample.java`, `sample.py`, `sample.pl`, `sample.v`
- Shared multi-config: every case tree includes all variant `.lcovrc` files so
  tree deltas come from `out.info`, not missing configs.
- Command (all cases):

```text
lcov --config-file <cfg> -a input.info -o out.info \
  --filter region,brace,directive \
  --ignore-errors source,unsupported,inconsistent,unused,empty
```

- Control: default language extension tables.
- Variants: set one `*_file_extensions = nomatch` so the corresponding real
  extension is no longer classified as that language.

### Why content changes

Language classification gates filter worklist membership
(`is_language('c|perl|python|java', ...)`) and C-only filters
(brace/directive) plus end-line derivation (`c|java|perl`).

| Variant key | Observable out.info effect vs control |
| --- | --- |
| `c_file_extensions=nomatch` | brace filter skips `sample.c`; C end-line not derived |
| `java_file_extensions=nomatch` | region filter skips `Sample.java`; Java end-line not derived |
| `python_file_extensions=nomatch` | region filter skips `sample.py` |
| `perl_file_extensions=nomatch` | region filter skips `sample.pl`; Perl end-line not derived |

SF path set stays five files (empty-of-DA records may still emit SF); honest
tree deltas are via `out.info` content / `file_tree_sha256`.

## Oracle table (sealed, 2× stable)

| Case | Exit | file_count | file_tree_bytes | file_tree_sha256 (prefix) |
| --- | ---: | ---: | ---: | --- |
| control | 0 | 13 | 1719 | `8acb76b55c6fe7b4…` |
| c-file-extensions | 0 | 13 | 1724 | `891e2b974c985d4e…` |
| java-file-extensions | 0 | 13 | 1731 | `a62539bf8247070a…` |
| python-file-extensions | 0 | 13 | 1733 | `8c44f9e92e72b160…` |
| perl-file-extensions | 0 | 13 | 1731 | `b881b7172a52d08b…` |

Environment: `HOME=/work LANG=C LC_ALL=C TZ=UTC PERL_HASH_SEED=0
PERL_PERTURB_KEYS=0 SOURCE_DATE_EPOCH=946684800 TMPDIR=/work`.  
Comparisons: `exit` + `filesystem` / `exact-v1` only (stderr excluded).  
`reverse_run.exit_code=23` planning convention.

Full pins: `compat/fixtures/m0-residual-b-lang-ext-contract/oracle-observations.json`.

## Blocked: `lcovrc.rtl-file-extensions`

### Evidence

1. In LCOV v2.5 (`lib/lcovutil.pm`), `rtl_file_extensions` is parsed into
   `$rtlExtensions` and applied via `set_extensions('rtl', …)` into
   `%languageExtensions`.
2. Public call sites of `TraceFile::is_language(...)` use only
   `c`, `java`, `perl`, and/or `python` (and combinations). **No**
   `is_language('rtl', …)` call exists in `bin/lcov`, `bin/geninfo`,
   `bin/genhtml`, or `lib/lcovutil.pm`.
3. Probe: same multi-SF fixture + `--filter region,brace,directive` with
   `rtl_file_extensions = nomatch` yields **identical**
   `file_tree_sha256` and exit 0 vs control (see
   `probe-evidence-rtl-blocked.json`).
4. genhtml control vs rtl-restrict differs only in `report/cmd_line`
   (config path/content). Standards forbid cmd_line-only / hollow close.

### Classification

Blocked residual (honest no-delta). Not closed as reviewed+planned suite
binding. Host unbound plan may remain until controller ledger update.

## Deliverables

| Artifact | Path |
| --- | --- |
| Fixture | `compat/fixtures/m0-residual-b-lang-ext-contract/` |
| Suite | `compat/cases/m0-residual-b-lang-ext-contract.json` |
| Validator | `compat/cases/m0_residual_b_lang_ext_contract.py` |
| Unit tests | `compat/cases/test_m0_residual_b_lang_ext_contract.py` |
| Authored wave | `compat/behavior/fragments/authored/m0-residual-b-lang-ext-wave.json` |
| RTL probe | `compat/fixtures/m0-residual-b-lang-ext-contract/probe-evidence-rtl-blocked.json` |

## Non-claims

- No Ferricov product implementation or product compatibility evidence.
- No full `compat/behavior/generate.py` / plan-bindings pin bump (controller).
- No strip of host fragments (controller).
- No push to `test/m0-tf030-exact-numeric-matrix`.

## Local validation

```bash
python3 -m unittest compat.cases.test_m0_residual_b_lang_ext_contract -v
python3 compat/cases/m0_residual_b_lang_ext_contract.py
```
