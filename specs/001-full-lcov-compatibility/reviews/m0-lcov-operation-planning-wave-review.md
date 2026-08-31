# M0 lcov Operation Planning Wave Review

Status: accepted for five primary plans; seven `lcov` gaps remain

## Scope

The `m0-lcov-operation-contract` suite closes five primary planning gaps:

- `--debug`
- `--extract`
- `--history-script`
- `--no-checksum`
- `--prune-tests`

A sixth case is the positive `--checksum` control for `--no-checksum`.
The fixture contains valid line checksums, two source files, contributing and
empty testcase data, one function, and one hit plus one missed branch.

## Oracle Executability Check

The Rust differential runner executed all six cases against immutable LCOV v2.5
image `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
with a read-only container root, `TMPDIR=/work`, clean environment values,
fresh writable fixture copies, timeout, cleanup, raw streams, and file-tree
evidence.

| Case | Exit | Observable result |
| --- | ---: | --- |
| `m0-lcov-checksum-control` | 0 | 286-byte checksummed output |
| `m0-lcov-debug` | 0 | 217-byte rewrite and extra debug memory line on stderr |
| `m0-lcov-extract` | 0 | 155-byte output retains `foo.c`, removes `bar.c` |
| `m0-lcov-history-script` | 0 | 217-byte rewrite plus 7-byte constructor marker |
| `m0-lcov-no-checksum` | 0 | paired checksum/no-checksum argv writes 217-byte checksum-free output |
| `m0-lcov-prune-tests` | 0 | 11-byte retained-input list |

The checksum control SHA-256 is
`8f5337ffd9d2ba2d1e54f2e3ba18b20f2d02337aea2a932339ed817bda89026c`;
the common checksum-free rewrite SHA-256 is
`1c2dc1373a1e8d4850ea2b349f21343a943131f74a7df0d428feba5539fe2673`.

## Residuals

Seven `lcov` entries remain unreviewed:

- capture-mode ownership: `--compat-libtool`, `--derive-func-data`,
  `--external`, and `--large-file`;
- capture/reset lifecycle: `--zerocounters`;
- `--fail-under-branches`, which does not execute the criterion in the tested
  add-tracefile operation and requires an applicable capture/summary path;
- `--preserve`, whose one-file operation is an inert no-op and whose true
  parallel path needs separate stable temp-tree evidence.

These entries were not promoted merely because their option parser accepted
argv.

## Contract Effect

- substantive reviewed primary plans: 382 -> 387
- explicit M0 behavior gaps: 149 -> 144
- fixed primary/interaction projections: 384 -> 389
- product evidence: unchanged and empty

The differential candidate is the intentional reverse-test stub. Its failures
validate reference capture only; all five primary plans remain planning-only.

## Verification

- exact case set, fixture hash closure, two-source extract shape, valid checksum
  atoms, testcase-prune input, callback marker, checksum control precedence
- immutable-image differential reference artifacts for all six suite cases
- stable behavior generation and fixed plan-binding hash
