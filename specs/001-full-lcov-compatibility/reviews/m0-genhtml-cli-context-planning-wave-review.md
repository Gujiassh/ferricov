# M0 genhtml CLI Context Planning Wave Review

Status: accepted as a bounded M0 planning slice

## Scope

This wave reviews exactly three command-owned public options in the dedicated owner fragment compat/behavior/fragments/authored/m0-genhtml-cli-context-wave.json. The residual skeletons were removed from the existing wave1 repair fragments.

- command.genhtml.option.baseline-title
- command.genhtml.option.merge-aliases
- command.genhtml.option.suppress-aliases

The retained suite is compat/cases/m0-genhtml-cli-context-contract.json. It has one control case and one direct-option target case per option. The shared invocation uses the pinned alias baseline/current/diff fixture, --filter function, a fixed baseline date, and exact exit, stdout, stderr, and filesystem comparisons.

## Source Contract

Each retained plan pins parser registration and executable consumer lines from LCOV v2.5:

| Option | Source references |
| --- | --- |
| baseline-title | bin/genhtml:7228, bin/genhtml:12362, bin/genhtml:12365 |
| merge-aliases | bin/genhtml:5243, bin/genhtml:7271, bin/genhtml:13912 |
| suppress-aliases | bin/genhtml:7272, bin/genhtml:7286, bin/genhtml:13998 |

The focused suite locks the exact source text at every referenced line.

## Fixture And Launcher

The fixture is the existing compat/fixtures/m0-lcovrc-genhtml-report-alias-contract; its recursive SHA-256 and SF:/work/src/alias.c / alias FNA semantic anchors remain locked. The existing pinned launcher pair is unchanged:

- image: sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7
- environment: HOME=/work, LANG=C, LC_ALL=C, pinned container PATH, SOURCE_DATE_EPOCH=946684800, TMPDIR=/work, and TZ=UTC
- reference program: {command}
- reverse program: sh, exiting 23

## Oracle Runs

The canonical differential command ran twice with fresh output roots:

cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-cli-context-suite.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-cli-context-run-a

cargo run --locked -p ferricov-oracle --bin differential -- /tmp/ferricov-genhtml-cli-context-suite.json compat/launchers/lcov-v2.5-genhtml-oracle.json compat/launchers/different-genhtml-oracle.json /tmp/ferricov-genhtml-cli-context-run-b

The runner exits non-zero only because the intentional reverse candidate differs; this is expected harness qualification. Both runs produced identical reference/output characterization facts and reverse exit status:

| Case | Reference stdout SHA-256 | Stdout bytes | Reference stderr SHA-256 | Stderr bytes | Reference tree SHA-256 | Tree bytes | Files | Reference exit | Reverse exit |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| control | 98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea | 800 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 8332c23c2da180e3656f1f55a63be39e2e99002fe96c082bfff44fc4876a26e5 | 6927 | 19 | 0 | 23 |
| baseline-title | 98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea | 800 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 4f14051fc342b9aa796f326e98e06d338508e10923dcdf852378544d54a979a3 | 6927 | 19 | 0 | 23 |
| merge-aliases | 98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea | 800 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | e25b2f27f72a1e97462f0874a5332e9d78a2fca276b5f1a0496bd3a687ca6d7f | 6927 | 19 | 0 | 23 |
| suppress-aliases | 98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea | 800 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 703fc37500b88cb830e46933a6b77da70476df2f7e20d210c061dfc291e16f00 | 6927 | 19 | 0 | 23 |

Reference exit status is 0, stderr is empty, all four reference trees are stable across both runs, and every container is absent after cleanup. no Ferricov candidate was run; the reverse executable exists only to qualify the differential harness.

## Planning Effect

This wave changes planning status only:

- reviewed primary plans: 434 -> 437
- fixed source/interaction projections: 436 -> 439
- explicit M0 planning gaps: 97 -> 94
- command gaps: 29 -> 26
- genhtml command gaps: 12 -> 9

M1 parser/model and product implementation remain blocked. This wave closes planning links only and claims no Ferricov product evidence.

## Acceptance Evidence

- PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_context_contract
- python3 compat/behavior/generate.py --check
- python3 compat/behavior/validate.py --mode current --skip-regeneration
- python3 compat/verify.py --skip-oracle
- git diff --check
