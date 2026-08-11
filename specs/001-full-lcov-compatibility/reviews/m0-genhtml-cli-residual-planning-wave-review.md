# M0 genhtml CLI Residual Planning Wave Review

Status: accepted as a bounded M0 planning slice after controller rework

Controller decision:
[`m0-genhtml-cli-residual-planning-wave-controller-review.md`](m0-genhtml-cli-residual-planning-wave-controller-review.md)

## Scope

This wave reviews exactly three residual public genhtml command surfaces in the
dedicated owner fragment
`compat/behavior/fragments/authored/m0-genhtml-cli-residual-wave.json`:

- `command.genhtml.option.preserve`
- `command.genhtml.option.synthesize-missing`
- `command.genhtml.positional.tracefile-pattern`, scoped here to **explicit multi-file positional aggregation only**

The retained suite is `compat/cases/m0-genhtml-cli-residual-contract.json`.
It has one control case and one direct target case per surface. Every case
compares exact exit, stdout, stderr, and filesystem results with normalizer
`exact-v1`.

### Explicit non-claims for the positional surface

The inventory identity remains `command.genhtml.positional.tracefile-pattern`
because inventory IDs are fixed. This wave does **not** claim wildcard/glob
semantics. Glob expansion, unmatched patterns, match ordering, and duplicate
matches remain separate M0 gaps. The retained case uses two concrete path
arguments: `input.info input2.info`.

Excluded from this wave because they are not yet stable under exact-v1 or need
broader fixtures:

- `command.genhtml.option.debug` (memory/debug stderr drifts across runs)
- `command.genhtml.option.history-script` (requires a reviewed callback fixture)
- `command.genhtml.option.new-file-as-baseline` (requires differential baseline
  inputs beyond this residual suite)

## Source Contract

Each retained plan pins parser registration and executable consumer lines from
LCOV v2.5:

| Surface | Source references | Planning scope |
| --- | --- | --- |
| preserve | `lib/lcovutil.pm:1286`, `lib/lcovutil.pm:622`, `lib/lcovutil.pm:10167` | CLI option |
| synthesize-missing | `bin/genhtml:7237`, `bin/genhtml:5727`, `bin/genhtml:5832` | CLI option |
| multi-file positional | `bin/genhtml:7456` | explicit multi-file aggregation only |

The focused suite locks the exact upstream source text at every referenced
line.

## Fixture, Observation Manifest, And Launcher

The dedicated fixture is `compat/fixtures/m0-genhtml-cli-residual-contract`.
It contains the shared control `lcovrc`, a normal source/trace pair, a second
compatible tracefile for multi-input merge, a missing-source tracefile for
synthesis, and the structured Oracle observation manifest
`oracle-observations.json`. Recursive fixture SHA-256 entries are locked by the
focused test. The focused test loads that manifest as the canonical observation
source; the table below is a human-readable projection and is asserted to match
it.

The pinned launcher pair is unchanged:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- environment: `HOME=/work`, `LANG=C`, `LC_ALL=C`, pinned container `PATH`,
  `SOURCE_DATE_EPOCH=946684800`, `TMPDIR=/work`, and `TZ=UTC`
- reference program: `{command}`
- reverse program: `sh`, exiting 23

## Oracle Runs

The canonical differential command ran twice with fresh output roots before the
manifest was sealed:

```text
cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-residual-final-suite.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-residual-final-a

cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-residual-final-suite.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-residual-final-b
```

The runner exits non-zero only because the intentional reverse candidate
differs; this is expected harness qualification. Both runs produced identical
reference/output characterization facts and reverse exit status. The sealed
manifest records those facts with `product_compatibility_evidence=false`.

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | 9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637 | 349 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | f8e60388d62a3f22fdf2efd1458249b4f8b0df5c4d0c51bbdb6b9ec0415dfa51 | 6359 | 18 | 0 | 23 |
| preserve | 9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637 | 349 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | c4cc1497831cf14b5eb5dd51db83e32b631795247c1c2f6b0ca339b556e0c45a | 6359 | 18 | 0 | 23 |
| synthesize-missing | 7cf9e458a47298b20ff12144dd1a103f9d45474c9c61d4d3ac819bc468a64c8b | 393 | 2125d1ed1e54c171bd8660ce06d553697bb248a167c659b6c122187d1f0f8c21 | 199 | 977a63d367b2c9edec60d514d8ef9f04d1bd63391c367926c4b011d8c0079590 | 6432 | 18 | 0 | 23 |
| multi | 8704922579e6f3a474d2cc944edba10b97ae28463f308604a8d9e7c2ea95d406 | 408 | 5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8 | 317 | bba9c587b30ddb407492adffe550f8fbb2c09286a25b33ea2bf200ee3b46d63c | 6359 | 18 | 0 | 23 |

Reference processes exited 0, reported no timeout, reaped their children, and
removed every container. The synthesize-missing case emits a source-synthesis
warning under `--ignore-errors source,unsupported`. These are Oracle facts
only; no Ferricov candidate was run and no product compatibility evidence is
claimed.

## Integrity Gates

Suite mutations are rejected by the production residual gate
`compat/cases/m0_genhtml_cli_residual_contract.py`, which is invoked from
`compat/verify.py` and by the focused residual tests:

- argv deletion, replacement, and reorder for each retained target
- comparison normalizer replacement away from `exact-v1`
- comparison dimension reorder
- invalid normalizer enum values

Bare `suite.schema.json` still accepts argv reorder and alternate stdout
normalizers; the residual production module is the semantic integrity gate.

## Planning Effect

- public primary plans: `531` (unchanged)
- reviewed primary plans: `440 -> 443`
- fixed source/interaction projections: `442 -> 445`
- explicit M0 planning gaps: `91 -> 88`
- command gaps: `23 -> 20`
- genhtml command gaps: `6 -> 3`
- product compatibility evidence: unchanged and empty

M1 parser/model and Rust product implementation remain blocked. This wave
closes planning links only and does not authorize product behavior work.

## Verification

- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_residual_contract`
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current --skip-regeneration`
- `python3 compat/verify.py --skip-oracle`
- `git diff --check`
