# M0 `genhtml` CLI Metric/Layout Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly three command-owned public options in the dedicated
owner fragment `compat/behavior/fragments/authored/m0-genhtml-cli-metric-layout-wave.json`:

- `command.genhtml.option.frames`
- `command.genhtml.option.precision`
- `command.genhtml.option.no-sort`

The retained suite is `compat/cases/m0-genhtml-cli-metric-layout-contract.json`.
It has one control case and one direct-option target case per option. The
shared invocation enables function, branch, and MC/DC coverage, selects
`control.lcovrc`, writes to `report`, and reads `input.info`; the target option
is inserted after `--config-file control.lcovrc` and before the output-directory
arguments. Exact exit, stdout, stderr, and filesystem comparisons are required.

## Source Contract

Each plan retains the parser registration and two executable consumers from the
pinned LCOV v2.5 source. The source references are sorted and the executable
line text is locked by the focused suite:

| Option | Parser | Consumers |
| --- | ---: | --- |
| `frames` | `bin/genhtml:7253` | `bin/genhtml:7552`, `bin/genhtml:8467` |
| `precision` | `bin/genhtml:7266` | `bin/genhtml:7558`, `lib/lcovutil.pm:2768` |
| `no-sort` | `bin/genhtml:7265` | `bin/genhtml:7337`, `bin/genhtml:8970` |

Manual/help-only references were removed from these plans. The fixture is the
existing `compat/fixtures/m0-lcovrc-genhtml-metric-contract`, whose recursive
SHA lock and semantic trace anchors remain covered by the focused test.

## Oracle Runs

The canonical differential command was run twice with fresh output roots:

```text
cargo run --locked -p ferricov-oracle --bin differential -- \
  /tmp/ferricov-genhtml-cli-metric-layout-suite.json \
  compat/launchers/lcov-v2.5-genhtml-report-oracle.json \
  compat/launchers/different-genhtml-report-oracle.json \
  /tmp/ferricov-genhtml-cli-metric-layout-run-c

cargo run --locked -p ferricov-oracle --bin differential -- \
  /tmp/ferricov-genhtml-cli-metric-layout-suite.json \
  compat/launchers/lcov-v2.5-genhtml-report-oracle.json \
  compat/launchers/different-genhtml-report-oracle.json \
  /tmp/ferricov-genhtml-cli-metric-layout-run-d
```

The runner exits non-zero because the intentional reverse candidate differs;
this is expected harness qualification. Both runs produced identical
reference/output characterization facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | `dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c` | 550 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `ba20427ff8a62d5ae3fbfec3d81600908a1cdeec524734deb2ce58a512c97904` | 11834 | 33 | 0 | 23 |
| `frames` | `dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c` | 550 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `9c5524a2b6856b12a7820785c2b7ca28c8abe4785dbae8ea62416af741453998` | 14075 | 39 | 0 | 23 |
| `precision 4` | `479c721b6327aede02c6c3a1265851bdb89404a37734a828d41a74c7d14a1083` | 562 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `582cc0c35384825eba455cf952f056dffc1271e6b46c820acb502ff5f0ac7bba` | 11834 | 33 | 0 | 23 |
| `no-sort` | `dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c` | 550 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `233d08f67421873aacd37a84670e9bcaa7c6dece107af6d215877e0921200fa7` | 9346 | 26 | 0 | 23 |

The reference process reported no timeout, reaped its child, and removed its
container for every case in both runs. These are Oracle characterization facts
only; no Ferricov candidate was run and no product compatibility evidence is
claimed.

## Contract Effect

- reviewed primary plans: `425 -> 428`
- fixed source/interaction projections: `427 -> 430`
- explicit M0 planning gaps: `106 -> 103`
- command gaps: `38 -> 35`
- `genhtml` command gaps: `21 -> 18`
- product compatibility evidence: unchanged and empty

The three skeletons were removed from the residual wave1 repair fragments and
placed in the responsibility-named fragment. Owner and age field widths remain
deferred because annotation/date inputs are not present in this fixture. M1
parser/model implementation remains blocked.

## Verification

- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_metric_layout_contract` (9 tests)
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration` (pass: 428 reviewed, 103 gaps)
- `python3 compat/behavior/validate.py --mode m0-ready --skip-regeneration` (expected failure on 103 gaps)
- `python3 compat/verify.py --skip-oracle`

The focused suite rejects target-option removal/value mutations, source-text
drift, fixture hash or semantic-anchor loss, launcher drift, and trusted
plan-binding mutations. No Rust product behavior was changed.
