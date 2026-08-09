# M0 llvm2lcov Planning Wave Review

Status: accepted as planning-only evidence

## Scope

The `m0-llvm2lcov-contract` suite closes seven primary planning gaps:

- `--debug`
- `--fail-under-branches`
- `--history-script`
- `--no-checksum`
- `--output-filename`
- `--preserve`
- `<json_file>`

The fixtures contain a minimal LLVM export, a real 50-percent branch export,
matching source files, and a Perl history callback whose constructor writes a
marker.

## Oracle Executability Check

Every argv was executed against pinned LCOV v2.5 image
`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
with network disabled, clean locale/timezone/home values, a read-only container
root, `TMPDIR=/work`, a fresh writable copy of the fixture directory, and the
runner's bounded host deadline.

| Case | Exit | Observable result |
| --- | ---: | --- |
| `m0-llvm2lcov-debug` | 0 | 51-byte requested tracefile; debug is a bounded no-op for this conversion path |
| `m0-llvm2lcov-fail-under-branches` | 1 | 169-byte tracefile; 50 percent branch result fails threshold 75 |
| `m0-llvm2lcov-history-script` | 0 | 51-byte tracefile plus 7-byte `history.loaded` constructor marker |
| `m0-llvm2lcov-no-checksum` | 0 | `--checksum --no-checksum` writes a 51-byte checksum-free tracefile; checksum flags are a bounded no-op on this writer path |
| `m0-llvm2lcov-output-filename` | 0 | 51-byte tracefile at the requested path |
| `m0-llvm2lcov-preserve` | 0 | 169-byte filtered tracefile; this bounded path creates no intermediate artifact to retain |
| `m0-llvm2lcov-json-file-positional` | 0 | 51-byte default `llvm2lcov.info` output |

The branch fixture yields one hit and one missed branch (`BRF=2`, `BRH=1`).
The preserve case combines filtering, parallelism, explicit temp-root selection,
and `--preserve`; the exact no-extra-artifact filesystem result is part of the
planned parity surface. The standard and reverse-test differential launchers
set `TMPDIR=/work`, because the Docker root is read-only and LCOV initializes a
`Capture::Tiny` tempfile before processing `--tempdir`. A real Rust differential
run retained all seven reference result trees under this envelope.

## Contract Effect

- substantive reviewed primary plans: 370 -> 377
- explicit M0 behavior gaps: 161 -> 154
- fixed primary/interaction projections: 372 -> 379
- product evidence: unchanged and empty

These runs establish executable planning argv only. They are not Ferricov
candidate results and cannot establish product compatibility.

## Verification

- suite schema, exact case set, fixture ownership, branch shape, callback
  marker, checksum precedence, threshold, preserve, and positional tests
- stable behavior generation and fixed plan-binding hash
- current validation expected at `public=531`, `reviewed_primary=377`,
  `m0_gaps=154`
