# M0 `genhtml` CLI Summary Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly three command-owned public options in the dedicated
owner fragment `compat/behavior/fragments/authored/m0-genhtml-cli-summary-wave.json`.
The residual skeletons were removed from the existing wave1 repair fragments.

- `command.genhtml.option.fail-under-branches`
- `command.genhtml.option.show-zero-columns`
- `command.genhtml.option.sort-tables`

The retained suite is `compat/cases/m0-genhtml-cli-summary-contract.json`. It
has one control case and one direct-option target case per option. Each case uses
the shared `--config-file control.lcovrc` fixture and exact exit, stdout, stderr,
and filesystem comparisons.

A trial `--debug` case was deliberately excluded: its 47-byte stderr has stable
length but different SHA-256 values across clean runs because the diagnostic
payload contains run-specific temporary-path text. No new normalizer is added
for that unresolved nondeterminism.

## Source Contract

Each retained plan pins the parser registration and executable consumer lines
from LCOV v2.5:

| Option | Source references |
| --- | --- |
| `fail-under-branches` | `lib/lcovutil.pm:1259`, `lib/lcovutil.pm:3167`, `lib/lcovutil.pm:7173` |
| `show-zero-columns` | `bin/genhtml:7087`, `bin/genhtml:7243`, `bin/genhtml:12480` |
| `sort-tables` | `bin/genhtml:7264`, `bin/genhtml:7336`, `bin/genhtml:7537` |

The focused suite locks the exact source text at every referenced line.

## Fixture And Launcher

The fixture is the existing `compat/fixtures/m0-lcovrc-genhtml-contract`; its
recursive SHA-256 and the `SF:/work/source.c` / `LF:5` semantic anchors remain
locked. The existing pinned launcher pair is unchanged:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- environment: `HOME=/work`, `LANG=C`, `LC_ALL=C`, pinned container `PATH`,
  `SOURCE_DATE_EPOCH=946684800`, `TMPDIR=/work`, and `TZ=UTC`
- reference program: `{command}`
- reverse program: `sh`, exiting 23

## Oracle Runs

The canonical differential command ran twice with fresh output roots:

```text
cargo run --locked -p ferricov-oracle --bin differential -- \
  /tmp/ferricov-genhtml-cli-next-suite.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-next-run-a

cargo run --locked -p ferricov-oracle --bin differential -- \
  /tmp/ferricov-genhtml-cli-next-suite.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-next-run-b
```

The runner exits non-zero only because the intentional reverse candidate differs;
this is expected harness qualification. Both runs produced identical
reference/output characterization facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329` | 8882 | 28 | 0 | 23 |
| `fail-under-branches` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `d22d7a069757268655feb255ba3175217037acc3df9cc80918f12514b8214737` | 8882 | 28 | 0 | 23 |
| `show-zero-columns` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `f4d6a1edcb7c762f50c07f754de5a8bcd93b5e9e092e109260d7eabf12911566` | 8882 | 28 | 0 | 23 |
| `sort-tables` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `2e9ca37edf3b5f7fa6c31d15efc0ffa5ba535ee551787fdcba3c42b7843ba6c6` | 8882 | 28 | 0 | 23 |

Every reference process reported no timeout, reaped its child, and removed its
container. These are Oracle facts only; no Ferricov candidate was run and no
product compatibility evidence is claimed.

## Contract Effect

- public primary plans: `531` (unchanged)
- reviewed primary plans: `431 -> 434`
- fixed source/interaction projections: `433 -> 436`
- explicit M0 planning gaps: `100 -> 97`
- command gaps: `32 -> 29`
- `genhtml` command gaps: `15 -> 12`
- product compatibility evidence: unchanged and empty

M1 parser/model and product implementation remain blocked. This wave closes
planning boundaries only and does not authorize Rust behavior work.

## Verification

- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_summary_contract` (7 tests)
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- `python3 compat/behavior/validate.py --mode m0-ready --skip-regeneration` (expected failure on 97 gaps)
- `python3 compat/verify.py --skip-oracle`
