# Compatibility Contract

## Definition Of Complete Compatibility

A surface is compatible only when all applicable observable behavior matches
LCOV 2.5 for the supported environment:

1. accepted and rejected CLI forms, aliases, defaults, and combinations
2. configuration discovery, precedence, types, and invalid-value handling
3. coverage data meaning for lines, functions, branches, conditions, and MC/DC
4. deterministic output data and semantically equivalent nondeterministic data
5. stdout/stderr channel, exit status, warning class, and ignore semantics
6. filesystem effects, output tree, links, source mapping, and callbacks
7. supported GCC/LLVM and platform integration

An option is not complete merely because it parses. Its success, failure, side
effects, output, and interaction cases require differential coverage.

## Comparison Rules

- Coverage totals and counters must match exactly.
- Deterministic tracefiles must match after documented canonicalization.
- HTML must have equivalent normalized DOM, navigation, anchors, source-line
  state, thresholds, and assets. Generated timestamps and explicitly unordered
  metadata may be normalized.
- Exit status and output channel must match exactly.
- Stable documented warnings and errors must match their category and text.
- Callback inputs, outputs, environment, and failure propagation must match.
- Any allowed normalization must be listed here before it is used by tests.

The approved normalization registry is `compat/normalizers.md`. The runner
rejects unknown normalizers, non-exact exit/filesystem comparisons, different
declared environments, duplicate case/comparison identities, and compatibility
suites that resolve to the same actual executable identity. Docker results
record both image and executable SHA-256 identities. Filesystem evidence
includes content, raw path bytes, Unix metadata, symlink targets, and hardlink
relationships where supported.

## Inventory Status

| Surface | Inventory | Implementation | Differential evidence |
| --- | --- | --- | --- |
| `lcov` | candidate generated | not started | none; harness self-test only |
| `genhtml` | candidate generated | not started | none; harness self-test only |
| `geninfo` | candidate generated | not started | none; harness self-test only |
| `lcovrc` | 130 candidates generated | not started | none |
| tracefile formats | pending | not started | none |
| auxiliary commands | 7 candidates generated | not started | none |
| support scripts/callbacks | 23 scripts found | not started | none |
| GCC/LLVM matrix | pending | not started | none |
| installation layout | command/script manifest found | not started | none |

The inventory will be generated from upstream manuals, help output,
configuration templates, installation manifests, and tests, then reviewed for
surfaces that static extraction cannot find.

The differential harness has passed six Oracle self-test cases and one
intentional reverse failure. These results verify evidence collection only;
they do not increase Ferricov compatibility status.

## Release Claims

- Pre-alpha and alpha releases publish exact matrix status and make no drop-in
  claim.
- A command can be called compatible only when its complete inventory passes.
- The project can claim LCOV 2.5 drop-in compatibility only after every row in
  this contract passes on the declared platform/toolchain matrix.
