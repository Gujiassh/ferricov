# LCOV 2.5 Coverage Model

## Status And Authority

This document is a proposed normative M1 coverage-model contract and a reviewed
M0 decision draft for Ferricov. It records reviewed behavior of LCOV `v2.5` at
commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`. The pinned executable remains the
behavioral Oracle when source, manual text, and observed execution disagree.

This is an M0 Week 2 readiness artifact. It does not authorize M1
implementation, mark an Oracle case as passing, or increase the product
compatibility percentage. M1 remains blocked by [plan.md](plan.md),
[tasks.md](tasks.md), and the
[compatibility contract](../../docs/ssot/compatibility-contract.md).

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL in this document are normative.
The companion [tracefile grammar](tracefile-grammar.md) defines accepted record
syntax and parser state. This document defines the semantic state that the Rust
model must be able to represent without loss.

## Model Principles

1. Compatibility is defined by observable LCOV 2.5 behavior, not by a cleaner
   interpretation of the tracefile manual.
2. The model MUST preserve byte strings, numeric meaning, positional identity,
   exclusions, and aggregate/testcase divergence required by the Oracle.
3. The model MUST remain independent of CLI parsing, filesystem traversal,
   subprocesses, callbacks, report rendering, and benchmark code.
4. Parser provenance, diagnostics, semantic coverage state, and canonical
   serialization configuration MUST be separate concerns.
5. The model MUST NOT require every accepted state to be valid canonical
   output. Ignored errors can produce states that a strict constructor would
   normally reject.
6. No implementation may simplify a source-observed anomaly until its assigned
   Oracle case resolves whether that anomaly is observable through a supported
   command.

## Pinned Upstream Sources

All upstream links identify the immutable compatibility commit.

| Anchor | Upstream source | Model consequence |
| --- | --- | --- |
| `U-VERSION-MATCH` | [`checkVersionMatch`, lines 2877-2908](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L2877-L2908) | Version equality, callback decision, and ignored mismatch behavior |
| `U-IO` | [`InOutFile`, lines 3570-3685](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L3570-L3685) | Tracefile byte transport without an explicit text decoding layer |
| `U-MAP` | [`MapData`, lines 3809-3890](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L3809-L3890) | Keyed maps and lazy testcase entries |
| `U-COUNT` | [`CountData`, lines 3893-4089](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L3893-L4089) | Counter coercion, cached totals, union, intersection, and difference |
| `U-BRANCH-ELEMENT` | [`BranchElement`, lines 4092-4305](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4092-L4305) | Taken state, type, exclusion, expression, and merge rules |
| `U-BRANCH-BLOCK` | [`BranchBlock` and `BranchLocation`, lines 4307-4583](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4307-L4583) | Ordered branch blocks, signatures, matching, and canonical order |
| `U-MCDC-BLOCK` | [`MCDC_Block` and `MCDC_Expression`, lines 4585-4829](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4585-L4829) | Group-size identity, expression order, two senses, counts, and exclusions |
| `U-FUNCTION-ENTRY` | [`FunctionEntry`, lines 4832-5134](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4832-L5134) | Alias counts, representative name, range, and function-local queries |
| `U-FUNCTION-MAP` | [`FunctionMap`, lines 5136-5428](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5136-L5428) | Location/name indexes and set algebra |
| `U-BRANCH-DATA` | [`BranchData`, lines 5506-5705](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5506-L5705) | Branch totals and set algebra |
| `U-MCDC-DATA` | [`MCDC_Data`, lines 5707-5844](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5707-L5844) | Per-line storage, close-time totals, and set algebra |
| `U-TRACE-INFO` | [`TraceInfo`, lines 5991-6375](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5991-L6375) | Per-source metadata plus independent aggregate and testcase stores |
| `U-PATH-KEY` | [`TraceFile::data`, lines 7350-7382](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L7350-L7382) | Lookup key distinct from first-seen display path |
| `U-FILE-ALGEBRA` | [`TraceFile::merge_tracefile`, lines 7413-7450](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L7413-L7450) | File-level union, intersection, and difference |
| `U-FILTER-STORES` | [`TraceFile::_filterFile`, lines 7982-8010](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L7982-L8010) | Separate testcase and aggregate mutations during filtering |
| `U-BIND` | [`TraceFile::_read_info`, lines 8986-9057](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L8986-L9057) | Empty default testcase and source-time binding of four testcase stores |
| `U-RECORDS` | [`TraceFile::_read_info`, lines 9068-9365](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9068-L9365) | Version, checksum, line, function, branch, and MC/DC mutations |
| `U-CLOSE` | [`TraceFile::_read_info`, lines 9367-9438](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9367-L9438) | Section commit, aggregate updates, and empty filtering |
| `U-WRITE` | [`TraceFile::write_info`, lines 9473-9682](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9473-L9682) | Canonical projection, ordering, and writer totals |
| `U-BRANCH-INTERSECT` | [`BranchData::intersect`, lines 5609-5656](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5609-L5656) | Replacement depends on a merge-reported `changed` flag and needs a repeated-signature cache case |
| `U-MCDC-COMPAT` | [`MCDC_Block::is_compatible` and `merge`, lines 4694-4744](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4694-L4744) | Asymmetric vector comparison and merge; vector lengths are not checked |
| `U-MCDC-EXCLUSION` | [`MCDC_Expression::set`, lines 4768-4786](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L4768-L4786) | Exclusion is sticky; a later non-excluded operand never clears it |
| `U-FUNCTION-REMOVE` | [`FunctionEntry::addAlias` and `removeAliases`, lines 5007-5017 and 5040-5068](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L5007-L5068) | Insertion uses a lexical equal-length tie-break; representative recomputation after removal does not |
| `U-MCDC-LATE-TN` | [`TraceFile::_read_info`, lines 9053-9056, 9352-9357, and 9388-9394](https://github.com/linux-test-project/lcov/blob/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5/lib/lcovutil.pm#L9053-L9394) | Line/function/branch maps bind at `SF`, while MC/DC close looks up the current test name |

These source ranges define behavior to be tested. They do not require Ferricov
to copy the Perl object layout or mutable-global implementation.

## Abstract Model

The following pseudotypes describe semantic responsibilities. They do not
mandate Rust field names or collection implementations.

```text
CoverageDatabase
  sources: map<SourceLookupKey, SourceCoverage>

SourceCoverage
  identity: SourceIdentity
  version: optional<ByteString>
  checksums: map<LineKey, ByteString>
  aggregate: CoverageStore
  testcases: TestcaseStores
  observable_totals: TotalState

CoverageStore
  lines: LineCoverage
  functions: FunctionTable
  branches: BranchCoverage
  mcdc: McdcCoverage

TestcaseStores
  lines: map<TestName, LineCoverage>
  functions: map<TestName, FunctionTable>
  branches: map<TestName, BranchCoverage>
  mcdc: map<TestName, McdcCoverage>
```

`aggregate` and all four testcase-family maps are independent first-class
stores. A conforming implementation MUST NOT replace either side with a lazily
derived view of the other. The four testcase-family key sets MUST remain
representable independently; a unified testcase wrapper MAY be offered only if
it preserves family-map presence as well as empty family values.
`observable_totals` represents any cache or lifecycle-dependent total whose
Oracle result cannot be reproduced by recomputing solely from current points.
It MAY be removed from the final Rust representation only after the relevant
Oracle cases prove recomputation equivalent for every supported operation.

## Byte Strings And Source Identity

`ByteString` MUST preserve every input byte and MUST NOT require UTF-8. It MUST
be usable for source paths, versions, test names, checksums, function aliases,
branch expressions, MC/DC expressions, and output comments. Display conversion
MUST be explicit and MUST NOT alter stored identity.

`SourceIdentity` MUST distinguish:

- the first-seen or otherwise Oracle-selected path emitted by the writer;
- the lookup key used to decide whether two source records address one model
  entry; and
- any raw or resolved path needed only for parser diagnostics or runtime path
  resolution.

Case-sensitive lookup uses the configured path bytes. Case-insensitive lookup
uses Oracle-compatible folding before map access, while preserving the chosen
display path. Unicode case folding is prohibited unless an Oracle case proves
that it matches the pinned Perl runtime. Path substitution and filesystem
resolution belong to the parser/runtime boundary and provide their result to
the model; the model MUST NOT access the filesystem.

`TestName` stores the parser-selected byte identity, including the empty name
and the exact retained `,diff` suffix. The original unsanitized bytes MAY be
retained as diagnostic provenance, but MUST NOT silently become a second
semantic testcase identity. Changing `TN` after a source binding does not rebind
the already-selected line, function, or branch maps. MC/DC is different: close
paths at `U-MCDC-LATE-TN` look up the current test name instead of the
source-bound `$mcdcMap`, so a late `TN` can assign an open MC/DC block to a
different testcase. `M0-TF-TN-MCDC-001` and `M1-TF-021` must freeze the exact
split before implementation.

## Numeric And Counter Representation

No coverage count, line key, function boundary, branch block token, MC/DC group
size, or MC/DC expression index may be modeled as an unqualified `u64`, `i64`,
`f64`, or Rust `String` conversion.

A parsed numeric atom MUST retain enough information to reproduce all of the
following where the Oracle exposes them:

- the original accepted byte lexeme before arithmetic;
- whether Perl treated the scalar as an integer-like or floating-like value;
- zero, signed zero, positive, and negative comparisons;
- addition in the original operation order;
- comparison with `excessive_count_threshold`;
- hash-key identity and numeric sort behavior for digit fields;
- Perl-compatible output formatting after no arithmetic and after arithmetic;
- values larger than Rust integer types and values whose integer precision is
  not preserved by binary floating point.

An implementation MAY use a raw lexeme plus a tagged numeric projection,
arbitrary precision types, or a reviewed Perl-number emulation. It MUST NOT
discard the lexeme on parse or coerce every accepted value through `f64` before
the Oracle cases establish that doing so is lossless.

`CoverageCount` MUST support the Oracle operations `validate`, `add`,
`is_positive`, `is_zero`, and `compare_threshold`. Invalid or negative counts
that continue under ignored errors become semantic zero, while their raw token
and diagnostic remain parser provenance. Excessive counts remain semantic
counts when the error is ignored.

`BranchTaken` is a sum type:

```text
BranchTaken = NeverEvaluated | Evaluated(CoverageCount)
```

`NeverEvaluated` corresponds to `-`, contributes no hit, is the identity when
merged from the right, and is replaced when an evaluated right operand is
merged into a never-evaluated left operand.

MC/DC count fields are syntactically digit-only, but they still MUST preserve
values beyond fixed-width integer limits and reproduce Oracle addition and
formatting. Summary payloads do not become numeric model values because the
parser ignores them.

Line and location keys MUST allow Oracle-retained zero and other ignored-error
states. A public canonical constructor MAY require positive canonical values,
but the parser-facing construction path MUST represent every retained Oracle
state.

## Aggregate And Testcase Stores

Each source has one aggregate store and four testcase-family maps. A testcase
can have line, function, branch, and MC/DC coverage independently, including an
explicit empty value in one family. A source/testcase section is selected from
membership in the line testcase map when the canonical writer emits output;
membership only in another family does not independently create a section.

The stores MUST remain independent because the pinned parser:

- reuses existing testcase-family values when a source/test pair repeats;
- unions the current testcase line, function, and branch values into aggregate
  stores at every effective terminator;
- mutates aggregate MC/DC first and then clones its current block into a
  testcase MC/DC value; and
- applies later filters and repairs to aggregate and testcase-family stores
  through separate traversal paths.

Static source inspection therefore permits aggregate/testcase divergence. In
particular, a repeated source/test section can add a cumulative testcase store
to aggregate state again, and MC/DC construction can expose aggregate counts
inside a later testcase clone. `M1-MD-003`, `M1-MD-019`, and their mapped
tracefile cases MUST decide the exact executable behavior before implementation.

Input `FNF`, `FNH`, `BRF`, `BRH`, `MCF`, `MCH`, `LF`, and `LH` values MUST NOT
be stored as trusted totals. They are ignored parser records. Writer totals,
aggregate summary totals, and any lifecycle cache are separate named views and
MUST NOT be conflated.

## Version And Checksum Scope

`version` is optional and scoped to a source, not a testcase. Repeating an
identical version is a no-op. A different second version during one parsed
database is a hard failure. Set operations validate versions before coverage
mutation; if the mismatch is ignored or callback-approved, the left version
remains authoritative.

`checksums` is a source-level map keyed by line identity. It is independent of
the line coverage maps and may contain entries not emitted by a particular
testcase section. Checksum-enabled parsing stores a checksum after verification
policy is applied. A later checksum for the same line reports a mismatch and,
when continuation is allowed, replaces the earlier value.

Set operations right-overlay checksum entries for union, intersection, and
difference. Canonical serialization emits a stored checksum when checksum
output is enabled; otherwise an external checksum provider may supply the
MD5-base64 value. The model MUST NOT read source files or compute checksums by
itself.

## Line Coverage

`LineCoverage` maps `LineKey` to `CoverageCount` and maintains or derives the
Oracle `found` and `hit` views. A new key increments `found`; a count greater
than zero contributes one hit. Repeating a key adds its count. Removing a key
removes its contribution.

Line union copies right-only keys and adds common counts. Line intersection
keeps common keys and adds their counts; it does not take a minimum. Line
difference removes common keys; it does not numerically subtract counts.

The implementation MUST preserve operand order. It MUST NOT assume that
counter addition is associative or commutative until the numeric Oracle matrix
proves that reordering cannot alter Perl numeric promotion, rounding, or
formatting.

## Functions And Aliases

`FunctionTable` requires two coherent indexes:

- start location to one `FunctionGroup`; and
- every alias name to its `FunctionGroup`.

One start location identifies one function group. All function names defined at
that location are aliases, even when they originated from different records.
A group contains the start, optional end, alias-to-count map, representative
name, and total count across aliases.

The representative is the shortest alias after applying the upstream lambda
penalty; equal effective lengths use lexical order. It is a report/model view,
not a reason to discard any alias. Function-found counts groups by default;
function-hit counts a group once when at least one alias is positive. The
function-alias filter can request alias-level found/hit views, so both views
MUST remain representable.

Repeated alias counts add. An unknown legacy `FNDA` reports mismatch and does
not create a function. A repeated name at another start reports inconsistent
data and, if ignored, can move the existing group to the smallest observed
start. Conflicting end lines within definition processing report inconsistent
data and can select the greatest accepted end. Cross-table union at an existing
start is left-biased for stored range data and merges aliases.

Function union merges groups by start and adds aliases. Function intersection
keeps common starts and common aliases, adding common alias counts. Function
difference removes common aliases and deletes a group when no aliases remain.
All mutations MUST keep the location and alias indexes coherent. Representative
recomputation after removing the current representative does not apply the
lexical equal-length tie-break used during insertion; `M1-ALG-FUNCTION-REP-001`
must capture the hash-seed and operand-order result rather than assuming the
lexically smallest survivor.

The model MUST allow ignored-error states such as start zero, end zero, end
before start, and groups produced by mixed legacy/current records. The
canonical serializer, not the core storage type, owns writer-time diagnostics.

## Ordered Branch Coverage

Branch coverage is hierarchical and partly positional:

```text
BranchCoverage
  lines: map<LineKey, BranchLine>

BranchLine
  blocks_in_model_order: sequence<BranchBlock>

BranchBlock
  model_position: integer
  signature: sequence<BranchType>
  edges: sequence<BranchEdge>

BranchEdge
  derived_index: integer
  taken: BranchTaken
  expression: optional<ByteString>
  kind: Vanilla | Exception | Fallthrough
  excluded: boolean
```

The input block token is parser transition state, not durable branch identity.
The parser creates a new block when line or input block changes, derives edge
indexes by appearance, and assigns model block positions contiguously. Revisiting
an earlier input block after another transition creates another model block.

A block signature is only its ordered sequence of branch kinds. Expressions do
not participate in compatibility. Blocks on a line match by signature and nth
occurrence of that signature. Common matched edge counts add positionally;
right-only signature occurrences are copied on union. The left expression is
retained when matched expressions differ. Exclusion mismatches report and
resolve to excluded when continuation is allowed.

Branch intersection retains the pairable prefix of each common signature and
adds matched counts. Branch difference removes the number of leading left
blocks represented by the matching right signature occurrences and retains
the remainder. Found/hit writer totals exclude excluded edges; excluded edges
remain serializable as `U` records.

Intersection replacement at `U-BRANCH-INTERSECT` is conditional on whether a
matched edge merge reports `changed`. A repeated-signature left block can
therefore survive when the replacement was built but no merge reports a change.
`M1-ALG-BRANCH-CACHE-001` must compare semantic blocks and cached totals before
Ferricov chooses a conventional intersection.

Model order and canonical order are distinct. Canonical output sorts blocks by
signature length, lexical signature, and model position, then reassigns output
block numbers from zero. Edge order inside a block is stable.

## MC/DC Coverage

MC/DC coverage is hierarchical:

```text
McdcCoverage
  lines: map<LineKey, McdcLine>

McdcLine
  groups: map<GroupSizeKey, sequence<McdcExpression>>

McdcExpression
  stored_position: integer
  declared_index: NumericAtom
  expression: ByteString
  false_sense: SenseCoverage
  true_sense: SenseCoverage

SenseCoverage
  count: CoverageCount
  excluded: boolean
```

There is at most one stored group for a group-size key on a line. The model
MUST NOT invent a second discriminator for independent same-sized groups unless
the Oracle requires it. Expressions are stored in vector order. An ignored
index gap appends at the next stored position while retaining enough parser
provenance to report the declared index. Canonical output uses stored position,
not a repaired interpretation of the declared index.

Each expression owns independent false and true counts and exclusions. Both
senses MUST exist in the semantic representation even when only one was seen;
the unseen sense has zero count and no exclusion. Repeated sense counts add.
An expression mismatch reports inconsistent data, retains the existing
expression, and then follows continuation policy for the count update.

MC/DC union and intersection add compatible sense counts at common lines and
group-size keys. Union copies a right-only line. Within a common compatible
line, both union and intersection copy a right-only group because the shared
merge helper does so. Incompatible common records report inconsistent data and
follow Oracle continuation behavior. MC/DC difference removes an entire left
line when the right side has that line; it does not subtract individual groups,
expressions, senses, or counts.

Compatibility checks use group-size keys, expression position, and expression
bytes. They do not use a normalized expression AST. The check is asymmetric and
does not compare vector lengths: a longer left vector can dereference an
undefined right element and die, while a shorter left vector can ignore extra
right expressions during merge. Exclusion mismatch reports, and exclusion is
sticky from either operand because `MCDC_Expression::set` only sets and never
clears the flag. These are blocked decisions in
`M1-ALG-MCDC-VECTOR-001` and `M1-ALG-MCDC-001`.

The canonical writer emits groups in Perl lexical key order, expressions in
stored order, and senses in `t`, then `f` order. The source writer counts every
stored sense before testing exclusion, while the manual says excluded MC/DC is
not counted. `M1-MD-009` decides the canonical total rule.

## Total Views And Invariants

The model MUST expose total computations by explicit purpose:

- `line_totals(store)` counts stored line keys and positive counts;
- `function_group_totals(store)` counts groups and groups with any positive
  alias;
- `function_alias_totals(store)` counts aliases and positive aliases;
- `branch_writer_totals(store)` excludes excluded edges;
- `mcdc_writer_totals(store)` follows the result of `M1-MD-009`;
- `aggregate_summary_totals(source)` reproduces aggregate lifecycle behavior;
  and
- `section_writer_totals(testcase)` is recomputed from the emitted testcase
  section and ignores input summary records.

These functions MUST NOT share a cache merely because their values agree on
canonical fixtures. Any cached `found` or `hit` value MUST be checked after
every insertion, removal, clone, merge, filter, and ignored-error continuation.
Repeated close and MC/DC clone cases MUST demonstrate whether cached values are
observable before Rust chooses recomputation instead of explicit state.

The following structural invariants always apply to a successfully returned
semantic model:

- every source map key resolves to exactly one source identity;
- every function alias reverse index points to its containing group;
- every branch block signature equals the ordered kinds of its edges;
- every branch derived edge index equals its position in that block after
  parser construction;
- every MC/DC expression has exactly two sense states;
- aggregate and testcase-family stores are never silently synchronized;
- ignored summary payloads never affect semantic totals; and
- no canonical serialization mutation changes the input semantic model.

## Set Algebra

The model-level operations are `union`, `intersect`, and `difference`. They are
ordered, mutating-left operations because version choice, checksum overlay,
numeric promotion, branch occurrence matching, and ignored-error recovery can
be order-dependent.

At source level:

- union merges common sources and adds right-only sources;
- intersection merges common sources and removes left-only sources; and
- difference mutates common sources, retains left-only sources, and ignores
  right-only sources.

At coverage-family level, the operation uses the rules in the preceding
sections. Version checking happens before family mutation. Checksum right
overlay happens for all three operations.

The upstream testcase loops visit testcase names present on the right and use
lazy accessors on the left. Static source inspection indicates that intersection
and difference do not explicitly remove left-only testcase maps and can create
empty right-only testcase maps. Ferricov MUST NOT impose conventional set
semantics until `M1-MD-014` pins the executable result.

Full commutativity, associativity, and idempotence are NOT invariants. Focused
properties MAY assert those laws only for a documented subset whose versions,
checksums, counter representations, branch multiplicities, exclusions, and
diagnostic outcomes make the law valid.

Public CLI orchestration, glob order, parallel scheduling, warning emission,
and exit policy are M2/shared-runtime concerns. M1 model operations MUST accept
an explicit operand order so later orchestration can reproduce the Oracle
without hidden reordering.

## Exact Algebra Fixture Contract

Every block below is exact ASCII input ending in one LF, with no omitted summary
records. The common Oracle command matrix is:

```sh
lcov --branch --mcdc-coverage -o <case>-union.info \
  --add-tracefile <left> --add-tracefile <right> \
  --ignore-errors empty,inconsistent,mismatch
lcov --branch --mcdc-coverage -o <case>-intersect.info \
  <left> --intersect <right> --ignore-errors empty,inconsistent,mismatch
lcov --branch --mcdc-coverage -o <case>-difference.info \
  <left> --subtract <right> --ignore-errors empty,inconsistent,mismatch
```

Each operation also runs with operands reversed. Evidence MUST contain raw
inputs/output, streams, exit, the aggregate store, all four independent
testcase-family maps, writer totals, and ordered operation trace. The small
integer expectations below are assertions; numeric-promotion, cache, vector,
and representative quirks remain Oracle decisions.

### `M1-ALG-LINE-001`

`md010-left.info`:

```text
TN:common
SF:/m1/algebra-line.c
DA:10,1
DA:20,2
DA:40,9007199254740992
end_of_record
```

`md010-right.info`:

```text
TN:common
SF:/m1/algebra-line.c
DA:10,4
DA:30,8
DA:40,1
end_of_record
```

Among the small-integer keys, union has lines 10/20/30 with counts 5/2/8,
intersection has line 10 with count 5, and difference has line 20 with count 2.
Line 40 remains in union/intersection, is removed by difference as a common key,
and is the ordered numeric-addition probe; it has no predeclared union or
intersection result until `M1-MD-004` records both operand orders and rewritten
bytes.

### `M1-ALG-FUNCTION-001` And `M1-ALG-FUNCTION-REP-001`

`md011-left.info`:

```text
TN:common
SF:/m1/algebra-function.c
FNL:0,10,20
FNA:0,2,aa
FNA:0,3,b
FNL:1,30,40
FNA:1,5,left_only
DA:1,1
DA:2,1
end_of_record
```

`md011-right.info`:

```text
TN:common
SF:/m1/algebra-function.c
FNL:0,10,99
FNA:0,7,aa
FNA:0,11,c
FNL:1,50,60
FNA:1,13,right_only
DA:2,1
end_of_record
```

At start 10, union retains the left range and aliases
`aa=9,b=3,c=11`; intersection retains `aa=9`; difference retains `b=3`.
The left-only start 30 and right-only start 50 follow the operation rules. The
representative-removal variant is byte-identical except that left start 10 has
aliases `aa`, `ab`, and `ba`, all count 1, and right contains only
`aa`. It runs with `PERL_HASH_SEED` and `PERL_PERTURB_KEYS` recorded across
at least eight fresh processes; no lexical survivor is assumed.

### `M1-ALG-BRANCH-001` And `M1-ALG-BRANCH-CACHE-001`

`md012-left.info`:

```text
TN:common
SF:/m1/algebra-branch.c
BRDA:10,0,left-a,1
BRDA:10,e0,left-b,-
BRDA:10,1,left-c,2
BRDA:10,e1,left-d,0
DA:1,1
DA:2,1
DA:10,1
end_of_record
```

`md012-right.info`:

```text
TN:common
SF:/m1/algebra-branch.c
BRDA:10,U7,right-a,4
BRDA:10,e7,right-b,5
DA:2,1
DA:10,1
end_of_record
```

The fixture freezes nth repeated-signature matching, left expression retention,
`-` transitions, count addition, right-side exclusion, and difference removal
of only the leading matched occurrence. The cache subcase is exactly the right
fixture with `U7` changed to `7` and taken values changed from `4,5` to
`1,-`, matching the left first block's exclusion and taken states. It compares
whether intersection retains the unmatched second left block when no matched
merge reports `changed`.

### `M1-ALG-MCDC-001`, `M1-ALG-MCDC-VECTOR-001`, And
### `M1-ALG-MCDC-EXPR-001`

`md013-left.info`:

```text
TN:common
SF:/m1/algebra-mcdc.c
MCDC:20,2,t,1,0,a
MCDC:20,2,f,0,0,a
MCDC:20,2,t,2,1,b
MCDC:20,2,f,0,1,b
DA:1,1
DA:2,1
DA:20,1
end_of_record
```

`md013-right.info`:

```text
TN:common
SF:/m1/algebra-mcdc.c
MCDC:20,U2,t,3,0,a
MCDC:20,2,f,4,0,a
MCDC:20,2,t,5,1,b
MCDC:20,2,f,6,1,b
MCDC:20,3,t,1,0,c
MCDC:20,3,f,0,0,c
MCDC:20,3,t,1,1,d
MCDC:20,3,f,0,1,d
MCDC:20,3,t,1,2,e
MCDC:20,3,f,0,2,e
DA:2,1
DA:20,1
end_of_record
```

This freezes common sense-count addition, sticky exclusion, right-only group
copy in both union and intersection, and whole-line MC/DC difference.
`md013-expr-right.info` is exactly `md013-right.info` with both group-2
expression-1 bytes changed from `b` to `B`.
`md013-vector-long.info` is exactly `md013-right.info` after deleting all
group-2 records and replacing `DA:2,1` with consecutive `DA:1,1` and
`DA:3,1`. `md013-vector-short.info` has exactly the same wrapper, group-3
indices 0 and 1 only, and `DA:2,1`, `DA:3,1`, `DA:20,1`. Thus both
difference directions retain a line-test key. Both long/short operand orders
MUST capture exception,
diagnostic, retained model, and output; neither may be normalized into symmetric
compatibility.

### `M1-ALG-TESTCASE-LINE-001` Through
### `M1-ALG-TESTCASE-MCDC-001`

For each family `F`, generate exact left/right files from this byte template:

```text
TN:common
SF:/m1/testcase-<F>.c
<COMMON-RECORD>
<KEEPALIVE-DA>
end_of_record
TN:<SIDE>_only
SF:/m1/testcase-<F>.c
<SIDE-RECORD>
<KEEPALIVE-DA>
end_of_record
```

Left substitutes `SIDE=left`; right substitutes `SIDE=right`. The exact
records are:

| Family/ID | Common left | Common right | Side record | Keepalive |
| --- | --- | --- | --- | --- |
| line / `M1-ALG-TESTCASE-LINE-001` | `DA:10,1` | `DA:10,4` | `DA:20,2` | empty |
| function / `M1-ALG-TESTCASE-FUNCTION-001` | `FNL:0,10,20` then `FNA:0,1,common` | `FNL:0,10,20` then `FNA:0,4,common` | `FNL:0,30,40` then `FNA:0,2,side` | `DA:1,1` |
| branch / `M1-ALG-TESTCASE-BRANCH-001` | `BRDA:10,0,common,1` | `BRDA:10,0,common,4` | `BRDA:20,0,side,2` | `DA:1,1` |
| MC/DC / `M1-ALG-TESTCASE-MCDC-001` | `MCDC:10,1,t,1,0,common` | `MCDC:10,1,t,4,0,common` | `MCDC:20,1,t,2,0,side` | `DA:1,1` |

The word `then` means the two records are emitted on consecutive LF-terminated
lines; an empty keepalive emits no line. For union, intersection, and difference in both
operand orders, snapshots MUST report key presence and value independently for
line, function, branch, and MC/DC testcase maps, including empty lazy maps. The
canonical output alone is insufficient because section emission is selected
from line-test membership.

## Canonical Serialization Boundary

Canonical serialization is a projection of semantic model plus explicit
context:

```text
SerializationContext
  function_coverage_enabled
  branch_coverage_enabled
  mcdc_coverage_enabled
  checksum_output_enabled
  source_path_projection
  optional_checksum_provider
  output_comments
```

The model MUST NOT contain a filesystem handle, callback object, CLI option
parser, or output stream. The serializer MAY receive pure provider interfaces
from the surrounding tracefile/runtime layer.

Given identical semantic model, serialization context, provider results, and
platform/locale qualification, serialization MUST produce byte-identical
output. No tracefile normalizer is approved. The required family and sort order
is defined in the [canonical writer contract](tracefile-grammar.md#canonical-writer-contract).

Canonical serialization MUST:

- select sections from source/testcase line data;
- emit `TN`, `SF`, optional `VER`, current functions, branches, MC/DC, lines,
  recomputed writer totals, and exact `end_of_record`;
- convert legacy function semantics to `FNL` and `FNA`;
- reassign function and branch output indexes;
- preserve required byte strings and count formatting;
- omit ignored input summaries and input comments;
- emit only explicitly supplied output comments; and
- avoid changing aggregate or testcase model state.

The serializer MUST NOT emit `KF`, `FN`, `FNDA`, raw malformed records,
permissive suffixes, or direct-converter alternate ordering. A separate raw AST
or evidence artifact MAY preserve those input bytes for diagnostics and Oracle
review, but they are not part of canonical semantic output.

## Malformed-But-Ignored States

The parser and model boundary MUST distinguish three outcomes:

1. hard failure with no successful semantic result;
2. categorized error with continuation and a coerced semantic value; and
3. categorized error with continuation and a retained noncanonical value.

The returned model MUST support at least these retained states when the Oracle
continues: line zero; function start or end zero; end before start; excluded
branch and MC/DC senses; noncanonical branch block transitions; MC/DC index
gaps; existing-expression authority after a mismatch; and coverage that differs
between aggregate and testcase stores.

Nonnumeric and negative general counts are coerced to semantic zero when their
errors are ignored. Excessive counts are retained. An unknown legacy function
count does not create a function. Duplicate current function indexes, unknown
current function indexes, different repeated source versions, and duplicate
per-test MC/DC insertion can be hard failures.

Diagnostic category, message context, raw token, source path, record number,
stdout/stderr destination, and continuation policy are parser/runtime evidence,
not fields that define semantic equality. They MUST still be retained by the
Oracle harness and tested with the mapped cases.

## Semantic Equality

Semantic equality for M1 MUST compare:

- source lookup identity and selected display path bytes;
- source version and checksum entries;
- aggregate and every testcase-family map independently, including family-map
  key presence and explicit empty values;
- exact counter semantic values and any lexeme state that affects later output;
- function groups, ranges, aliases, representative, and alias counts;
- branch line/block/edge order, kind, expression, taken state, and exclusion;
- MC/DC line/group/expression order, expression bytes, both sense counts, and
  exclusions; and
- observable total state not reproducible from current points.

Semantic equality MUST ignore input record family order where the model has no
positional meaning, ignored summary payloads, discarded input comments, raw
legacy spelling after canonical conversion, parser-only diagnostics, and
reassigned canonical output indexes.

Any relaxation of semantic equality is a normalizer decision and requires an
explicit compatibility-contract update before use.

A model is `canonically serializable` only when every semantic field included
in equality can be reconstructed from the sections emitted by the canonical
writer under the fixed context. In particular, its aggregate stores and
observable totals must equal the Oracle reconstruction from exactly the
testcase sections that the writer will emit. An accepted input may produce a
valid semantic model that is not canonically serializable, such as a repeated
section whose lifecycle updates are not represented in output records. The
model MUST represent that state; the writer MUST NOT silently claim a lossless
round trip for it.

## Parse, Write, And Property Invariants

For a model `M`, canonical writer `W`, parser `P`, and fixed context `C`, M1
MUST establish these properties over all applicable fixtures:

1. `P(W(M, C), C)` is semantically equal to `M` for every canonically
   serializable model.
2. `W(P(W(M, C), C), C)` is byte-identical to `W(M, C)`.
3. For accepted input `B`, `P(W(P(B, C), C), C)` is semantically equal to
   `P(B, C)`. If a source-observed accepted state fails because canonical output
   cannot reconstruct aggregate or lifecycle state, `M1-MD-019` blocks this
   property until the contract records an explicit reviewed resolution. A test
   MUST NOT hide the difference with an unapproved semantic normalizer.
4. Repeated canonical writes do not mutate `M` and return identical bytes.
5. Legacy `FN`/`FNDA` and current `FNL`/`FNA` fixtures with equivalent
   semantics canonicalize to equivalent current-form output.
6. Ignored summary payload changes do not change the semantic model or
   canonical totals.
7. Branch output renumbering preserves block occurrence and edge semantics.
8. MC/DC sense output reordering to `t`, then `f` preserves both sense states.
9. General-count addition and branch `NeverEvaluated` behavior match the pinned
   numeric matrix without silent saturation, wrap, or precision loss.
10. Arbitrary byte input cannot cause a Rust panic, memory unsafety, unbounded
    allocation beyond the configured limit, or invalid UTF-8 conversion.

Property generators MUST include aggregate/testcase divergence, empty names,
non-UTF-8 bytes, legacy/current functions, duplicate branch signatures,
excluded points, missing MC/DC senses, ignored-error states, and counts near
every numeric representation boundary. They MUST NOT generate only canonical
happy paths.

Algebra properties MUST preserve input order. Tests MUST NOT assert broad
commutativity, associativity, or idempotence unless their generator enforces the
documented safe subset.

### Executable Property Contract

Every property result uses this semantic snapshot schema:

```text
source display bytes and lookup-key bytes
source version and checksums
aggregate {line,function,branch,mcdc} stores
testcase-family key presence and value for each of the four families
function location/name indexes and representative
branch model order, signature, edge order, expression, taken, exclusion
MC/DC line, group key, vector position, declared index, expression, senses
purpose-specific totals and canonical-serializable classification
diagnostic facts, retained parser provenance, output bytes, and exit
```

| Property ID | Generator domain and precondition | Oracle/invariant | Shrink strategy |
| --- | --- | --- | --- |
| `M1-PROP-ROUNDTRIP-001` | Canonically serializable models, including all families and byte strings | `P(W(M)) == M` and writer fixed point | Remove sources, testcases, families, records, then shorten bytes/count lexemes while preserving serializability |
| `M1-PROP-ACCEPTED-INPUT-001` | Canonical, legacy, permissive, ignored-error, and malformed-boundary bytes | Oracle semantic snapshot, category, retained state, streams, and exit | Delete sections/records, reduce suffixes and numeric atoms, preserve the triggering category |
| `M1-PROP-NUMERIC-001` | Exact M0 numeric lexeme matrix and ordered sequences of 1-8 additions | Oracle class, comparisons, threshold, hash-key identity, and emitted lexeme | Delta-debug operations, then shrink mantissa/exponent/sign without changing the observed class |
| `M1-PROP-ALGEBRA-001` | Ordered operands from the exact algebra fixtures plus generated variants | Exact Oracle snapshot after each operation; no broad set law | Remove right-only then left-only data, reduce common points, preserve operand order and diagnostic path |
| `M1-PROP-ALGEBRA-SAFE-001` | Equal versions/checksums, small nonnegative integers, unique branch signatures, equal MC/DC vectors/exclusions, symmetric testcase sets | Only this subset may test documented commutativity or fixed point | Shrink within the safe subset; discard any candidate that violates a precondition |
| `M1-PROP-INDEX-001` | Function alias add/remove, branch block rebuild, MC/DC vector mutation | All forward/reverse indexes and signatures remain coherent after successful return | Remove operations while preserving the first invariant failure |
| `M1-PROP-NONSERIAL-001` | Aggregate/testcase divergence, late-`TN` MC/DC, repeated close, lazy empty maps | Classify as `serializable`, `nonserializable_by_contract`, or blocked Oracle unknown before writer invocation | Minimize to one source/test/family transition retaining the classification |

A `nonserializable_by_contract` model is not discarded and is not forced
through the writer. The corpus retains its semantic snapshot and construction
sequence. Legacy/current mapping is explicit in every generated case; equivalent
legacy and current inputs compare semantic snapshots, while raw spelling is
compared only where parser provenance is part of the case.

### Named Fuzz Targets

| Fuzz ID | Target and input | Failure oracle |
| --- | --- | --- |
| `M1-FZ-LEX-001` | Lexical record parser over arbitrary bytes and every record prefix | No panic/OOM/hang; exact accepted/rejected record class and consumed suffix against Oracle seeds |
| `M1-FZ-STATEFUL-001` | Stateful trace parser over record sequences, `TN`/`SF`/terminator transitions, and malformed constructors | No partial commit after a hard failure; exact semantic snapshot and diagnostics |
| `M1-FZ-WRITER-001` | Canonically serializable generated models | Valid canonical bytes, no model mutation, parse/write fixed point |
| `M1-FZ-ROUNDTRIP-001` | Parse-write-parse over canonical, legacy, permissive, and ignored-error corpus | `M1-PROP-ROUNDTRIP-001` or explicit nonserializable classification |
| `M1-FZ-NUMERIC-001` | Numeric atom plus ordered operation bytecode | No saturation/wrap/precision loss relative to pinned numeric snapshot |
| `M1-FZ-LINE-ALGEBRA-001` | Ordered line maps and operation bytecode | Exact `M1-ALG-LINE-001`-compatible snapshot |
| `M1-FZ-FUNCTION-ALGEBRA-001` | Function groups, aliases, ranges, removal, and operation bytecode | Coherent indexes and exact representative/range/count behavior |
| `M1-FZ-BRANCH-ALGEBRA-001` | Ordered repeated signatures, kinds, expressions, `-`, counts, and exclusions | Exact block occurrence/cache/totals behavior; no stale derived index |
| `M1-FZ-MCDC-ALGEBRA-001` | Group maps, unequal vectors, expressions, senses, counts, and exclusions | Exact asymmetric exception/merge/difference behavior; no unchecked Rust access |

Each target maps every stable fixture case to a deterministic seed:
SHA-256(`target-id || NUL || case-id || NUL || fixture-sha256`), first eight
bytes interpreted big-endian. Shrinking MUST retain raw input, seed, target ID,
first failing operation, semantic snapshots, streams/status, and runtime
manifest. Minimized regressions become permanent corpus entries and link back to
the originating `M1-MD-*`, `M1-TF-*`, property, and fuzz IDs.

### Resource And Fuzz Budgets

The following are **harness safety budgets**, not Ferricov product acceptance
limits and not compatibility decisions:

| Budget | CI smoke | Scheduled run |
| --- | --- | --- |
| Input bytes per generated case | 1 MiB | 16 MiB |
| One logical record/field | 256 KiB | 1 MiB |
| Records / sections / family cardinality | 65,536 / 4,096 / 65,536 | 1,000,000 / 65,536 / 1,000,000 |
| Per-case wall timeout | 2 s | 10 s |
| Per-worker RSS/container cap | 512 MiB | 1 GiB |
| Time per fuzz target | 60 s | 15 min |

A timeout, signal, Rust panic, sanitizer finding, allocation-cap breach, or RSS
kill is a failure artifact. Expected Oracle `die`/nonzero behavior passes only
when its case declares that outcome and the semantic/stream/status snapshot
matches. Corpus minimization must run under the same cap, then replay the
minimized input without minimizer instrumentation.

`M0-RSRC-MEASURE-001` contains 13 controlled scale profiles, each with one
primary scale axis and every dependent input dimension recorded. The field
profiles use an exact `TN` payload of 1 KiB, 64 KiB, 1 MiB, or 16 MiB; the
logical record additionally contains the `TN:` prefix. The record profiles use
exactly 1, 1,024, or 65,536 `DA` records inside one source section. The section
profiles use exactly 1, 1,024, or 16,384 source sections with one `DA` record
each, so their global line-point cardinality necessarily changes with the
section count. The family profiles use equal source-scoped line, function,
branch, and logical MC/DC-condition cardinalities of 1, 1,024, or 65,536
inside one source section. Each logical MC/DC condition emits two condition
outcomes, one observed hit and one observed miss.

The Oracle command enables `--branch-coverage` and `--mcdc-coverage` before
`--summary`; plain summary output is not evidence for those two families. Each
profile binds its exact expected stdout/stderr hashes and parsed line,
function, branch, and condition-outcome summary. The retained result also
binds input hash/bytes, maximum record and field, total/data records, sections,
source-scoped family cardinalities, raw metrics, wall/user/system CPU time,
peak RSS, exit/signal/timeout, output, input immutability, cleanup, and
host/kernel/Docker/cgroup identity. The host-bounded Docker invocation is the
sole deadline observer: only a host `TimeoutExpired` event is a timeout, while
a target exit code of 124 before the deadline remains a nonzero, non-timeout
outcome. When output storage is writable, a post-generation failure retains
the exact generated input, available raw metrics and streams, Docker status,
failure class/reason, deadline provenance, and post-cleanup facts under the
fresh result root. Retention failure is reported alongside the original
capture failure, does not claim a manifest exists, and cannot bypass attempted
named-container or temporary-directory cleanup. Successful evidence closes the
retained tree exactly over `result.json` and three artifacts in each of the 13
expected sample directories.

All 13 retained Oracle profiles exit zero without a signal, timeout, stderr, or
output file. They establish observed accepted lower bounds through a 16 MiB
field, 65,536 `DA` records, 16,384 sections, and 65,536 distinct points in each
coverage family. The timing and RSS values are one bounded observation per
profile, not stable distributions, performance gates, or causal attribution.
No larger input behavior is implied.

Any Ferricov product limit or over-limit diagnostic must be selected only after
a candidate exists and, when it intentionally differs from an accepted Oracle
input, a reviewed resource-safety deviation. `M1-MD-020` and `M1-TF-063`
therefore retain their product/parity blockers, while `M1-TF-064` retains its
executable fuzz-corpus blocker. The harness budgets above MUST NOT be reported
as product limits.

## Oracle Decisions And Case IDs

The following model case IDs are stable planned identities. They do not claim
execution or pass status. Each case MUST retain the evidence required by the
[tracefile grammar](tracefile-grammar.md#m1-evidence-and-exit-conditions).

| Model case | Required decision | Executable case bindings |
| --- | --- | --- |
| `M1-MD-001` | Raw bytes, invalid UTF-8, source display path versus lookup key, and case-sensitive/case-insensitive identity | `M1-TF-005`, `M1-TF-006`, `M1-TF-061` |
| `M1-MD-002` | Empty, sanitized, comma-suffixed, `,diff`, and late-bound testcase identities | `M1-TF-003`, `M1-TF-004`, `M1-TF-021` |
| `M1-MD-003` | Independent aggregate/testcase snapshots for repeated source/test sections | `M1-TF-005`, `M1-TF-023` |
| `M1-MD-004` | General numeric lexeme, Perl numeric class, hash-key identity, addition, threshold, and output formatting | `M1-TF-030`, `M1-TF-031`, `M1-TF-032`, `M1-TF-033`, `M1-TF-034` |
| `M1-MD-005` | Per-source version and checksum scope, conflict, replacement, merge, and writer-provider behavior | `M1-TF-007`, `M1-TF-008`, `M1-TF-035`, `M1-TF-043` |
| `M1-MD-006` | Function location/name indexes, representative selection, ranges, mixed forms, and alias-level/group-level totals | `M1-TF-009`, `M1-TF-010`, `M1-TF-011` |
| `M1-MD-007` | Ordered branch blocks, expression independence, duplicate signatures, exclusion, set operations, and canonical renumbering | `M1-TF-013`, `M1-TF-025`, `M1-TF-041` |
| `M1-MD-008` | MC/DC group-size identity, stored versus declared index, missing/repeated senses, exclusion, and incompatible merge behavior | `M1-TF-014`, `M1-TF-026`, `M1-TF-041` |
| `M1-MD-009` | Source/manual conflict for excluded MC/DC writer and aggregate totals | `M1-TF-042` |
| `M1-MD-010` | Line union/intersection/difference values and operand-order effects | `M1-ALG-LINE-001`, `M1-PROP-ALGEBRA-001`, `M1-FZ-LINE-ALGEBRA-001` |
| `M1-MD-011` | Function union/intersection/difference alias and range behavior | `M1-ALG-FUNCTION-001`, `M1-ALG-FUNCTION-REP-001`, `M1-FZ-FUNCTION-ALGEBRA-001` |
| `M1-MD-012` | Branch union/intersection/difference for repeated signatures and `-` taken state | `M1-ALG-BRANCH-001`, `M1-ALG-BRANCH-CACHE-001`, `M1-FZ-BRANCH-ALGEBRA-001` |
| `M1-MD-013` | MC/DC union/intersection/difference granularity, counts, compatibility, and exclusions | `M1-ALG-MCDC-001`, `M1-ALG-MCDC-VECTOR-001`, `M1-ALG-MCDC-EXPR-001`, `M1-FZ-MCDC-ALGEBRA-001` |
| `M1-MD-014` | Left-only and right-only testcase behavior under all set operations, including empty lazy maps | `M1-ALG-TESTCASE-LINE-001`, `M1-ALG-TESTCASE-FUNCTION-001`, `M1-ALG-TESTCASE-BRANCH-001`, `M1-ALG-TESTCASE-MCDC-001` |
| `M1-MD-015` | Complete writer projection, total views, lexical/numeric ordering, fixed point, and immutability | `M1-TF-040`, `M1-TF-041`, `M1-TF-042`, `M1-TF-043`, `M1-TF-044`, `M1-TF-045`, `M1-TF-046` |
| `M1-MD-016` | Semantic snapshots after every categorized ignored error and hard-failure boundary | `M1-TF-016`, `M1-TF-024`, `M1-TF-026`, `M1-TF-031`, `M1-TF-032`, `M1-TF-033`, `M1-TF-034`, `M1-TF-035`, `M1-TF-036` |
| `M1-MD-017` | Parse-write-parse equality across canonical, legacy, permissive, and ignored-error corpora | `M1-TF-045`, `M1-TF-052` |
| `M1-MD-018` | Perl lexical ordering and character-class behavior across locale, platform, and byte inputs | `M1-TF-001`, `M1-TF-004`, `M1-TF-041`, `M1-TF-061` |
| `M1-MD-019` | Repeated terminator totals, cumulative aggregate addition, MC/DC cross-test clone bleed, and duplicate-line hard failure | `M1-TF-015`, `M1-TF-023`, `M1-TF-026`, `M1-TF-042` |
| `M1-MD-020` | Adversarial size, allocation, malformed nesting, and model invariant fuzzing | `M1-TF-062`, `M1-TF-063`, `M1-TF-064`; `M0-RSRC-MEASURE-001`; `M1-FZ-LEX-001`, `M1-FZ-STATEFUL-001`, `M1-FZ-WRITER-001`, `M1-FZ-ROUNDTRIP-001`, `M1-FZ-NUMERIC-001`, `M1-FZ-LINE-ALGEBRA-001`, `M1-FZ-FUNCTION-ALGEBRA-001`, `M1-FZ-BRANCH-ALGEBRA-001`, `M1-FZ-MCDC-ALGEBRA-001` |

No row may be marked resolved from static source inspection alone. The result
must be captured from the pinned executable with exact input bytes, runtime,
locale, feature flags, error policy, streams, status, output bytes, and semantic
snapshot.

### Case And Evidence Manifest Boundary

The canonical executable manifest is planned at
`compat/cases/m1-model.json`. It MUST bind each `M1-MD-*` decision and every
listed property/algebra/fuzz case to an exact runner, operand fixture hashes,
command, environment, source anchors, expected semantic snapshot schema, status,
and evidence directory. That manifest does not yet exist, so all model rows
remain `blocked`.

The current `compat/fixtures/m0-tracefiles/oracle-cases.json` contains
free-form `requirement` labels and CLI stream/output captures. It has no
executable `M1-MD-*` definitions, does not validate compound requirement
coverage, and does not retain aggregate plus four independent testcase-family
semantic snapshots. It is useful source evidence but cannot close a model row.

Each manifest entry has two independent phase states:

- `oracle_baseline`: executed during M0 against the pinned Oracle to resolve
  model/grammar decisions needed for the go/no-go review; it does not require a
  Ferricov implementation and cannot count as compatibility.
- `ferricov_parity`: executed during M1 after authorization against the same
  retained Oracle baseline and candidate; only this phase may become
  `pass`/`not_applicable`/`blocked` for compatibility.

The M0 approval record is planned at
`specs/001-full-lcov-compatibility/m0-go-no-go.md`. It MUST record approver,
date, source SHA, Oracle image/manifest hash, case-manifest hash, unresolved
exceptions, and go/no-go result. Its absence is an authorization blocker, not a
reason to defer Oracle decision probes until M1.

## Open Unknowns

The following decisions remain blocked on the Oracle cases above:

1. Exact `looks_like_number` acceptance, Perl scalar promotion, signed-zero
   formatting, huge integer behavior, `Inf`/`NaN` handling, leading-zero key
   identity, and arithmetic order effects.
2. Exact `\d`, `\s`, `\W`, `lc`, and lexical `sort` behavior for invalid UTF-8,
   non-ASCII bytes, locale changes, and qualified platforms.
3. Whether repeated source/test close behavior exposes cumulative double-add in
   aggregate counts through supported summary, merge, filter, or report paths.
4. Whether aggregate-first MC/DC mutation makes later testcase snapshots
   include prior testcase counts, and the exact hard-failure boundary for
   repeated or noncontiguous per-test MC/DC lines.
5. Whether repeated `end_of_record` exposes lifecycle-dependent cached totals
   that cannot be recomputed from stored points.
6. Whether excluded MC/DC senses contribute to canonical `MCF`/`MCH`, aggregate
   summaries, both, or neither in the pinned executable.
7. Exact testcase-map behavior for intersection and difference when the two
   operands have different testcase sets.
8. Exact checksum storage when local verification arguments and global checksum
   configuration differ, including right-overlay behavior after ignored
   mismatches.
9. Which input numeric lexemes survive unchanged until write and which are
   reformatted merely by insertion into Perl numeric/hash contexts.
10. Whether every accepted repeated-section model is canonically serializable;
    if not, which explicit M1 round-trip scope and compatibility decision
    replaces the currently unrestricted plan invariant.
11. Product input, record, field, section, cardinality, allocation, RSS, and
    timeout limits, including the diagnostic/exit/model state at every boundary.
12. Function representative selection after equal-length alias removal and
    branch intersection cache behavior when no merge reports `changed`.
13. MC/DC unequal-vector behavior in both operand orders, sticky exclusion from
    either side, and expression mismatch after ignored continuation.

No unknown may be resolved by selecting the easiest Rust type or by correcting
an apparent upstream defect.

## Non-Goals

This document does not:

- authorize M1 implementation before the M0 exit gate;
- preserve Perl package names, array offsets, object cycles, mutable globals,
  or `Storable` serialization;
- define CLI option parsing, configuration precedence, callbacks, error text,
  stream routing, exit status, or parallel scheduling;
- put filesystem traversal, path resolution, source reads, or checksum I/O in
  `ferricov-model`;
- define `genhtml` report structures or GCC/LLVM capture models;
- require raw tracefile record order in the semantic model where order has no
  semantic effect;
- preserve ignored input summary payloads, input comments, or legacy record
  spelling in canonical output;
- make direct converter order the canonical `TraceFile::write_info` order;
- guarantee conventional mathematical set laws where the Oracle is ordered or
  stateful; or
- improve, repair, normalize, saturate, or reject upstream numeric and coverage
  behavior without reviewed differential evidence.

## M1 Model Gate

The coverage model is approved for implementation only when:

- every `M1-MD-*` row has an executable Oracle case definition in
  `compat/cases/m1-model.json`;
- every open unknown has a recorded Oracle result or an explicit reviewed
  exclusion from M1 scope;
- semantic snapshots distinguish aggregate and every testcase-family map;
- the numeric representation decision passes `M1-MD-004` without information
  loss;
- parse-write-parse and writer fixed-point properties are executable over the
  complete corpus;
- malformed and non-UTF-8 fuzz seeds cover every retained-state constructor,
  all named fuzz targets pass their harness budgets, and product resource limits
  are measured or retained as an explicit reviewed blocker;
- the model remains independent of CLI, filesystem, subprocess, callback, and
  report layers; and
- the retained `m0-go-no-go.md` record explicitly authorizes M1 with hashes
  for the approved source, Oracle, and case manifest.

Until then, this file is a reviewed model inventory and decision contract, not
an implementation claim.
