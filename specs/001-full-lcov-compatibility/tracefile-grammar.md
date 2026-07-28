# LCOV 2.5 Tracefile Grammar

## Status And Authority

This document is a proposed normative M1 tracefile contract and a reviewed M0
decision draft for Ferricov. It records observed behavior of LCOV `v2.5` at
commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` and defines the planned M1
acceptance cases. The pinned executable remains the behavioral Oracle when
source, manual text, and observed execution disagree.

This document is an M0 Week 2 readiness artifact. It does not authorize M1
implementation and does not mark any M1 acceptance case as passing. M1 remains
blocked by the gates in [plan.md](plan.md), [tasks.md](tasks.md), and the
[compatibility contract](../../docs/ssot/compatibility-contract.md).

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL in this document are to be
interpreted as normative requirements.

## Compatibility Principle

Ferricov MUST distinguish these two contracts:

1. **Accepted input behavior:** all canonical, legacy, malformed, and
   permissive forms that the pinned Oracle accepts, rejects, ignores, coerces,
   or reports through an ignorable error class.
2. **Canonical output behavior:** the strict deterministic form emitted by the
   pinned `TraceFile::write_info` implementation.

Observed parser permissiveness is a compatibility requirement for input. It is
not a recommendation and MUST NOT broaden Ferricov's canonical writer. In
particular, prefix-only matches, ignored summary payloads, `KF`, trailing junk,
and legacy function records MUST be tested as observed input behavior but MUST
NOT be emitted as canonical output.

## Pinned Upstream Sources

All source references below are relative to the pinned upstream checkout. The
links point to the immutable commit.

| Anchor | Upstream reference | Purpose |
| --- | --- | --- |
| `U-FEATURE-DEFAULTS` | [`lib/lcovutil.pm:209-211`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L209-L211) | Default function, branch, and MC/DC parser flags |
| `U-TRACE-OPTIONS` | [`lib/lcovutil.pm:1180-1290`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L1180-L1290) | Test-name and coverage feature controls |
| `U-IO` | [`lib/lcovutil.pm:3570-3685`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L3570-L3685) | Plain, standard-stream, and `.gz` input/output |
| `U-COUNT` | [`lib/lcovutil.pm:3928-3971`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L3928-L3971) | Line-count validation and accumulation |
| `U-BRANCH-ELEMENT` | [`lib/lcovutil.pm:4092-4140`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4092-L4140) | Branch taken-count validation |
| `U-BRANCH-ORDER` | [`lib/lcovutil.pm:4472-4489`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4472-L4489) | Canonical branch-block ordering |
| `U-MCDC` | [`lib/lcovutil.pm:4585-4636`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4585-L4636) | MC/DC grouping, index, expression, and count updates |
| `U-FUNCTION-COUNT` | [`lib/lcovutil.pm:4983-5024`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4983-L5024) | Function alias count validation and accumulation |
| `U-FUNCTION-MAP` | [`lib/lcovutil.pm:5172-5310`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5172-L5310) | Function definitions, aliases, and legacy count lookup |
| `U-VERSION` | [`lib/lcovutil.pm:6074-6084`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L6074-L6084) | Version repetition constraint |
| `U-READ-PREAMBLE` | [`lib/lcovutil.pm:8896-9064`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L8896-L9064) | Read loop, line normalization, comments, `SF`/`KF`, and section binding |
| `U-READ-RECORDS-1` | [`lib/lcovutil.pm:9068-9215`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9068-L9215) | `VER`, `TN`, `DA`, and function records |
| `U-READ-RECORDS-2` | [`lib/lcovutil.pm:9217-9365`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9217-L9365) | Branch and MC/DC records |
| `U-READ-END` | [`lib/lcovutil.pm:9367-9451`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9367-L9451) | Section commit, ignored summaries, unknown records, and empty filtering |
| `U-WRITE` | [`lib/lcovutil.pm:9473-9682`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9473-L9682) | Canonical tracefile writer |
| `U-TESTCASE-MAPS` | [`lib/lcovutil.pm:6088-6102,6177-6240`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L6088-L6240) | Independent lazy line/function/branch/MC/DC testcase maps |
| `U-MCDC-APPEND` | [`lib/lcovutil.pm:5718-5737`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5718-L5737) | Duplicate per-test MC/DC line failure and aggregate reuse |
| `U-MCDC-LATE-TN` | [`lib/lcovutil.pm:9053-9056,9348-9363,9388-9395`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9053-L9395) | `SF` binds four maps, but MC/DC close appends through the current test name |
| `U-TESTCASE-FILTER-WRITE` | [`lib/lcovutil.pm:9429-9437,9503-9507`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9429-L9507) | Empty-test cleanup and writer enumeration are driven by line-test keys |
| `U-FORMAT-MANUAL` | [`docs/man/geninfo.rst:663-910`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/docs/man/geninfo.rst#L663-L910) | Published tracefile description |
| `U-CONVERTER-HEAD` | [`bin/xml2lcovutil.py:100-222`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/bin/xml2lcovutil.py#L100-L222) | Direct converter header and section framing |
| `U-CONVERTER-DATA` | [`bin/xml2lcovutil.py:353-494`](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/bin/xml2lcovutil.py#L353-L494) | Direct converter branch, function, line, and summary order |

The canonical parser and writer live in a 10,184-line source file. These
bounded anchors are the reviewed ranges; no claim is based on an unbounded
whole-file reading.

## Lexical Processing

The grammar in this document describes logical input lines. Before record
matching, the Oracle performs these steps:

1. Read a line from the tracefile stream.
2. Apply Perl `chomp`.
3. Remove all trailing characters matched by Perl `\s+`.
4. Ignore the line if its first remaining character is `#`.
5. Test `SF` and `KF` before the other record alternatives.
6. Ignore the rest of an excluded or invalid current source section until a
   later `SF` or `KF` is encountered.
7. Match the remaining record alternatives in source order.

A comment marker is recognized only at the beginning of the normalized line.
Leading whitespace before `#` is not a comment under the parser expression.
An empty or whitespace-only line is ignored. Input comments are not stored in
the parsed model; writer comments come only from explicit `add_comments` calls.

The canonical `_read_info` entry point first requires its path to be readable
and a plain file. It then reads regular files and `.gz` files through
`InOutFile`. A `.gz` filename triggers an external `gzip` availability check,
integrity test, and decompression pipe. Empty or corrupt gzip files fail before
record parsing. The generic `InOutFile` utility supports standard input, but
that does not bypass `_read_info`'s earlier plain-file check; command-level
standard-stream behavior requires a separate Oracle case.

No explicit encoding layer or `binmode` appears in `U-IO`. Perl character
classes such as `\d`, `\s`, and `\W` therefore remain Oracle-defined for raw
non-ASCII input and MUST be pinned by acceptance cases before Ferricov claims
byte-preserving compatibility.

## Parser Record Grammar

The `Parser expression` column reproduces the pinned Perl regular expression.
`Start` means the expression has `^` but no `$`; unconsumed suffix text can be
accepted. `Full` means both start and end are anchored after trailing
whitespace removal. Semantic validation occurs after a syntactic match.
Backslashes before `|` in table cells escape Markdown column delimiters; they
are not characters in the upstream regular expression or output.

| Class | Record | Parser expression | Anchor | Canonical output |
| --- | --- | --- | --- | --- |
| Framing | comment | `^#` | Start | `#<comment>` only at file start |
| Framing | blank | `^\s*$` | Full | Never emitted |
| Test | `TN` | `^TN:([^,]*)(,diff)?` | Start | `TN:<testname>` |
| Source | `SF` | `^[SK]F:(.*)` | Start | `SF:<source-path>` |
| Source, observed alternate | `KF` | `^[SK]F:(.*)` | Start | Never emitted |
| Version | `VER` | `^VER:(.+)$` | Full | `VER:<version>` when defined |
| Line | `DA` | `^DA:(\d+),([^,]+)(,([^,\s]+))?` | Start | `DA:<line>,<count>[,<checksum>]` |
| Function, legacy | `FN` | `^FN:(\d+),((\d+),)?(.+)$` | Full | Never emitted |
| Function, legacy | `FNDA` | `^FNDA:([^,]+),(.+)$` | Full | Never emitted |
| Function, current | `FNL` | `^FNL:(\d+),(\d+)(,(\d+))?$` | Full | `FNL:<index>,<start>[,<end>]` |
| Function, current | `FNA` | `^FNA:(\d+),([^,]+),(.+)$` | Full | `FNA:<index>,<count>,<alias>` |
| Branch | `BRDA` | `^BRDA:(\d+),([ef]?)(U?)(\d+),(.+)$` | Full | `BRDA:<line>,[e\|f][U]<block>,<branch>,<taken>` |
| MC/DC | `MCDC` | `^MCDC:(\d+),(U?)(\d+),([tf]),(\d+),(\d+),(.+)$` | Full | `MCDC:<line>,[U]<group-size>,<sense>,<count>,<index>,<expression>` |
| Terminator | `end_of_record` | `^end_of_record` | Start | Exact `end_of_record` |
| Summary | `FNF` | `^(FN\|BR\|L\|MC)[HF]` | Start | `FNF:<count>` |
| Summary | `FNH` | `^(FN\|BR\|L\|MC)[HF]` | Start | `FNH:<count>` |
| Summary | `BRF` | `^(FN\|BR\|L\|MC)[HF]` | Start | `BRF:<count>` when non-excluded branches exist |
| Summary | `BRH` | `^(FN\|BR\|L\|MC)[HF]` | Start | `BRH:<count>` with `BRF` |
| Summary | `MCF` | `^(FN\|BR\|L\|MC)[HF]` | Start | `MCF:<count>` when MC/DC records exist |
| Summary | `MCH` | `^(FN\|BR\|L\|MC)[HF]` | Start | `MCH:<count>` with `MCF` |
| Summary | `LF` | `^(FN\|BR\|L\|MC)[HF]` | Start | `LF:<count>` |
| Summary | `LH` | `^(FN\|BR\|L\|MC)[HF]` | Start | `LH:<count>` |

The summary expression validates only the tag prefix. It does not require a
colon, numeric payload, end anchor, canonical position, or unique occurrence.
For example, a line beginning `FNF` is ignored even if the remaining payload is
not a canonical summary. Ferricov MUST reproduce the Oracle result for planned
permissiveness cases, but its writer MUST emit exact tag, colon, and decimal
count forms.

An unrecognized nonblank, noncomment line is an `ERROR_FORMAT` condition. The
configured ignore and stop-on-error policy determines whether parsing
continues, returns a nonzero result, or terminates.

## Record Semantics

### Test And Source Binding

- The initial test name is the empty string.
- `TN:` with no payload is valid.
- The `TN` base capture stops at the first comma. Perl `\W` characters in that
  base are replaced with `_`, and a warning is emitted after parsing if a name
  changed.
- The exact optional `,diff` capture is appended after sanitization. `genhtml`
  renders such a name as `<base> (converted)`.
- Because `TN` is prefix-only, other comma suffixes and text after a matched
  `,diff` can remain unconsumed. This is observed permissiveness, not canonical
  syntax.
- When `forget_testcase_names` or `--forget-test-names` activates
  `TraceFile::ignore_testcase_name`, every matched `TN` is replaced with the
  default empty name after parsing and sanitization.
- `TN` changes the name used by the next `SF` or `KF`. It does not rebind the
  line, function, or branch maps already selected for the current source.
  MC/DC is exceptional: close paths ignore the `$mcdcMap` bound at `SF` and
  call `testcase_mcdc($testname)` with the current name. A late `TN` can
  therefore attach the complete open MC/DC block to a different testcase.
- `SF` and `KF` share the same implementation. Their payload is passed to
  `ReadCurrentSource::resolve_path`. An empty or whitespace-only payload raises
  `ERROR_FORMAT`, marks the current file as skipped, and does not create a
  valid section.
- A new `SF` or `KF` selects or creates per-file data and binds all four
  per-test maps using the current test name. It resets current-format function
  indices and branch-block construction state. It does not explicitly reset an
  already open MC/DC block.

`M0-TF-TN-MCDC-001` uses these exact bytes:

```text
TN:A
SF:/m0/late-tn.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,edge,1
MCDC:1,1,t,1,0,cond
DA:1,1
TN:B
MCDC:1,1,f,1,0,cond
end_of_record
```

M0 MUST capture aggregate plus all four testcase-family key/value snapshots and
canonical output. The decision points are ownership of the open MC/DC block,
whether `B` exists only in the MC/DC map, whether `A` has empty MC/DC, and
whether writer enumeration from the line-test key omits `B`'s MC/DC. Variants
close the first block by a new MC/DC line and by `end_of_record`.

`M0-TF-MCDC-SF-001` uses these exact bytes:

```text
TN:A
SF:/m0/first.c
MCDC:1,1,t,1,0,first
DA:1,1
TN:B
SF:/m0/next.c
MCDC:2,1,t,1,0,second
DA:2,1
end_of_record
```

It MUST freeze which source/test receives the old open block, duplicate-line
failure, aggregate/testcase snapshots, diagnostics, and output. These are
upstream-only M0 decision probes mapped to `M1-TF-021`, `M1-TF-022`, and
`M1-TF-026`; they do not claim compatibility.

### Version

- `VER` requires a current source and a nonempty payload.
- The version is stored per source file, not per test name.
- Repeating the identical version for the same source is accepted.
- Attempting to set a different second version for the same source triggers an
  unconditional `die`, not an ignorable version error.
- The canonical writer emits at most one `VER` per section when the source has
  a version.

### Line Data And Checksums

- The `DA` line capture is Perl `\d+`. A value numerically less than or equal to
  zero raises `ERROR_FORMAT`; if ignored, the invalid line is retained.
- Repeated `DA` records for the same line and test name add their counts.
- The optional checksum is any nonempty token containing neither a comma nor
  Perl whitespace. Because the expression is not end-anchored, later suffix
  text can remain unconsumed.
- When checksum verification is active and source content is available, the
  Oracle compares the recorded checksum with `Digest::MD5::md5_base64` of the
  source line. Missing or different checksums raise `ERROR_VERSION`.
- The canonical writer emits a stored checksum or computes the same MD5 base64
  value when checksum output is enabled. It omits the field when no checksum is
  available.

### Current Function Form

- `FNL` declares an index, start line, and optional end line. Its index is local
  to the current `SF` or `KF` binding.
- A duplicate `FNL` index triggers an unconditional `die`.
- `FNA` MUST syntactically follow an `FNL` for the same index somewhere in the
  current section. An unknown index triggers an unconditional `die`.
- One `FNL` MAY have multiple `FNA` aliases. Repeating an alias adds its count.
  The alias is the final nonempty capture and can contain commas.
- The parser does not enforce positive current-format start or end lines at
  `FNL` read time. The canonical writer reports a format error for a function
  start less than or equal to zero.
- The manual requires at least one `FNA` per `FNL` and contiguous aliases. The
  parser's index map does not itself enforce either layout rule. Oracle cases
  MUST distinguish parser acceptance from canonical writer structure.

### Legacy Function Form

- `FN:<start>,<name>` and `FN:<start>,<end>,<name>` declare legacy functions.
  The name is the final nonempty capture and can contain commas. A name whose
  first segment is decimal digits followed by a comma can instead satisfy the
  optional end-line capture; the pinned regular expression decides that
  ambiguity.
- Legacy start and present end lines numerically less than or equal to zero
  raise `ERROR_FORMAT`, subject to function suppression patterns and ignore
  policy.
- `FNDA:<count>,<name>` adds a count to an already declared function name.
  An unknown name raises `ERROR_MISMATCH` and does not create a function.
- Repeated definitions are reconciled through `FunctionMap`; inconsistent name,
  start, or end locations use the upstream mismatch and inconsistent-data
  rules.
- LCOV 2.5 reads `FN` plus `FNDA`, but `TraceFile::write_info` writes only
  `FNL` plus `FNA`. Ferricov MUST preserve legacy input semantics and MUST NOT
  emit the legacy form in canonical output.
- Current and legacy records are not selected by an explicit file-level mode.
  Mixed input therefore reaches the shared function map and MUST be covered by
  an Oracle case rather than rejected by an invented grammar rule.

### Branch Data

- The second `BRDA` field consists of an optional type (`e` for exception or
  `f` for fallthrough), optional `U`, and a decimal block token with no
  delimiter between them. `e` and `f` are mutually exclusive by grammar.
- The final capture is split at its last comma. The prefix is the branch
  expression and the suffix is the taken count. Expressions can contain
  commas. Canonical input has a final delimiter comma. If it is absent,
  Perl `rindex` returns `-1`, and the subsequent `substr` calls can still
  construct an empty or truncated expression and a taken capture from the
  malformed tail. That observed edge requires an Oracle case; it MUST NOT be
  rejected or accepted solely from a cleaner grammar assumption.
- Taken is `-` for not evaluated or a Perl numeric count. Other values use the
  numeric error rules below.
- A line numerically less than or equal to zero raises `ERROR_FORMAT`; if
  ignored, it is retained.
- Input block numbers identify boundaries while reading. The model re-derives
  element indices in appearance order, and the writer re-numbers output blocks
  contiguously from zero for each line.
- Records for one logical input block SHOULD be contiguous. Revisiting the same
  line and block after another block creates another positional block rather
  than looking it up by its original number.
- `U` is ignored when `ignore_unreachable_flag` is active. Otherwise it marks
  the branch excluded. Exception filtering can also set exclusion.

### MC/DC Data

- `MCDC` uses field order line, optional `U` plus group size, sense, count,
  index, expression. Count and index are decimal captures; sense is exactly
  `t` or `f`; the final expression is nonempty and can contain commas.
  `lib/lcovutil.pm:9335-9363` assigns the first decimal after sense to count and
  the second to index; `lib/lcovutil.pm:9630-9638` writes the same order.
- A line numerically less than or equal to zero raises `ERROR_FORMAT`; if
  ignored, it is retained.
- Groups are keyed by group size. Within a group, the first new index MUST be
  zero and later new indices MUST be contiguous. A gap raises `ERROR_FORMAT`;
  ignored gaps are still appended at the next array position.
- Repeating an existing index with a different expression raises
  `ERROR_INCONSISTENT_DATA`; the existing expression remains authoritative and
  the count update still follows the configured error policy.
- Repeating the same line, group, index, and sense adds the count.
- `U` is ignored when `ignore_unreachable_flag` is active. Otherwise it marks
  that expression sense excluded.
- All MC/DC records for one source line MUST be contiguous. Returning to a
  source line after its per-test MC/DC block has closed can trigger the hard
  `MCDC already defined` failure.
- The canonical writer emits two records for each expression index in `t`, `f`
  order.

### Summary Records

- Parsed `FNF`, `FNH`, `BRF`, `BRH`, `MCF`, `MCH`, `LF`, and `LH` values never
  populate or validate model totals. They are ignored and recomputed on write.
- `FNF` counts function groups, not individual aliases. `FNH` counts a group
  once if any alias has a positive count.
- `BRF` and `BRH` exclude branches marked `U`. Excluded `BRDA` records remain
  in output. The pair is omitted if there are no non-excluded branches.
- `LF` counts emitted `DA` records. `LH` counts emitted line records with a
  value greater than zero.
- The implementation increments `MCF` by two for every stored MC/DC expression
  and increments `MCH` for every nonzero sense before checking its exclusion
  marker. The manual says excluded MC/DC conditions are not counted. This is an
  unresolved source/manual conflict and MUST be settled by `M1-TF-042` against
  the pinned executable before implementation.

### Terminator

- Any normalized line beginning `end_of_record` matches the parser terminator.
  Suffix text is observed permissiveness.
- A terminator unions current per-test line, function, and branch data into the
  per-file summaries, closes the current branch block, closes current MC/DC
  data, optionally computes a version, and checks branch counts.
- The terminator does not fully clear the current source binding. Repeating it
  or placing records after it without a new `SF` is not canonical and MUST be
  defined by Oracle cases rather than a cleaner invented state machine.
- At end of input, a source whose aggregate line map has no entries is removed.
  If no valid source remains, the parser raises `ERROR_EMPTY`. A section with
  line data but no effective terminator can therefore disappear as empty.

## Numeric Semantics

`DA`, `FNDA`, `FNA`, and the taken portion of `BRDA` do not use an integer-only
grammar. After their broad syntactic captures, the Oracle applies
`Scalar::Util::looks_like_number` in its pinned Perl runtime.

Ferricov MUST reproduce that predicate's observed acceptance set through
Oracle fixtures. It MUST NOT replace it with a decimal-integer parser or infer
validity from the upstream diagnostic phrase "non-integer". The acceptance
matrix MUST include signed zero, positive integers, decimal fractions,
scientific notation, malformed exponent forms, whitespace-bearing captures,
special numeric spellings accepted or rejected by the pinned Perl runtime, and
values around the configured excessive-count threshold.

After numeric recognition:

- A value less than zero raises `ERROR_NEGATIVE` and becomes zero if that error
  is ignored.
- A nonnumeric value raises `ERROR_FORMAT` and becomes zero if that error is
  ignored.
- A value greater than `excessive_count_threshold` raises
  `ERROR_EXCESSIVE_COUNT` but is not coerced to zero when the error is ignored.
- `-` is a special valid `BRDA` taken value and contributes zero hits.
- MC/DC counts are restricted syntactically to Perl `\d+` and do not pass
  through the same `looks_like_number` validation path.
- Parsed summary payloads have no numeric semantics because their entire
  payload is ignored.

Every numeric error case MUST compare model value, message category, stream,
exit status, and continuation behavior. A parser-only unit assertion is not
sufficient evidence.

`M0-TF-NUMERIC-001` starts from
`tests/lcov/format/format.info:4-39` and freezes these exact atoms:

| Family | Atom | Expected decision under required ignore |
| --- | --- | --- |
| `DA` | `-3` | `negative`; retained semantic zero |
| `DA` | `1.a0e+19` | `format`; retained semantic zero |
| `DA` | `1.0e+19` | numeric; `excessive` when threshold is 1,000,000; value retained if ignored |
| `FNDA` | `-2` | `negative`; retained semantic zero |
| `FNDA` | `1.5eb+20` | `format`; retained semantic zero |
| `FNDA` | `1.5e+20` | numeric; `excessive` at the fixture threshold; value retained if ignored |
| `FNDA` and `BRDA` | `-0` | numeric signed-zero decision; record semantic value and rewritten bytes |
| `BRDA` | `-1` | `negative`; retained semantic zero |
| `BRDA` | `-` | valid never-evaluated branch state |
| `BRDA` | `1.67+20` | `format`; retained semantic zero |
| `BRDA` | `1.67e+20` | numeric; `excessive` at the fixture threshold; value retained if ignored |

Runs cover default stop, one/two ignores, threshold 1,000,000, and keep-going,
and retain lexeme, Perl numeric class, category, semantic value, stream, exit,
and rewritten bytes. Additional integer/fraction/exponent/`Inf`/`NaN`
candidates remain blocked until this exact baseline is complete.

## Parser State, Ordering, And Repetition

The recommended input order is the canonical writer order below. The parser is
more permissive, but it is stateful rather than generally order-independent.

| Input action | State and repetition behavior |
| --- | --- |
| `TN` | Replaces the pending/current test name. It affects maps bound by the next source record and also the testcase selected when an open MC/DC block closes; it does not rebind already selected line/function/branch maps. |
| `SF` or `KF` | Opens or reuses source data, binds per-test maps, resets `FNL` indices and branch construction. It does not implicitly commit a prior unterminated section or explicitly reset an open MC/DC block. |
| Repeated `VER` | Same value is accepted; a different value for the same source dies. |
| Repeated `DA` | Counts add for the same source, test, and line. |
| Repeated `FNDA` or `FNA` | Counts add for an existing function alias. |
| Repeated `FNL` index | Dies, even if the payload is identical. |
| Repeated `BRDA` | Positional. It adds elements or blocks according to contiguous line/block transitions; it is not a keyed overwrite. |
| Repeated `MCDC` | Same line/group/index/sense adds counts; expression changes report inconsistency; noncontiguous line reuse can die. |
| Repeated summary | Ignored without comparison. |
| Repeated terminator | Re-applies section-close logic to still-bound state and is noncanonical. Oracle evidence is required for any claimed behavior. |

Function, branch, and MC/DC records are ignored after syntactic recognition
when their corresponding coverage feature is disabled. Summary records remain
ignored regardless of feature flags. Ferricov MUST cover both enabled and
disabled modes so disabled data does not accidentally create model state or
diagnostics. At module initialization, function coverage is enabled while
branch and MC/DC coverage are disabled; command and configuration processing
can change those flags before tracefile parsing.

The parser accepts category orderings that differ from the writer. The pinned
fixture `tests/lcov/format/format.info:1-43`, for example, places `DA`, `LF`, and
`LH` before legacy function and branch records. Flexible category order MUST be
supported where state prerequisites are satisfied. It does not relax these
dependencies:

- Data records require a current source binding.
- Current `FNA` requires a previously declared current `FNL` index.
- Legacy `FNDA` requires a function name already known to the function map.
- Records composing one branch block SHOULD remain contiguous for stable
  positional identity.
- Records composing one MC/DC source line MUST remain contiguous.
- A section requires effective close behavior to survive empty-file filtering.

## Canonical Writer Contract

Canonical output is the exact deterministic subset emitted by `U-WRITE`. Given
the same semantic model, feature flags, path-resolution configuration, checksum
mode, and comments, Ferricov MUST emit byte-identical record ordering and field
formatting unless a separately approved normalization is added to the
compatibility contract. No tracefile normalizer is currently approved.

The writer orders source files with Perl lexical `sort`, then orders test names
with Perl lexical `sort` within each source. It emits one section for each
source/test pair represented by line data. Added comments precede all sections
in insertion order.

```text
#<comment> ...

TN:<testname>
SF:<resolved-source-path>
[VER:<version>]

[FNL:<index>,<start>[,<end>]
 FNA:<index>,<count>,<alias>
 ...]
[FNF:<function-groups-found>]
[FNH:<function-groups-hit>]

[BRDA:<line>,[e|f][U]<block>,<branch>,<taken>
 ...]
[BRF:<non-excluded-branches-found>]
[BRH:<non-excluded-branches-hit>]

[MCDC:<line>,[U]<group-size>,<sense>,<count>,<index>,<expression>
 ...]
[MCF:<conditions-found>]
[MCH:<conditions-hit>]

DA:<line>,<count>[,<checksum>]
...
LF:<lines-found>
LH:<lines-hit>
end_of_record
```

Optional brackets describe feature- or data-dependent emission; they are not
literal output.

Canonical ordering inside a section is:

1. Current-format functions, sorted numerically by start line. Each `FNL` gets
   a sequential index beginning at zero; its aliases are lexical-sorted and
   contiguous. `FNF` then precedes `FNH`.
2. Branches, sorted numerically by line. Blocks on a line sort by signature
   length, then lexical signature, then original appearance index. Elements
   retain block order. Output block numbers are reassigned contiguously from
   zero per line. `BRF` then precedes `BRH` when emitted.
3. MC/DC, sorted numerically by line. Group-size hash keys use Perl lexical
   `sort`, not numeric sort. Expression indices follow stored array order. Each
   index emits `t` before `f`. `MCF` then precedes `MCH` when emitted.
4. Lines, sorted numerically. `LF` precedes `LH`, followed by the exact
   `end_of_record` line.

The writer MUST NOT emit `KF`, `FN`, `FNDA`, blank separator lines, permissive
tag suffixes, malformed summary payloads, or a suffixed terminator. It MUST NOT
preserve ignored input summaries or comments that were not explicitly added to
the output model.

## Direct Converter Alternate Order

`xml2lcov` and `py2lcov` use `bin/xml2lcovutil.py` and write accepted tracefiles
directly rather than calling `TraceFile::write_info`. Their output order is a
public converter behavior and MUST be tested separately from canonical
re-serialization.

The direct converter writes one `TN` when the converter object is created, then
zero or more source sections:

```text
TN:<testname>

SF:<source-path>
[VER:<version>]
[BRDA records in XML line and condition order]
[FNL/FNA pairs in discovered function order]
[DA records in numeric line order]
[LF, LH]
[BRF, BRH]
[FNF, FNH]
end_of_record
```

The summary-family order follows the Python dictionary insertion order:
line, branch, function. A summary pair is omitted when its found count is zero.
The converter emits no MC/DC records. It uses the current `FNL`/`FNA` function
form. Its `BRDA` records use block zero, a numeric condition identifier, and
taken values zero or one.

This alternate order is valid parser input. Ferricov's converter-compatible
commands MUST match it when those commands are implemented. Reading this output
and writing it through the canonical writer MAY reorder records but MUST
preserve the semantic model.

`gendesc` is not a tracefile converter. Its `TN` and `TD` records belong to the
separate test-description sidecar parsed by `genhtml`. `TD` is not a tracefile
record and MUST reach the tracefile parser's unknown-record behavior if placed
in a coverage tracefile.

## Error And Failure Contract

The following distinctions are observable and MUST not be collapsed into one
generic parse failure:

| Condition | Upstream behavior |
| --- | --- |
| Unknown nonblank record | `ERROR_FORMAT` |
| Empty `SF` or `KF` payload | `ERROR_FORMAT`; current section becomes skipped |
| Zero `DA`, legacy function, `BRDA`, or `MCDC` line | `ERROR_FORMAT`; invalid value retained if ignored |
| Nonnumeric count | `ERROR_FORMAT`; count becomes zero if ignored |
| Negative count | `ERROR_NEGATIVE`; count becomes zero if ignored |
| Excessive count | `ERROR_EXCESSIVE_COUNT`; count retained if ignored |
| Missing or different verified checksum | `ERROR_VERSION` |
| Legacy count for unknown function | `ERROR_MISMATCH`; no function created |
| MC/DC index gap | `ERROR_FORMAT`; continuation mutates the next stored position if ignored |
| MC/DC expression change | `ERROR_INCONSISTENT_DATA`; existing expression retained |
| Duplicate `FNL` index | Unconditional `die` |
| `FNA` for unknown index | Unconditional `die` |
| Different repeated source version | Unconditional `die` |
| Noncontiguous duplicate per-test MC/DC line | Can trigger unconditional `MCDC already defined` failure |
| No surviving source with aggregate line data | `ERROR_EMPTY` |

M1 evidence MUST capture raw stdout, raw stderr, exit status, produced files,
and semantic output after ignored errors. Exact error category and continuation
behavior are required even when message text is later assigned to the shared
runtime milestone.

## Observed Permissiveness Versus Recommended Form

The following behavior is deliberately classified as **observed input
permissiveness**:

- `TN`, `DA`, summary tags, and `end_of_record` can match without consuming the
  full normalized line.
- Summary tags do not require a colon or valid count.
- `KF` opens a source section through the same branch as `SF`.
- `TN` comma suffixes can be partially ignored.
- Current function aliases need not be contiguous for parser lookup.
- Category families can appear outside canonical writer order.
- Ignored format, negative, excessive, version, mismatch, and inconsistent
  errors can permit parsing to continue with coercion or retained data.

Ferricov MUST reproduce these results only where pinned Oracle cases confirm
them. Documentation, examples, converters, and the writer SHOULD use the
canonical form. New Ferricov-only permissiveness is prohibited.

## Open Gaps Requiring Oracle Decisions

1. **`KF` provenance:** `KF` occurs only through `^[SK]F:` in the reviewed
   pinned tree. It has no manual entry, fixture, writer, or explanatory comment.
   Its parser behavior is known; its intended name, provenance, and support
   status are unknown. It remains an observed alternate input, not a canonical
   record.
2. **Non-ASCII character classes and invalid UTF-8:** the input layer has no
   explicit encoding mode, while record expressions use Perl `\d`, `\s`, and
   `\W`. Exact byte behavior, locale sensitivity, and diagnostic rendering need
   executable fixtures.
3. **Excluded MC/DC summaries:** `U-WRITE` counts stored MC/DC senses before
   inspecting the exclusion marker, while `U-FORMAT-MANUAL` says excluded
   conditions are not included in `MCF` or `MCH`. The executable Oracle decides.
4. **Line summary documentation order:** the manual lists `LH` before `LF`; the
   writer emits `LF` before `LH`. Canonical output follows the writer, while the
   parser ignores both in either order.
5. **Function manual wording:** the manual introduces current `FNL`/`FNA`, then
   describes legacy `FN` and subsequently `FNDA`. The implementation establishes
   the actual contract: both legacy records are read, but neither is written.
6. **Prefix permissiveness stability:** the source expressions clearly accept
   suffixes, but the upstream suite does not exhaustively pin every suffix. M1
   MUST add exact cases rather than generalize beyond observed examples.

No gap may be resolved by choosing a cleaner grammar without an Oracle result
and spec update.

### Claim-To-Case Traceability

| Claim family | Source anchor | Stable cases |
| --- | --- | --- |
| Byte framing, comments, suffix trimming, unknown input | `U-IO`, `U-READ-PREAMBLE`, `U-READ-END` | `M1-TF-001`, `M1-TF-002`, `M1-TF-016`, `M1-TF-060`, `M1-TF-061` |
| `TN`, `SF`/`KF`, late `TN`, testcase filtering/writing | `U-READ-PREAMBLE`, `U-TESTCASE-MAPS`, `U-MCDC-LATE-TN`, `U-TESTCASE-FILTER-WRITE` | `M0-TF-TN-MCDC-001`, `M0-TF-MCDC-SF-001`, `M1-TF-003` through `M1-TF-006`, `M1-TF-021`, `M1-TF-022`, `M1-TF-026` |
| Version and checksum | `U-VERSION`, `U-READ-RECORDS-1`, `U-WRITE` | `M1-TF-007`, `M1-TF-008`, `M1-TF-035`, `M1-TF-043` |
| Current and legacy functions | `U-FUNCTION-COUNT`, `U-FUNCTION-MAP`, `U-READ-RECORDS-1` | `M1-TF-009`, `M1-TF-010`, `M1-TF-011`, `M1-TF-024`, `M1-TF-044` |
| Branch records, ordering, and exclusion | `U-BRANCH-ELEMENT`, `U-BRANCH-ORDER`, `U-READ-RECORDS-2` | `M1-TF-013`, `M1-TF-025`, `M1-TF-041`, `M1-TF-042` |
| MC/DC records, close ownership, and duplicate line | `U-MCDC`, `U-MCDC-APPEND`, `U-MCDC-LATE-TN`, `U-WRITE` | `M1-TF-014`, `M1-TF-021`, `M1-TF-022`, `M1-TF-026`, `M1-TF-042` |
| Summaries, terminators, repeated close, canonical writer | `U-READ-END`, `U-WRITE` | `M1-TF-012`, `M1-TF-015`, `M1-TF-023`, `M1-TF-028`, `M1-TF-040` through `M1-TF-046` |
| Numeric classification and continuation | `U-COUNT`, `U-BRANCH-ELEMENT`, `U-FUNCTION-COUNT`, `M0-TF-NUMERIC-001` fixture anchor | `M1-TF-030` through `M1-TF-036` |
| Direct converters | `U-CONVERTER-HEAD`, `U-CONVERTER-DATA` | `M1-TF-050`, `M1-TF-051`, `M1-TF-052` |
| Scale, limits, and fuzz | `U-IO`, `U-READ-PREAMBLE`, coverage-model resource contract | `M0-RSRC-MEASURE-001`, `M1-TF-062`, `M1-TF-063`, `M1-TF-064` |

Ranges in this review table are human-readable summaries only. The executable
manifest MUST expand them into individual IDs.

### Executable Mapping And Phase Boundary

The canonical manifest is planned at `compat/cases/m1-tracefile.json`. It MUST
bind every `M1-TF-*` ID to exact input hashes, runner command, parser/config
profile, source anchors, expected raw/semantic artifacts, evidence directory,
and two independent statuses:

- `oracle_baseline` runs during M0 against the pinned upstream executable.
  Decision probes needed to approve the grammar/model run here before M1 exists.
  A completed baseline is not a compatibility pass.
- `ferricov_parity` runs during M1 only after the retained go/no-go approval.
  It compares Ferricov to the retained baseline and may be `pass`,
  `not_applicable`, or `blocked`.

The current `compat/fixtures/m0-tracefiles/oracle-cases.json` has candidate
coverage for exactly these 19 IDs:

`M1-TF-001`, `M1-TF-004`, `M1-TF-006`, `M1-TF-008`, `M1-TF-010`,
`M1-TF-012`, `M1-TF-015`, `M1-TF-016`, `M1-TF-030`, `M1-TF-031`,
`M1-TF-032`, `M1-TF-033`, `M1-TF-034`, `M1-TF-036`, `M1-TF-040`,
`M1-TF-042`, `M1-TF-044`, `M1-TF-061`, and `M1-TF-062`.

Its free-form compound `requirement` labels are not semantically validated and
its baselines lack the aggregate plus four-family testcase snapshots. These 28
IDs have no current exact executable mapping and remain explicit blockers:

`M1-TF-002`, `M1-TF-003`, `M1-TF-005`, `M1-TF-007`, `M1-TF-009`,
`M1-TF-011`, `M1-TF-013`, `M1-TF-014`, `M1-TF-020`, `M1-TF-021`,
`M1-TF-022`, `M1-TF-023`, `M1-TF-024`, `M1-TF-025`, `M1-TF-026`,
`M1-TF-027`, `M1-TF-028`, `M1-TF-035`, `M1-TF-041`, `M1-TF-043`,
`M1-TF-045`, `M1-TF-046`, `M1-TF-050`, `M1-TF-051`, `M1-TF-052`,
`M1-TF-060`, `M1-TF-063`, and `M1-TF-064`.

No M1 parser implementation is authorized until the M0 baseline phase resolves
the model-shaping decisions and the executable manifest/approval record exist.

## Planned M1 Acceptance Cases

These IDs are stable planned case identities. They do not indicate execution or
pass status. The upstream-only `oracle_baseline` phase runs during M0; the
Ferricov `ferricov_parity` phase runs during M1 only after authorization.

### Record And Framing Cases

| Case ID | Required coverage |
| --- | --- |
| `M1-TF-001` | Plain input framing: LF, CRLF, final line with and without newline, trailing Perl whitespace, blank lines |
| `M1-TF-002` | Column-zero comments before, inside, and after sections; leading-space `#`; read/write comment retention behavior |
| `M1-TF-003` | Canonical empty and nonempty `TN`; valid word names; forget-test-names mode; writer repetition per section |
| `M1-TF-004` | `TN` sanitization, exact `,diff`, other comma suffixes, suffix after `,diff`, and warning behavior |
| `M1-TF-005` | Canonical `SF`, repeated source/test sections, path resolution, empty and whitespace-only payloads |
| `M1-TF-006` | Undocumented `KF` parity with `SF`, empty payload, repetition, and proof that canonical output uses `SF` |
| `M1-TF-007` | `VER` absent, present, repeated equal, repeated different, and per-source versus per-test scope |
| `M1-TF-008` | `DA` with and without checksum, repeated line accumulation, checksum verify/store/rewrite behavior |
| `M1-TF-009` | Current `FNL`/`FNA`: optional end, multiple/comma-bearing aliases, repeated alias, missing alias, noncontiguous alias, zero lines |
| `M1-TF-010` | Legacy `FN`/`FNDA`: optional-end ambiguity, comma-bearing names, repeated definitions/counts, unknown name, legacy-to-current rewrite |
| `M1-TF-011` | Mixed legacy/current function records sharing names and locations; mismatch and merge outcomes |
| `M1-TF-012` | All eight summary tags in canonical, missing-colon, nonnumeric, duplicate, misplaced, and suffixed forms |
| `M1-TF-013` | `BRDA` vanilla, exception, fallthrough, `U` with both unreachable-flag modes, `-`, numeric and comma-bearing expressions, malformed tail |
| `M1-TF-014` | `MCDC` group sizes, indices, both senses, `U` with both unreachable-flag modes, comma-bearing expressions, repeated counts |
| `M1-TF-015` | Exact and suffixed `end_of_record`, missing terminator, duplicate terminator, records after terminator |
| `M1-TF-016` | Unknown tags, `TD`, leading whitespace before known tags, case changes, and configured format-ignore behavior |

### State, Order, And Repetition Cases

| Case ID | Required coverage |
| --- | --- |
| `M1-TF-020` | Canonical order and accepted cross-family order permutations with equivalent semantics |
| `M1-TF-021` | `TN` before `SF`; after `SF` before MC/DC; during an open MC/DC block closed by line transition; during a block closed by terminator; all four testcase-family ownership snapshots and canonical output |
| `M1-TF-022` | New source before terminator, including while MC/DC is open; old/new source ownership, EOF filtering, empty sections, diagnostics, and surviving aggregate line data |
| `M1-TF-023` | Repeated source/test sections and additive line/function/branch/MC/DC model behavior |
| `M1-TF-024` | `FNL` index scope, duplicate index hard failure, unknown `FNA` hard failure |
| `M1-TF-025` | Branch block contiguity, noncontiguous reuse, input block gaps, expression identity, canonical renumbering |
| `M1-TF-026` | MC/DC line contiguity, index gaps, expression mismatch, repeated sense, duplicate-line hard failure |
| `M1-TF-027` | Function, branch, and MC/DC records with each coverage feature enabled and disabled |
| `M1-TF-028` | Summary records before, within, and after data families; proof that payload and repetition do not affect totals |

### Numeric And Failure Cases

| Case ID | Required coverage |
| --- | --- |
| `M1-TF-030` | `M0-TF-NUMERIC-001` exact atoms plus `0`, `+1`, `1.5`, `1e3`, `Inf`, `+Inf`, `-Inf`, `Infinity`, `NaN`, and `nan`; Perl class, semantic value, category, threshold, and rewritten bytes |
| `M1-TF-031` | Nonnumeric and malformed exponent counts for `DA`, `FNDA`, `FNA`, and `BRDA`; digit-only MC/DC rejection; format-ignore coercion |
| `M1-TF-032` | Negative counts and negative zero; `ERROR_NEGATIVE`, continuation, and resulting model values |
| `M1-TF-033` | Counts below, at, and above `excessive_count_threshold`; suppression patterns where applicable |
| `M1-TF-034` | Zero and otherwise invalid line/start/end fields across `DA`, `FN`, `FNL`, `BRDA`, and `MCDC` |
| `M1-TF-035` | Missing, mismatched, duplicate, and recomputed checksums with version-ignore behavior |
| `M1-TF-036` | Error policy matrix: default stop, `--ignore-errors`, keep-going/stop-on-error, stream, exit, and output effects |

### Writer And Round-Trip Cases

| Case ID | Required coverage |
| --- | --- |
| `M1-TF-040` | Complete canonical writer sequence and exact tag/field formatting for all current records |
| `M1-TF-041` | File, test, function, alias, branch block, MC/DC group, sense, and line sort rules, including lexical group size |
| `M1-TF-042` | Recomputed `FNF/FNH`, `BRF/BRH`, `MCF/MCH`, and `LF/LH`, including excluded branch and MC/DC decisions |
| `M1-TF-043` | Canonical comments and checksum modes; proof that ignored input summaries/comments are not blindly reproduced |
| `M1-TF-044` | Proof that canonical output never emits `KF`, `FN`, `FNDA`, malformed prefixes, or suffixed terminators |
| `M1-TF-045` | Parse-write-parse semantic preservation for canonical, legacy, permissive, and ignored-error corpora |
| `M1-TF-046` | Byte-identical repeated writes from identical model/configuration inputs |

### Converter, Transport, And Scale Cases

| Case ID | Required coverage |
| --- | --- |
| `M1-TF-050` | `xml2lcov` direct record order, global `TN`, optional summaries/version, no MC/DC |
| `M1-TF-051` | `py2lcov` direct record order with derived functions enabled and disabled |
| `M1-TF-052` | Direct converter output parsed and canonically rewritten without semantic loss |
| `M1-TF-060` | Plain file, standard stream where supported, valid gzip, missing gzip utility, empty/corrupt gzip |
| `M1-TF-061` | Non-ASCII and invalid UTF-8 bytes in source paths, test names, function names, branch expressions, MC/DC expressions, and versions |
| `M1-TF-062` | Deterministic scale profiles with recorded seed/hash, bytes, records, sections, family cardinalities, maximum field/record, exact model/output, wall/CPU, and peak RSS |
| `M1-TF-063` | `M0-RSRC-MEASURE-001` exact size/cardinality matrix; any product limit, over-limit diagnostic/exit/model state, and reviewed deviation; remains blocked until measured |
| `M1-TF-064` | Corpus seeds from every record/legacy/prefix/state/hard-failure case mapped to all named `M1-FZ-*` targets, shrink/replay artifacts, CI 60-second and scheduled 15-minute budgets; remains blocked until executable |

The deterministic `M1-TF-062` generator profiles are:

| Profile | Sources | Testcases/source | Records/source/test | Maximum field |
| --- | --- | --- | --- | --- |
| `scale-small-v1` | 1 | 1 | 16 `DA` plus one of every enabled non-line family | 64 bytes |
| `scale-medium-v1` | 64 | 4 | 256 per family | 4 KiB |
| `scale-large-v1` | 256 | 4 | 128 per family | 64 KiB |
| `scale-cardinality-v1` | 1 | 4 | 16,384 distinct keys per family | 1 KiB |

Generation seed is SHA-256 of the literal profile name, interpreted as bytes;
paths/test names/expressions are deterministic counter encodings. The generator
MUST retain its version, seed, output SHA-256, byte length, section/record/family
counts, and maximum field/record. These are correctness/performance fixtures,
not product acceptance limits.

The exact M0 resource measurement sizes, harness input/record/cardinality caps,
RSS/time budgets, failure oracle, minimization, and regression-retention rules
are normative in
[coverage-model.md](coverage-model.md#resource-and-fuzz-budgets). Upstream
product limits remain unmeasured. Any Ferricov rejection limit stays blocked
unless the measurement matrix and a required safety deviation approve it.

## M1 Evidence And Exit Conditions

Each acceptance case MUST retain:

- case ID, exact source anchor, and grammar requirement reference
- phase status: `oracle_baseline` and `ferricov_parity`
- pinned Oracle executable and source commit identity
- raw input bytes
- relevant feature flags, error policy, locale, platform, and Perl runtime
- raw stdout, raw stderr, and exit status
- output file bytes and filesystem metadata where applicable
- parsed semantic model or an independently reviewable semantic snapshot
- Ferricov result and exact unexplained differences

For canonical writer cases, raw tracefile bytes are the comparison oracle. For
permissive, legacy, or malformed input, both the semantic result and failure
contract are required. A normalized success result MUST NOT hide a record,
counter, ordering, error-category, stream, or path-byte difference.

This grammar is complete as a reviewed source inventory only when every record
row and every open gap has a linked executable case. Product compatibility
remains zero until the corresponding M1 parity cases pass. M0 upstream-only
decision probes MUST run before the go/no-go review; they do not wait for M1.
Parser implementation MUST NOT start before the M0 exit gate, approved model
specification, executable case manifest, retained Oracle correctness/resource
baselines, and hashed approval record are complete. `M1-TF-063` and
`M1-TF-064` remain blockers, not implied limits or passes.
