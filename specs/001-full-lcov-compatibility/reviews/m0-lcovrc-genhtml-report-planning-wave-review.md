# M0 lcovrc genhtml Report Planning Wave Review

Status: accepted as bounded Oracle-reference planning evidence for two primary plans

## Scope

This wave closes the two previously unbound source-bound `lcovrc` report plans:

- `merge_function_aliases`
- `num_context_lines`

The existing authored fragment `m0-lcovrc-report-wave.json` now carries reviewed
primary plans with exact suite bindings. The upstream `lcovrc` spelling
`merge_function_aliasess` at line 216 is intentionally not bound; it is a
separate not-applicable inventory candidate.

## Pinned Source Contract

`merge_function_aliases` binds the registration at `bin/genhtml:7192` and
its observable consumers at `5243`, `5262`, `5989`, `13912`, and `13998`.
The alias fixture contains two `FNL`/`FNA` aliases sharing one function
location, with one hit and one zero-hit alias. The control and target use the
same baseline/current tracefiles and unified diff; only the config assignment
changes.

`num_context_lines` binds `bin/genhtml:7206`, `lcovrc:365`, and the context
expansion consumers at `bin/genhtml:4453` and `4479`. Its fixture uses a
baseline/current tracefile pair, an absolute-path no-change diff, a short
`select.pm` callback that selects line 5, and source text with fifteen lines. The control sets
`num_context_lines = 0`; the target sets `num_context_lines = 5`.

All four invocations also pass `--baseline-date 2000-01-01`. This is a
reproducibility control, not a third behavior dimension: `bin/genhtml:7229`
registers the option, and `bin/genhtml:7479-7496` otherwise derives the
baseline date from the copied baseline file's mtime.

## Oracle Envelope

Both suites use the pinned launcher pair with:

- image `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- `SOURCE_DATE_EPOCH=946684800`, `PERL_HASH_SEED=0`, and
  `PERL_PERTURB_KEYS=0`
- `TZ=UTC`, `LANG=C`, `LC_ALL=C`
- `TMPDIR=/work`, `HOME=/work`, and the pinned container `PATH`

The report-wave-only reference executable is `{command}`. The reverse launcher
is a distinct `sh` command that exits 23. The launcher pair pins Perl hash
iteration without changing the shared `genhtml` launcher. It is harness
qualification only; no Ferricov candidate was run and all plan evidence arrays
remain empty with `evidence_status=planned`.

## Reference Observations

The canonical differential runner recorded exit 0 for all four reference
cases. Raw reference artifacts remain in the temporary runner output; the
stable fixture and binding facts are committed in the suite tests.

| Case | stdout SHA-256 | stdout bytes | stderr SHA-256 | file-tree SHA-256 | tree bytes | output files |
| --- | --- | ---: | --- | --- | ---: | ---: |
| alias control | `575b236ae4b4bd9f76d7fed8c1ec6987e5009a6452aea0107618ae5fee8c7a31` | 669 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `01fa263783ea756d157a8abddd29eb8ff82931c594a127dd26f3cfb2579f2e47` | 6927 | 19 |
| alias merge | `614c16b0e288d4ceaec67c585696c98c2163b54e4b78ee18b4457a1ce0869bf6` | 633 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `020862f9e2548f84c6002d13517174948834e2a9c2bf5cb04e16f2d1082970a3` | 6927 | 19 |
| context 0 | `e9d622bec746f21e7e54cd92c267240e0cb1bf2d54eb14125fb2adae8c4109ff` | 532 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `1b8b6dacdda6071e13d6653088ade88858bdf56c357cbe4d05d280a3eaaf9edc` | 6485 | 18 |
| context 5 | `011bef1851f2d8c6fc30cfb6c064baa055b1eadada1b27ee716d8b38c2d3b2a5` | 569 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `28d69dfa47141569947aae9a49c6385ea1c7d7439b9b48369a913e7d33b16fe1` | 6485 | 18 |

The alias and context target deltas are distinct from their controls. The
context target also increases reference stdout from 532 to 569 bytes, which
matches the expanded differential source selection.

Two independent clean runner invocations produced the same reference exit,
stdout, stderr, file-tree hashes, tree bytes, and output-file counts for every
case. The reverse candidate exited 23 in each run.

## Contract Effect

- reviewed primary plans: `417 -> 419`
- fixed source/interaction projections: `419 -> 421`
- explicit M0 behavior gaps: `114 -> 112`
- product compatibility evidence: unchanged and empty

## Verification

- `python3 -m unittest compat.cases.test_m0_lcovrc_genhtml_report_contract`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- pinned Oracle differential runs for both suites; all four reference cases exit 0
- `m0-ready` remains expected to fail on 112 gaps

This slice does not authorize Rust parser/model/ops implementation, does not
claim Ferricov compatibility, and keeps M1 gated.
