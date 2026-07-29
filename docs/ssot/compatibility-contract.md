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
| `lcovrc` | all 158 reviewed: 153 public, 5 not applicable | not started | 22 Oracle configuration cases cover discovery, precedence, include, expansion, and selected diagnostics; no product evidence |
| environment and discovery | 19 named variables, 1 dynamic input, 5 discovery paths, and all 36 direct `$ENV` lines reviewed in a separate contract | not started | 22 bindings to retained Oracle configuration cases; no product evidence |
| tracefile formats | 20 record tags, 2 lexical rules, all 15 reader matcher lines, all 18 writer emission lines, and 21 per-record malformed fixtures reviewed in a separate contract | not started | 52 retained Oracle observations across 36 fixtures; reference-only, with 28 planned M1 tracefile IDs still unmapped |
| upstream test map | all 205 files mapped and reviewed | not started | planning sources only; no product evidence |
| support scripts/callbacks | all 23 scripts reviewed and public; external runner and qualified `perl2lcov` adapter accepted, Perl host proposed in ADR 0002 | not started | 23 reviewed primary behavior plans; no product evidence |
| behavior planning | primary plans cover all 531 public entries | not started | 69 reviewed primary plans, including 40 CLI parser entries plus 8 configuration-semantic slices with 67 bindings; all 4 critical interaction domains reviewed; 462 primary reviews open |
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

The aggregate M0 correctness baseline retains 148 raw observations from the
pinned LCOV 2.5 Oracle in
`compat/correctness/baselines/m0-cli-oracle-v2.5/`. A second independent capture
passed semantic replay comparison for exit status, stdout, stderr, and the
filesystem tree. The total comprises 126 CLI cases and 22 configuration cases.
Replay ignores timing and image identity and normalizes only
the random `geninfo` tempfile token; raw diagnostics are retained verbatim.
This is Oracle qualification evidence only. It does not provide Ferricov
product compatibility evidence, and the baseline status explicitly keeps
`product_compatibility_evidence=false`.

Forty public CLI primary entries already exercised by that contract
now have reviewed authored plans across argparse, direct Getopt, and shared
Getopt parser families. Their 154 exact suite-case bindings are planning links
only: every entry remains `evidence_status=planned`, every evidence array is
empty, and no product compatibility status changes.

Eight additional configuration-semantic plans bind 67 exact suite cases and
review six previously open primary targets. These plans separate CLI parser
ownership from configuration discovery and precedence ownership. Their Oracle
observations remain reference-only; all eight plans stay `planned` with empty
evidence arrays.

The standalone environment contract is generated independently of the public
inventory. It pins exact source text for the 36 direct `$ENV` lines across six
upstream files, reviews 19 named inputs plus one dynamic configuration input,
and orders five configuration discovery paths. Schema, source-closure, Oracle
binding, mutation, and committed-byte checks fail closed. Its source and Oracle
observations do not provide Ferricov product compatibility evidence.

The standalone tracefile contract is also independent of the public inventory.
It closes the pinned source inventory over every reader matcher and canonical
writer emission, distinguishes the three reader-only tags, and binds the
retained corpus and Oracle baseline by exact hashes. Its 52 observations are
Oracle references only. They do not resolve the 28 M1 tracefile IDs that still
lack executable mappings and do not provide Ferricov product compatibility
evidence.

## Release Claims

- Pre-alpha and alpha releases publish exact matrix status and make no drop-in
  claim.
- A command can be called compatible only when its complete inventory passes.
- The project can claim LCOV 2.5 drop-in compatibility only after every row in
  this contract passes on the declared platform/toolchain matrix.
