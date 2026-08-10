# M0 `genhtml` CLI Report Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly three command-owned public options in the dedicated
owner fragment `compat/behavior/fragments/authored/m0-genhtml-cli-report-wave.json`.
The three residual skeletons were removed from `m0-genhtml-wave1-repair-b.json`.

- `command.genhtml.option.footer`
- `command.genhtml.option.no-checksum`
- `command.genhtml.option.no-html`

The retained suite is `compat/cases/m0-genhtml-cli-report-contract.json`. It
has one control case and one direct-option target case per option. Every
invocation uses the shared `--config-file control.lcovrc` fixture and writes to
`report` from `input.info`. Exact exit, stdout, stderr, and filesystem
comparisons are required.

## Source Contract

Each plan retains the parser registration and executable consumer lines from
the pinned LCOV v2.5 source. The source references are exact-text locked by the
focused suite:

| Option | Source references |
| --- | --- |
| `footer` | `bin/genhtml:7157`, `bin/genhtml:7222`, `bin/genhtml:11706` |
| `no-checksum` | `lib/lcovutil.pm:1243`, `lib/lcovutil.pm:1596`, `lib/lcovutil.pm:9779` |
| `no-html` | `bin/genhtml:7251`, `bin/genhtml:7291`, `bin/genhtml:7951` |

The `no-checksum` plan intentionally follows the shared lcovutil option and its
runtime consumer, while the other two plans remain genhtml-owned.

## Fixture And Launcher

The fixture is the existing `compat/fixtures/m0-lcovrc-genhtml-contract`.
The focused suite locks every recursive fixture SHA-256 and checks the source
and trace anchors used by the report wave. The existing pinned launcher pair is
unchanged:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- environment: `HOME=/work`, `LANG=C`, `LC_ALL=C`, pinned container `PATH`,
  `SOURCE_DATE_EPOCH=946684800`, `TMPDIR=/work`, and `TZ=UTC`
- reference program: `{command}`
- reverse program: `sh`, exiting 23

## Oracle Runs

The canonical differential command was run twice with fresh output roots:

```text
cargo run --locked -p ferricov-oracle --bin differential -- \
  compat/cases/m0-genhtml-cli-report-contract.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-report-differential-fixed-a

cargo run --locked -p ferricov-oracle --bin differential -- \
  compat/cases/m0-genhtml-cli-report-contract.json \
  compat/launchers/lcov-v2.5-genhtml-oracle.json \
  compat/launchers/different-genhtml-oracle.json \
  /tmp/ferricov-genhtml-cli-report-differential-fixed-b
```

The runner exits non-zero because the intentional reverse candidate differs;
this is expected harness qualification. Both runs produced identical reference/output characterization facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329` | 8882 | 28 | 0 | 23 |
| `footer` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `a05c4105eff8f5dafd6af9c443ea4993b93d8465e7b10a418ea50c67ae5e3a3f` | 8882 | 28 | 0 | 23 |
| `no-checksum` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `0b2d3c12d04b463b1c356b0369186a2c3f791556b64c9de7191a16856654bd5c` | 8882 | 28 | 0 | 23 |
| `no-html` | `52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137` | 337 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `aa4c1afab3bf0f16591e032c947f8b558c139a4fe36ab2d877da293f03ed41e8` | 4610 | 15 | 0 | 23 |

The reference process reported no timeout, reaped its child, and removed its
container for every case in both runs. These are Oracle characterization facts
only; no Ferricov candidate was run and no product compatibility evidence is
claimed.

## Contract Effect

- public primary plans: `531` (unchanged)
- reviewed primary plans: `428 -> 431`
- fixed source/interaction projections: `430 -> 433`
- explicit M0 planning gaps: `103 -> 100`
- command gaps: `35 -> 32`
- `genhtml` command gaps: `18 -> 15`
- product compatibility evidence: unchanged and empty

M1 parser/model and product implementation remain blocked. This wave closes
planning boundaries only and does not authorize Rust behavior work.

## Verification

- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_report_contract` (9 tests)
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- `python3 compat/behavior/validate.py --mode m0-ready --skip-regeneration` (expected failure on 100 gaps)
- `python3 compat/verify.py --skip-oracle`
