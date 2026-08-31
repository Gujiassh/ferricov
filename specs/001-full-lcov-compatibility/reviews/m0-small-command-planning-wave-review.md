# M0 Small-Command Planning Wave Review

Status: accepted as planning-only evidence

## Scope

The `m0-small-command-contract` suite closes six command primary planning gaps:

- `gendesc --output-filename`
- `py2lcov --tabwidth`
- `genpng --output-filename`
- `genpng --tab-size`
- `genpng --width`
- `genpng <sourcefile>`

Every case compares exact exit, stdout, stderr, and filesystem dimensions from
a fresh copy of its committed fixture directory.

## Oracle Executability Check

All suite argv was executed against pinned LCOV v2.5 image
`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
with network disabled, `HOME=/tmp`, `LANG=C`, `LC_ALL=C`, `TZ=UTC`, and a
30-second host deadline.

| Case | Exit | Output fact |
| --- | ---: | --- |
| `m0-gendesc-output-filename` | 0 | `output.desc`, 58 bytes |
| `m0-py2lcov-tabwidth` | 1 | `output.info`, 19-byte partial `TN`/`SF`; 632-byte `AttributeError` stderr |
| `m0-genpng-output-filename` | 0 | `output.png`, 194 bytes |
| `m0-genpng-tab-size` | 0 | `tab.png`, 194 bytes |
| `m0-genpng-width` | 0 | `width.png`, 195 bytes |
| `m0-genpng-sourcefile-positional` | 0 | `source.txt.png`, 194 bytes |

All successful cases had empty stdout and stderr. The `py2lcov` case
meaningfully enters indentation-based function derivation with a tabbed source
and exposes the pinned Oracle's `args.tabwidth` versus `args.tabWidth` namespace
defect. That failure is bounded and retained as an explicit planning case under
ADR 0004 rather than hidden by `--no-functions`. These runs validate executable
planning argv only; outputs are not Ferricov differential results and do not
establish product parity.

## Contract Effect

- substantive reviewed primary plans: 364 -> 370
- explicit M0 behavior gaps: 167 -> 161
- fixed primary/interaction projections: 366 -> 372
- product evidence: unchanged and empty

## Verification

- suite schema and fixture ownership tests
- stable behavior fragment regeneration
- current behavior validation expected at `public=531`,
  `reviewed_primary=370`, `m0_gaps=161`
- behavior mutation tests retain fail-closed plan-binding checks
