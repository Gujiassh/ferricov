# M0 `genhtml` CLI Output Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly six command-owned public options in the dedicated
owner fragment `compat/behavior/fragments/authored/m0-genhtml-cli-output-wave.json`.
The six skeletons were removed from `m0-genhtml-wave1-repair-b.json`, leaving
that repair fragment below its review-size limit; no duplicate plan IDs remain.

- `command.genhtml.option.html-epilog`
- `command.genhtml.option.html-extension`
- `command.genhtml.option.html-gzip`
- `command.genhtml.option.html-prolog`
- `command.genhtml.option.legend`
- `command.genhtml.option.num-spaces`

The retained suite is
`compat/cases/m0-genhtml-cli-output-contract.json`. It has one control case and
one target case per option. Every invocation starts with
`--config-file control.lcovrc`, then adds only the direct CLI option under
review, and writes to `report` from `input.info`. Exact exit, stdout, stderr,
and filesystem comparisons are required.

## Source Contract

Each plan retains the parser registration and two executable consumers from the
pinned LCOV v2.5 `bin/genhtml` source. The consumer lines are:

| Option | Parser | Consumers |
| --- | ---: | --- |
| `html-epilog` | 7259 | 7512, 14167 |
| `html-extension` | 7260 | 7636, 8019 |
| `html-gzip` | 7261 | 7956, 7997 |
| `html-prolog` | 7258 | 7511, 14128 |
| `legend` | 7254 | 12427, 12455 |
| `num-spaces` | 7248 | 8737, 8739 |

The fragment pins the exact source text for all eighteen references and keeps
the source references sorted and direct. Manual/help candidates were removed
from these six plans because executable consumer lines provide the required
semantic boundary.

## Fixture And Launcher

The fixture is
`compat/fixtures/m0-lcovrc-genhtml-contract`. Its focused test locks the
SHA-256 of every fixture file and checks the semantic anchors: the tabbed
`source.c`, `SF:/work/source.c`, `LF:5`/`LH:3`, and the prolog/epilog marker
files. The reference and reverse launchers remain the existing pinned pair:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- environment: `HOME=/work`, `LANG=C`, `LC_ALL=C`, pinned container `PATH`,
  `SOURCE_DATE_EPOCH=946684800`, `TMPDIR=/work`, and `TZ=UTC`
- reference program: `{command}`
- reverse program: `sh`, exiting 23

The launcher JSON hashes are locked by
`compat/cases/test_m0_genhtml_cli_output_contract.py`.

## Oracle Runs

The canonical differential command was run twice with fresh output roots:

```text
cargo run --locked -p ferricov-oracle --bin differential -- \
  compat/cases/m0-genhtml-cli-output-contract.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-output-differential-fixed-a-1786342161

cargo run --locked -p ferricov-oracle --bin differential -- \
  compat/cases/m0-genhtml-cli-output-contract.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-output-differential-fixed-b-1786342522
```

The runner exits non-zero because the intentional reverse candidate differs;
this is expected harness qualification. Both runs produced the following
identical reference facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| control | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329` | 8882 | 26 | 23 |
| `html-epilog` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `5219fd1b0268007258e10fcdd79383a8cd20a57989ea2885dee0dd06da014909` | 8883 | 26 | 23 |
| `html-extension` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `b93f516ef048334d57a7970c4f789a7493b0005ad84049d73fcdbce24cdcd0a4` | 8897 | 26 | 23 |
| `html-gzip` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `0f723523bdd8dd05084b61fca60247c4233218e9ad2a8803f021ff79d4986ed4` | 9203 | 27 | 23 |
| `html-prolog` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `52f1a42e850fdddef67c8ceff50a91c57bcbd9052b63488592fdf1a43c720cb3` | 8883 | 26 | 23 |
| `legend` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `ab1cab67a6387cc9ac018f21b2a5ffe57a16df1cf64e9ce36bd5ef41e34f1c2e` | 8882 | 26 | 23 |
| `num-spaces` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `e5515cfcd4e931f73a279911fdd8b6a0ccda9bb3255af9df0703ef0aee07c031` | 8882 | 26 | 23 |

The stderr SHA shown for every row is the empty-byte digest. The reverse
candidate's stdout and filesystem are intentionally different and are not
used as Ferricov evidence. This is reference/output characterization only; no
Ferricov candidate was run.

## Contract Effect

- public primary plans: `531` (unchanged)
- reviewed primary plans: `419 -> 425`
- fixed source/interaction projections: `421 -> 427`
- explicit M0 planning gaps: `112 -> 106`
- command gaps: `44 -> 38`
- `genhtml` command gaps: `27 -> 21`
- product compatibility evidence: unchanged and empty

M1 parser/model and product implementation remain blocked. This wave closes
planning boundaries only and does not authorize Rust behavior work.

## Verification

- `python3 -m unittest compat.cases.test_m0_genhtml_cli_output_contract` (`9/9`, including
  direct-CLI argv mutation rejection for `xhtml`, `--legend`, and `--num-spaces 2`)
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- `python3 compat/behavior/validate.py --mode m0-ready --skip-regeneration` (expected failure on 106 gaps)
