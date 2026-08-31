# M0 lcovrc genhtml Metric Planning Wave Review

Status: accepted for nine primary plans

## Scope

The `m0-lcovrc-genhtml-metric-contract` suite closes these consumers against a
shared control:

- `genhtml_function_hi_limit`
- `genhtml_function_med_limit`
- `genhtml_branch_hi_limit`
- `genhtml_branch_med_limit`
- `genhtml_mcdc_hi_limit`
- `genhtml_mcdc_med_limit`
- `genhtml_branch_field_width`
- `genhtml_mcdc_field_width`
- `genhtml_overview_width`

The nine unreviewed objects were moved from the residual wave1 A/B fragments
into `m0-lcovrc-genhtml-metric-wave.json`, a responsibility-named fragment.
The source and target object audit found nine moved objects, no ID loss, and no
duplicate case or target identity. `owner-field-width` and `age-field-width`
remain explicitly deferred: their visible source-view effects require annotation
and date inputs, which this metric fixture does not provide.

## Deterministic Envelope

The reference and reverse launchers are paired fixed-epoch variants of the
same canonical LCOV v2.5 image:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- `SOURCE_DATE_EPOCH=946684800`
- `TZ=UTC`, `LANG=C`, `LC_ALL=C`
- `TMPDIR=/work` and each config's `lcov_tmp_dir=/work`
- read-only container root and writable per-case `/work`

The reference executable identity was `sha256:8ef84c95ce3970f6ba4743e81dd91e4dacca71266478801982179362204b2b6a`.
The reverse launcher used a distinct executable identity and intentionally
exited 23. The differential artifact directory was temporary:
`/tmp/ferricov-lcovrc-genhtml-metric-differential`.

## Fixture Semantics

`alpha.c` and `beta.c` each declare two functions. Alpha is 50% function,
branch, and MC/DC covered; beta is 100% for each metric. The tracefile has
valid `FN`/`FNDA` pairs, four mixed-hit `BRDA` rows per source, valid MCDC
records, and matching `MCF`/`MCH` summaries. The shared argv enables
`--frames`, `--function-coverage`, `--branch-coverage`, and `--mcdc-coverage`.

## Oracle Reference Facts

All ten reference cases exited 0 with empty stderr, 550-byte stdout, and 39
generated output files. The control and each target tree are pairwise distinct;
the exact reference file-tree SHA-256 values are:

| Setting | File-tree SHA-256 |
| --- | --- |
| control | `ca0d288fea65d0171795f050e89f6bfebc246bff515d7f4646c3388670a30911` |
| `genhtml_function_hi_limit = 50` | `69b2560b1db4856d4975c283beb9d5cdbb3a79a9d4bfa154080dc4fbe9bce635` |
| `genhtml_function_med_limit = 50` | `36c4f066bd5b4b962aa4f4321ba022fe7b3685e6cfa41bead0c2e9dba6079498` |
| `genhtml_branch_hi_limit = 50` | `070b92948b371c0fad92b928914557686fba1a8b70abc7d2288b622fe736f569` |
| `genhtml_branch_med_limit = 50` | `da570d74666f2a3e6846e078dffd14b306b2736ac41787c4d701d9d60f5ad011` |
| `genhtml_mcdc_hi_limit = 50` | `3f2483e06cf60d8a19e71992155f14f284102879486989ff6818ca1de30ff8da` |
| `genhtml_mcdc_med_limit = 50` | `5228f6011246b0f25381c6f9779ec56e01c34d6588efddd2717882fb79437ce6` |
| `genhtml_branch_field_width = 24` | `7823ad34d555f1f00bb1afad0c9ee312ff58efe9038b12c367c8a8281ae20b79` |
| `genhtml_mcdc_field_width = 24` | `b1978269b3d6b2aedb644efcdabf9be5f603b75dc4143f08a72163545d10d11f` |
| `genhtml_overview_width = 40` | `500a999149e02683c025816099cd72b435380d1b03c0d8dc1012eeee9d279eea` |

The overview-width target is independently observable: with `--frames`, the
Oracle changes the frameset column from 120 to 80, overview image width from
80 to 40, image-map coordinates, and PNG dimensions. This target is therefore
included rather than deferred.

These are Oracle reference/output characterization facts. No Ferricov
candidate was run, every plan remains `evidence_status=planned` with
`evidence=[]`, and product compatibility evidence remains false.

Every new plan uses an explicit `config-key boundary` description. The fixed
plan-binding artifact seals each boundary form to its exact target assignment,
including `genhtml_overview_width = 40` rather than shared `--frames`; its
trusted SHA-256 is `562d79ca8528ad2d47e88d888de427dfba0fe75bccdc141ad0e9941e0a28fead`.

## Contract Effect

- substantive reviewed primary plans: 408 -> 417
- explicit M0 behavior gaps: 123 -> 114
- fixed primary/interaction projections: 410 -> 419
- product pass/fail evidence: unchanged and empty

## Verification

- exact 10-case suite with four comparison dimensions
- recursive fixture SHA-256 locks and source line checks
- paired launcher image, environment, executable identity, and fixed-epoch checks
- shared control plus one target config assignment per case
- pinned LCOV v2.5 differential reference and intentionally divergent reverse harness
- focused metric contract tests, behavior generation, and plan-binding mutation checks
- `PYTHONPATH=. python3 -m unittest compat.cases.test_m0_lcovrc_genhtml_metric_contract` (10 tests)
- `PYTHONPATH=. python3 -m unittest compat.behavior.test_validate` (48 tests)
- `python3 compat/behavior/validate.py --mode current` (pass: 417 reviewed, 114 gaps)
- `python3 compat/behavior/validate.py --mode m0-ready` (expected failure: 114 gaps)
- `python3 compat/verify.py --skip-oracle` (pass)
- `cargo fmt --all -- --check`, `cargo check --workspace`, `cargo test --workspace` (106 Oracle tests), and `cargo clippy --workspace --all-targets -- -D warnings` (pass)
- `git diff --check` (pass); no files are staged. M1 remains blocked.
