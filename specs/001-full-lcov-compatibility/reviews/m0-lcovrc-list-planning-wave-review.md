# M0 lcovrc List Planning Wave Review

Status: accepted for two primary plans; truncate-max remains unbound

## Structural Split

`m0-lcovrc-wave1-repair-c.json` was 1,986 lines and could not safely accept more
bindings. Its 20 unreviewed cases were moved without semantic changes into five
consumer-owned fragments:

- `m0-lcovrc-list-wave.json`
- `m0-lcovrc-capture-wave.json`
- `m0-lcovrc-report-wave.json`
- `m0-lcovrc-filter-wave.json`
- `m0-lcovrc-blocked-wave.json`

The retained reviewed fragment is 1,130 lines; every new fragment is below 300
lines. Contract totals and plan bindings remained unchanged before the list
cases were promoted.

## Scope

The `m0-lcovrc-list-contract` suite closes:

- `lcov_list_full_path`
- `lcov_list_width`

Both bind the same default control. The fixture contains five source paths in a
shared directory, including one deliberately long basename.

## Oracle Executability Check

The Rust differential runner executed all three cases against immutable LCOV
v2.5 image
`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
under the standard read-only-root, clean-environment envelope.

| Case | Exit | Stdout bytes | Stdout SHA-256 |
| --- | ---: | ---: | --- |
| default control | 0 | 687 | `d71af4d5063da042db2b3ede3d7743caf15a315c32d6a23dc68fccc821c9c1da` |
| full path = 1 | 0 | 1275 | `6b82305c96399a9fec6d5301e369a525c401c0820f51a703444d504b79e64764` |
| width = 50 | 0 | 389 | `9afe7b7bdf7fe38b31013ca6f42c62b825c71702dc14e7d10b852908af0912ff` |

All stderr streams are empty. The two nondefault values therefore have
independent, byte-distinct Oracle behavior.

## Truncate Residual

`lcov_list_truncate_max=0` was probed against control value 20 with two fixture
shapes and at widths 50 and 80. Every probe was byte-identical to its control.
Without a fixture that makes prefix selection observably differ, the case
remains unreviewed with no suite binding.

## Contract Effect

- substantive reviewed primary plans: 387 -> 389
- explicit M0 behavior gaps: 144 -> 142
- fixed primary/interaction projections: 389 -> 391
- product evidence: unchanged and empty

## Verification

- exact suite IDs and config comparison dimensions
- fixture/config SHA-256 closure and long-path shape
- independent control/nondefault values
- explicit truncate residual guard
- immutable-image differential reference artifacts
- stable behavior generation and fixed plan-binding hash
