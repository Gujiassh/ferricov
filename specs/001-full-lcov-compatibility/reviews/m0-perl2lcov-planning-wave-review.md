# M0 perl2lcov Planning Wave Review

Status: accepted for five primary plans; `--preserve` remains unbound

## Scope

The `m0-perl2lcov-contract` suite closes five primary planning gaps:

- `--debug`
- `--fail-under-branches`
- `--history-script`
- `--no-checksum`
- `<cover_db>`

A sixth suite case is the positive `--checksum` control required to make the
`--no-checksum` result independently meaningful.

The fixture is a minimal real `Devel::Cover` database generated inside the
pinned Oracle from `sample.pl`, then reduced to the DB files actually required
for replay. Opaque database bytes are binary-classified and pinned by focused
tests. Generated lock files and HTML reports are not part of the input fixture.

## Oracle Executability Check

The Rust differential runner executed all six cases against immutable LCOV v2.5
image `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
with a read-only container root, `TMPDIR=/work`, clean locale/timezone/home
values, fresh writable fixture copies, executable identity, timeout, cleanup,
raw streams, and file-tree evidence.

| Case | Exit | Observable result |
| --- | ---: | --- |
| `m0-perl2lcov-checksum-control` | 0 | positive control writes 188-byte checksummed tracefile |
| `m0-perl2lcov-debug` | 0 | 142-byte tracefile; debug is a bounded no-op for this path |
| `m0-perl2lcov-fail-under-branches` | 1 | 142-byte tracefile; 50 percent branch result fails threshold 75 |
| `m0-perl2lcov-history-script` | 0 | 142-byte tracefile plus 7-byte `history.loaded` constructor marker |
| `m0-perl2lcov-no-checksum` | 0 | `--checksum --no-checksum` writes the 142-byte checksum-free form |
| `m0-perl2lcov-cover-db-positional` | 0 | 142-byte default `perlcov.info` output |

The model contains one hit and one missed branch (`BRF=2`, `BRH=1`), one hit
function, and two hit lines. Checksum output SHA-256 is
`03f4813d11dea6d1420b575412cdaa359ed062f375954003209501bb7a18356c`;
checksum-free output SHA-256 is
`9add1b1a15f3399b627ecc6e91ab6f1116eb2d35f84b29fefc424b45acef9f11`.

## Preserve Residual

A separate pinned-Oracle probe generated a real 52-source `Devel::Cover`
database. That crosses the upstream `>50 files` filter threshold and reaches
the parallel child/dumper path. Under the real read-only-root runner it requires
`lcov_tmp_dir` to point at `/work`; once configured, LCOV leaves a randomized
`filter_datXXXX` tree and enters volatile parent/fork/child failure behavior.

No approved filesystem normalizer exists for that retained randomized tree.
The one-file probe was an inert no-op and was rejected. Therefore
`command.perl2lcov.option.preserve` remains `unreviewed`, has no suite binding,
and stays in the M0 gap ledger.

## Contract Effect

- substantive reviewed primary plans: 377 -> 382
- explicit M0 behavior gaps: 154 -> 149
- fixed primary/interaction projections: 379 -> 384
- product evidence: unchanged and empty

The retained differential run uses an intentionally different reverse-test
candidate. Its failures validate harness/reference capture only and are not
Ferricov product evidence. All five primary plans remain
`evidence_status=planned` with empty evidence arrays.

## Verification

- exact suite IDs and four comparison dimensions
- complete fixture path and SHA-256 closure, with no committed lock files
- threshold, history callback, checksum positive/negative pair, debug, and
  positional argument invariants
- immutable-image differential reference artifacts for all six suite cases
- stable behavior generation and fixed plan-binding hash
