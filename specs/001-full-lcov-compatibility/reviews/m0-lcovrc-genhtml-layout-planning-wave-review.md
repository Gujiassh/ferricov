# M0 lcovrc genhtml Layout Planning Wave Review

Status: accepted for eleven primary plans

## Scope

The `m0-lcovrc-genhtml-layout-contract` suite closes these consumers against a
shared control:

- `genhtml_hi_limit`
- `genhtml_med_limit`
- `genhtml_line_hi_limit`
- `genhtml_line_med_limit`
- `genhtml_line_field_width`
- `genhtml_missed`
- `genhtml_precision`
- `genhtml_hierarchical`
- `genhtml_no_prefix`
- `genhtml_show_navigation`
- `genhtml_sort`

The 11 unreviewed objects were moved from B into the 595-line
`m0-lcovrc-genhtml-layout-wave.json`; the retained B fragment is 1,134 lines.
The pre-binding object audit found 37 old cases, 26 retained, 11 moved, and no
ID loss or duplication.

## Deterministic Envelope

The reference and reverse launchers are paired fixed-epoch variants of the
same canonical LCOV v2.5 image:

- image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- `SOURCE_DATE_EPOCH=946684800`
- `TZ=UTC`, `LANG=C`, `LC_ALL=C`
- `TMPDIR=/work` and each config's `lcov_tmp_dir=/work`
- read-only container root with writable per-case `/work`

The reverse launcher exits 23 and remains harness-only evidence. Product
compatibility evidence is unchanged and false.

## Fixture Semantics

`alpha.c` has five instrumented lines with 4 hits (80%); `nested/beta.c` has
two instrumented lines with 2 hits (100%). This makes the common threshold and
line-threshold boundaries observable. The nested path makes hierarchical,
no-prefix, navigation, and sort settings reach their output consumers.

## Oracle Reference And Harness Facts

The pinned Rust differential runner recorded exit 0 and empty stderr for all 12
reference cases. These values are Oracle reference/output characterization; the
intentionally divergent launcher yielded `overall_status=fail`, no Ferricov
candidate was run, and this is not candidate or product evidence. The control
reference has stdout 416 bytes and file-tree SHA-256
`264cce1ddc38c77d486bd33b7fc1ebbfdc011c1df5a1cd996112b0fe86246303`.
Nondefault reference file-tree hashes are:

| Setting | File-tree SHA-256 | Files |
| --- | --- | ---: |
| `genhtml_hi_limit=80` | `d2fa8a5552a7fb5ceea914c4c983c73837fc83e77f5a233a16828b012fd79417` | 34 |
| `genhtml_med_limit=85` | `0f61cd16eb2aa1c693be28e376c84b51ec782a8d9455a550ed60c4b87dd038cc` | 34 |
| `genhtml_line_hi_limit=80` | `e501a1565303aececa836f04a0b6d06c4c66466a0c82917152ddac5e87dbe75c` | 34 |
| `genhtml_line_med_limit=85` | `a772889a265751343d7029dac9d2f81c4772bbba450af4dd5829d42b12e1a421` | 34 |
| `genhtml_line_field_width=20` | `a80a61d455effc10382f5c402fa0d5a78650559548afe58cfafc5bc09aa64291` | 34 |
| `genhtml_missed=1` | `09d2475deda1fbe916e54a12666cc730c1e3c97dab00623f198c5a6854d4e084` | 34 |
| `genhtml_precision=4` | `2c51e922f868e7ee5618d030477b0d171568ac1a050d586fc364d6c40ee4f760` | 34 |
| `genhtml_hierarchical=1` | `855ab4b1b4f191f5809d836b21fd4c93c74add411af3e8ce01a0a68f85685e0c` | 34 |
| `genhtml_no_prefix=1` | `ce09b3b614b3d49330805cc5a0b82d3c31b07cd02d41fd83b2893fc5788f46c8` | 34 |
| `genhtml_show_navigation=1` | `2be352f15125b146477563828998c0748413fc966ddf05734399713dc356dfc2` | 34 |
| `genhtml_sort=0` | `fb9e911a64f062063afc51c3f3f733d85b046e1e42a18b1b026820213c288549` | 29 |

Two independent manual Docker runs produced the same report-only tree hash for
every case and distinct hashes for every nondefault case. The differential
artifact directory is temporary, not retained product evidence, and is
`/tmp/ferricov-lcovrc-genhtml-layout-differential-1786289728`.

## Contract Effect

- substantive reviewed primary plans: 397 -> 408
- explicit M0 behavior gaps: 134 -> 123
- fixed primary/interaction projections: 399 -> 410
- product pass/fail evidence: unchanged and empty

## Verification

- exact 12-case suite and four comparison dimensions
- recursive fixture SHA-256 locks
- paired launcher image, environment, and fixed-epoch checks
- shared control plus one target config assignment per case
- stable behavior generation, behavior validator, full `verify --skip-oracle`, and Rust gates

The 11 plans are reference planning closure only. They do not authorize parser,
model, ops, or Ferricov product implementation before the M0 gate.
