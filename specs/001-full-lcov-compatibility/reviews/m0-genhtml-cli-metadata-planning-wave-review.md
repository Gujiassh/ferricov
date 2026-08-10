# M0 genhtml CLI Metadata Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly three command-owned public options in the dedicated
owner fragment `compat/behavior/fragments/authored/m0-genhtml-cli-metadata-wave.json`:

- `command.genhtml.option.css-file`
- `command.genhtml.option.description-file`
- `command.genhtml.option.keep-descriptions`

The retained suite is `compat/cases/m0-genhtml-cli-metadata-contract.json`.
It has one control case and one direct metadata target case per option. The
`description-file` and `keep-descriptions` cases use a sidecar containing one
referenced and one unused test description; `keep-descriptions` retains both.
Every case compares exact exit, stdout, stderr, and filesystem results.

## Source Contract

Each retained plan pins parser registration and executable consumer lines from
LCOV v2.5:

| Option | Source references |
| --- | --- |
| css-file | `bin/genhtml:7226`, `bin/genhtml:9047`, `bin/genhtml:9049` |
| description-file | `bin/genhtml:7224`, `bin/genhtml:7929`, `bin/genhtml:7931` |
| keep-descriptions | `bin/genhtml:7225`, `bin/genhtml:7935`, `bin/genhtml:7936` |

The focused suite locks the exact upstream source text at every referenced
line.

## Fixture And Launcher

The dedicated fixture is `compat/fixtures/m0-genhtml-cli-metadata-contract`.
It contains a named testcase tracefile, source file, description sidecar, and
custom stylesheet. Recursive fixture SHA-256 entries are locked by the focused
test. The pinned launcher pair is unchanged:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- environment: `HOME=/work`, `LANG=C`, `LC_ALL=C`, pinned container `PATH`,
  `SOURCE_DATE_EPOCH=946684800`, `TMPDIR=/work`, and `TZ=UTC`
- reference program: `{command}`
- reverse program: `sh`, exiting 23

## Oracle Runs

The canonical differential command ran twice with fresh output roots:

```text
cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-metadata-suite-0810.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-metadata-run-d-0810

cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-metadata-suite-0810.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-metadata-run-e-0810
```

The runner exits non-zero only because the intentional reverse candidate
 differs; this is expected harness qualification. Both runs produced identical
reference/output characterization facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | 9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637 | 349 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | 74dd47fe7c0c02d6d7ec11702806b30207664675ca4134bc5f570385b1cfc1f4 | 6369 | 18 | 0 | 23 |
| css-file | 9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637 | 349 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | 8007161eaf091228b8a7d9ee595db8c964f30087b8e674cf316c68667296cb30 | 6366 | 18 | 0 | 23 |
| description-file | c954365ccc25f07a9e1644d69dc9882c37a9bf21c1e5e4b9ec457756ae749d36 | 477 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | be7bff53e61e5b6cb55503273d0f22220e7c85da0ab165796c76c2b51cc3564b | 6717 | 19 | 0 | 23 |
| keep-descriptions | 2eb041faeea393e3b7cc80019aba71ea24564534ca7d885f318967d343c58e01 | 433 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | b8e6fd647212d4d431921c1249bd7a55720e947c2741686bc354401a20c62a93 | 6717 | 19 | 0 | 23 |

Reference processes exited 0, reported no timeout, reaped their children, and
removed every container. The fixed 317-byte stderr is the pinned GCC/gcov
unsupported-function-boundary warning emitted by this fixture. These are
Oracle facts only; no Ferricov candidate was run and no product compatibility
evidence is claimed.

## Planning Effect

- public primary plans: `531` (unchanged)
- reviewed primary plans: `437 -> 440`
- fixed source/interaction projections: `439 -> 442`
- explicit M0 planning gaps: `94 -> 91`
- command gaps: `26 -> 23`
- genhtml command gaps: `9 -> 6`
- product compatibility evidence: unchanged and empty

M1 parser/model and Rust product implementation remain blocked. This wave
closes planning links only and does not authorize product behavior work.

## Verification

- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_metadata_contract` (7 tests)
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- `python3 compat/verify.py --skip-oracle`
- `git diff --check`
