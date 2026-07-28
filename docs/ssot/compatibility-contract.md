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
| command-line parsers | 353 definitions and explicit parser policies across 10 commands; 41 generated tokens observed under 2 profiles | not started | 6 Oracle policy probes and 82 profile-resolution probes; no product evidence |
| command option review | all 394 reviewed: 346 public, 41 generated tokens, 7 internal | not started | default profile: 9 unique abbreviations, 2 ambiguous, 30 unknown; POSIX profile: 41 unknown |
| positional arguments | 9 parser-backed command forms; `xml2lcovutil.py` consumes none | not started | none |
| `lcovrc` | all 158 reviewed: 153 public, 5 not applicable | not started | none |
| tracefile formats | pending | not started | none |
| upstream test map | all 205 files mapped and reviewed | not started | planning sources only; no product evidence |
| support scripts/callbacks | all 23 scripts reviewed and public; external runner and qualified `perl2lcov` adapter accepted, Perl host proposed in ADR 0002 | not started | 23 reviewed primary behavior plans; no product evidence |
| behavior planning | primary skeletons cover all 531 public entries | not started | 23 reviewed primary plans; all 4 critical interaction domains reviewed; 508 primary reviews open |
| GCC/LLVM matrix | Oracle lane has reproducible package/tree/key-file/smoke closures and a runtime-validated manifest; compiler capture and release matrices remain open | not started | Oracle environment evidence only |
| installation layout | 321-entry installed tree pinned and reproduced across two no-cache builds | not started | environment evidence only |

The inventory is generated from pinned parser definitions, manuals, help output,
configuration templates, installation manifests, and tests. Schema and semantic
validation enforce exact parser counts and policies, unique entry identities,
totals, source classification invariants, generated-token resolution counts,
source file/line integrity, and byte-stable regeneration. Six focused Oracle
probes pin unique and ambiguous abbreviation plus the argparse ordering
boundary. Another 82 Oracle probes verify every committed generated-token and
profile resolution, including the accepted abbreviation targets. Complete option behavior,
configuration precedence, interactions, and converter shared-option
reachability still require differential cases before M0 can close.

The differential harness has passed six Oracle self-test cases and one
intentional reverse failure. These results verify evidence collection only;
they do not increase Ferricov compatibility status.

## Release Claims

- Pre-alpha and alpha releases publish exact matrix status and make no drop-in
  claim.
- A command can be called compatible only when its complete inventory passes.
- The project can claim LCOV 2.5 drop-in compatibility only after every row in
  this contract passes on the declared platform/toolchain matrix.
