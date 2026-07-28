# Callback, Perl Runtime, And Installation Contract

## Status And Authority

This is a proposed normative M2-M5 contract and a reviewed M0 decision draft
for Ferricov's LCOV 2.5 callback, installed support script, optional Perl
runtime, `perl2lcov`, and installation surfaces. It refines the project
requirements without changing the architecture-only acceptance in ADR 0002.

The behavioral Oracle is upstream LCOV `v2.5` at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`. Source references in this document
are relative to that pinned upstream tree unless they start with `docs/`,
`specs/`, or `compat/` and clearly refer to Ferricov.

The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative. An
observed upstream defect is still Oracle behavior until a reviewed divergence
is recorded. This contract does not require Ferricov to reproduce a destructive
installation defect without review; it does require the difference to be
measured, classified, and excluded from any unsupported compatibility claim.

## Scope

This contract covers:

- the nine documented callback families;
- common external callback construction and process behavior;
- Perl module loading, interpreter state, objects, and parallel lifecycle;
- all 23 files installed from upstream `scripts/`;
- the command, library, documentation, example, test, configuration, and report
  assets in the installed surface;
- the `perl2lcov` and Devel::Cover runtime boundary; and
- the milestone boundary between the M1 core model and M5 runtime delivery.

It does not make upstream Perl package structure part of Ferricov's core
architecture. It does not accept the proposed separate Perl callback host. It
does not authorize an M5 callback, `perl2lcov`, support-script, packaging, or
complete-installed-suite compatibility claim.

## Stable Identity Rules

The IDs in this contract are stable. Tests, inventory entries, and evidence MAY
add a suffix for a particular case, but MUST retain the base identity. Renaming
an ID requires an explicit compatibility-spec migration.

The existing `support-script.*` IDs are the canonical identities for installed
support files. The current generated inventory leaves all 23 entries
`unreviewed` with empty behavior, dependency, interaction, and planned-case
fields. That inventory state is not evidence of compatibility.

## Milestone And Architecture Boundary

### Accepted M1-Scope Decisions

The proposed Perl host does not block M1. The following decisions are accepted
for the scope needed by M1:

1. `ferricov-model` and `ferricov-tracefile` are Perl-neutral canonical core
   layers.
2. The model MUST preserve path and text bytes and MUST represent every
   inventoried tracefile record, counter, identity, and invariant without lossy
   conversion.
3. The model MUST NOT contain Perl globals, `%INC`, Perl class or array layout,
   callback lifecycle state, host framing, launcher state, CWD, environment, or
   umask.
4. Later callback adapters MUST translate through stable domain operations and
   MUST NOT make the core model depend on CLI, filesystem traversal, processes,
   report rendering, or Perl.
5. Callback-free and external-executable workflows MUST NOT require Perl.
6. M1 MAY claim only the tracefile-core preview defined by the execution plan.
   It MUST NOT claim callback, Perl, primary-command, or installed-suite parity.

These decisions implement the scoped M0 gate in
`specs/001-full-lcov-compatibility/plan.md`. The broader wording in the current
M1 task checklist MUST be interpreted as "accepted for the scope needed by M1,"
not as requiring acceptance of the proposed host before M1 begins.

### M2 Through M5 Runtime Boundary

- The native external callback runner is a proposed architecture direction. Its
  call sites MUST NOT be treated as accepted or qualified until the applicable
  common and callback-specific contract cases pass.
- The separate Perl host remains proposed. It MUST NOT be implemented until the
  state, lifecycle, wire, failure, and launcher contracts pass their Oracle
  characterization gates.
- If a separate process cannot reproduce documented arbitrary same-interpreter
  access, affected `.pm` workflows MUST use a pinned Perl front-end in the same
  interpreter context instead of receiving a full compatibility claim.
- The `perl2lcov` adapter architecture remains proposed. Its launcher, runtime,
  and behavior qualification are blocked until runtime discovery and all
  applicable `P2L-*` cases are specified and pass.
- Support scripts, installed assets, runtime dependencies, package manifests,
  fresh-install behavior, and complete callback protocols are M5 scope.
- No M5 compatibility claim is permitted until every applicable case in this
  contract passes for the published platform and dependency matrix.

The required dependency direction is:

```text
M1 model and tracefile
  <- M2-M4 operations, report, and capture call sites
  <- native callback adapters
  <- M5 Perl host or pinned Perl front-end

proposed perl2lcov Perl adapter -> neutral tracefile and model boundary
```

## Common Callback Contract

| ID | Pinned source | Normative behavior | Failure and interaction requirements |
| --- | --- | --- | --- |
| `CB-CFG-001` | `lib/lcovutil.pm:990-1046`, `lib/lcovutil.pm:130` | One configured string is split using `split_char`, comma by default. Repeated option values are concatenated without that split. A first argument ending in `.pm` selects module loading; every other value selects an external caller. | Tests MUST distinguish one combined value from repeated values and MUST preserve empty values, whitespace, quotes, glob characters, and shell metacharacters. |
| `CB-PM-LOAD-001` | `lib/lcovutil.pm:1000-1046` | The loader derives directory and basename, removes `.pm` for the class, temporarily prepends the directory to `@INC`, requires the basename, and calls `Class->new(module_path, args...)`. | Load failure, undefined constructor result, and save without restore use `package`. Same-basename modules MUST be tested because `%INC` is process-global and first-loaded state is observable. |
| `CB-PM-STATE-001` | `scripts/context.pm:59-65`, `scripts/select.pm:174-193`, `scripts/history.pm:98-104` | Callback modules execute in the tool interpreter and may read or write tool/package globals, `%INC`, CWD, environment, umask, signals, descriptors, and shared callback state. | The contract MUST define initial value, owner, lifetime, mutation visibility, and writeback order for every exposed state item before a separate host is accepted. Failure MUST NOT imply rollback unless the Oracle proves rollback. |
| `CB-PM-LIFE-001` | `lib/lcovutil.pm:1013-1032`, `lib/lcovutil.pm:1817-1829`, `lib/lcovutil.pm:2127-2238` | A callback with paired `save` and `restore` participates in child state transfer; `start` runs in a child, `save` runs before child exit, `restore` runs in the parent, and `finalize` runs late. | Serial, parallel, and `LCOV_FORCE_PARALLEL` ordering MUST be characterized. Save exceptions and positional callback-data behavior MUST be Oracle-frozen; a later-value shift MUST NOT be silently normalized. |
| `CB-PIPE-001` | `lib/lcovutil.pm:3247-3309` | Pipe callbacks use list-form execution. If total argv count is two, or four for criteria, and the first path does not exist, the first value is split on spaces before operation arguments are appended. | Direct process creation is `callback`. Close status is callback-specific. The legacy rewrite is distinct from configured `split_char` and shell parsing. |
| `CB-SHELL-001` | `lib/lcovutil.pm:3320-3327`, `lib/lcovutil.pm:3387-3394`, `lib/lcovutil.pm:3445-3455` | Version comparison and selection join a command string and execute through the shell. | Version command-not-found and other nonzero status mean mismatch and enter `version` handling. Select command-not-found, signal, and other nonzero status are truthy and select the item. They are not generic callback transport failures. |
| `CB-IO-001` | `lib/lcovutil.pm:3279-3309`, `lib/lcovutil.pm:3336-3485` | External callbacks inherit stdin, CWD, environment, umask, descriptors, and permissions. Pipe stdout is consumed, stderr remains on the tool error path, and consumed line endings remove CR. | Empty output, empty first line, missing final newline, arbitrary bytes, stderr, large output, broken pipe, exit, and signal MUST be tested per callback. No global status rule may replace the per-callback rules below. |

### Callback Lifecycle Failure Matrix

All rows below are blocked contract cases. Each case MUST run in serial,
parallel, and `LCOV_FORCE_PARALLEL` profiles where the lifecycle method is
reachable, and MUST retain the ordered callback transcript, category, ignore
count, keep-going state, stdout/stderr, child wait status, payload presence and
index, sibling merge result, partial parent mutation, output artifact, and final
exit. The aggregate diagnostics binding is
`PAR-CALLBACK-LIFECYCLE-FAIL-001` in
[diagnostics-parallel-contract.md](diagnostics-parallel-contract.md).

| Case ID | Pinned source | Required decision |
| --- | --- | --- |
| `CB-LIFE-START-FAIL-001` | `lib/lcovutil.pm:2127-2167` | Freeze exception/category handling before worker business work, whether `save` still runs, sibling admission/drain, payload creation, and final merge/status. |
| `CB-LIFE-SAVE-FAIL-001` | `lib/lcovutil.pm:2170-2226` | Freeze callback error/ignore behavior, whether a failed save contributes any payload slot, child result disposition, and parent/sibling state after continuation. |
| `CB-LIFE-RESTORE-FAIL-001` | `lib/lcovutil.pm:2229-2238` | Freeze parent-side exception/category handling, mutations made before the failure, later restores, coverage commit, artifact, and final status. |
| `CB-LIFE-FINALIZE-FAIL-001` | `lib/lcovutil.pm:1817-1829` | Freeze late parent failure after prior coverage/callback effects, ignore and keep-going behavior, output retention, teardown order, and final status. |
| `CB-LIFE-SAVE-INDEX-001` | `lib/lcovutil.pm:2191-2201`, `lib/lcovutil.pm:2231-2238` | Upstream appends no placeholder when `save()` throws; first freeze whether a later callback value shifts onto an earlier callback's positional `restore`, including ignore and keep-going results. Ferricov MUST preserve any bounded qualified Oracle trap by default. Identity framing or atomic rejection that changes the continued result requires a separate accepted safety-deviation ADR; ADR 0004 does not authorize it. |

Registration-time missing `save`/`restore` pairing remains a separate `package`
path at `lib/lcovutil.pm:1013-1032`; it is not interchangeable with the runtime
`callback` failures above. No lifecycle row may be collapsed into a generic
child-error case.

## Callback Surface Matrix

### `CB-CONTEXT-001`

- Sources: `lib/lcovutil.pm:1049-1066`, `lib/lcovutil.pm:3336-3357`.
- External behavior: no operation argument; each stdout line splits at the
  first run of spaces; repeated keys concatenate values with `\n`;
  `close(1)` checks nonzero status as `callback`.
- Module behavior: `context() -> hashref`; callback exceptions use `callback`;
  a non-hash result is fatal.
- Applicability: `lcov`, `geninfo`, and `genhtml` collect context during late
  cleanup after callback finalization. `llvm2lcov` calls cleanup but does not
  persist the same profile artifact. `perl2lcov` may construct the callback via
  shared parsing but does not call `cleanup_callbacks()`.
- Interactions: configuring context enables profile collection; constructors
  may mutate `@lcovutil::comments` before the callback method is called.
- Required cases: line parsing, repeated/missing values, constructor mutation,
  profile auto-enable, cleanup timing, no-cleanup front ends, close failure, and
  serial/parallel finalization order.

### `CB-VERSION-001`

- Sources: `lib/lcovutil.pm:2828-2908`, `lib/lcovutil.pm:3359-3394`.
- Extract behavior: external callers receive `file` and return the first stdout
  line; modules return a scalar or undef. Results, including undef, are cached
  by the exact filename string.
- Compare behavior: equal defined strings bypass the callback. Otherwise the
  real module order is `compare_version($you, $me, $filename)` and `0` means
  match. External order is `--compare '$you' '$me' '$file'` through the shell.
- Applicability: capture, merge, filtering, converters, and report checks that
  compute or compare file versions. Some call sites first require source
  existence under `check_existence_before_callback`.
- Failure: extract method exceptions use `callback`; compare exceptions use
  `callback` and then mismatch behavior. External nonzero, signal, or
  command-not-found is a version mismatch and enters `version` handling.
- Required cases: equal bypass, undef/empty/empty-line extraction, every caller's
  ID order, source existence gate, cache identity and parent/child merge, module
  zero-on-match, shell quoting, command-not-found, ignore, and silent compare.

### `CB-ANNOTATE-001`

- Sources: `lib/lcovutil.pm:3396-3427`, `bin/genhtml:5721-5853`,
  `bin/genhtml:7963-7971`.
- External behavior: argv appends filename; each line is
  `commit|author_data|date|source_text`; only the first three pipes split; the
  first semicolon splits abbreviated and full author.
- Module behavior: `annotate(file)` returns a system-style status and an array
  of `[text, abbreviated_author, full_author_or_undef, W3CDTF_date, commit_id]`.
- Applicability: `genhtml` only. Annotation drives source text, owner/date bins,
  tooltips, selection, and cache/version validation.
- Failure: rows for a file cannot mix committed IDs and `NONE`; bad owner/date,
  count, or status enters `annotate`. A method exception first enters `callback`.
  An ignored applicable error may fall back to source loading or synthesis.
- Required cases: delimiter preservation, CRLF, `NONE`, mixed rows, wrong row
  count, source absence, cache/version mismatch, nonzero, exception, ignore,
  synthesis, and global zero-success failure.

### `CB-CRITERIA-001`

- Sources: `lib/lcovutil.pm:3139-3162`, `lib/lcovutil.pm:3429-3443`,
  `lib/lcovutil.pm:7198-7243`, `bin/genhtml:1307-1395`.
- External behavior: argv appends `name`, `type`, and compact JSON; nonempty
  stdout lines are messages; raw wait status is the result.
- Module behavior: `check_criteria(name, type, hashref)` returns status and a
  message array.
- Applicability: shared Perl front ends can configure the callback. `genhtml`
  has file/directory/top and optional date/owner bins; TraceFile paths use
  file/top behavior. Auxiliary reachability MUST be proved per command.
- Interactions: `criteria_callback_levels` and `criteria_callback_data` change
  invocation. The last nonzero callback status can overwrite the global raw
  status; non-genhtml entry points may fold the process exit to one.
- Failure: rejection is a semantic criteria result after processing, not a
  transport failure. An ignored external open failure can skip a check with
  status zero; an ignored module exception produces callback handling and a
  synthetic nonzero criteria status.
- Required cases: every level and coverage type, differential/date/owner data,
  JSON versus hash, message order, multiple failures, signoff/suppress, open and
  method failure, delayed output, and serial/parallel aggregation.

### `CB-RESOLVE-001`

- Sources: `lib/lcovutil.pm:3373-3385`, `lib/lcovutil.pm:3712-3762`,
  `lib/lcovutil.pm:7288-7305`.
- Behavior: resolution follows substitution, existing paths and source
  directories, then callback. External output uses the first line; modules
  return path or undef. Truthy results are cached by requested filename.
- Applicability: missing source resolution and `geninfo` GCNO resolution;
  `lcov --capture` forwards applicable configuration to `geninfo`.
- Interactions: a relative result is relative to callback CWD. A nonempty but
  nonexistent result can affect missing-filter behavior differently from later
  source reads.
- Failure: method or process-creation failure uses `callback`; external nonzero
  close status is generally not checked and can become undef/original-path
  fallback. Later source failure remains distinct.
- Required cases: substitution/search precedence, source and GCNO, relative and
  nonexistent results, aliases, cache, empty/undef, exception, nonzero, ignore,
  missing filter, and original-path fallback.

### `CB-UNREACHABLE-001`

- Sources: `lib/lcovutil.pm:8023-8360`, `lib/lcovutil.pm:8208-8233`,
  `scripts/unreach.pm:190-203`.
- Behavior: the real ABI is
  `exclude(type, source_reader, per_test_map, summary_map)`. It receives live
  mutable branch or MC/DC objects and may change excluded flags and totals.
- Applicability: compatible use requires a `.pm` module. An external value can
  be constructed as `ScriptCaller`, but the first `exclude` invocation has no
  such method and fails; configuration success MUST NOT be reported as protocol
  support. Direct `geninfo` and `lcov --capture` reachability require separate
  cases because forwarding differs.
- Interactions: invoked for each applicable testcase and enabled map; false
  return or exception does not roll back mutations already made.
- Failure: method exception uses `callback`; partial mutations, recomputed
  totals, and subsequent filtering are observable.
- Required cases: module-only enforcement at first use, branch and MC/DC order,
  per-test/summary mutation, excluded flags, false-after-mutation,
  exception-after-mutation, forwarding, source reader behavior, and lifecycle.

### `CB-SELECT-001`

- Sources: `lib/lcovutil.pm:3445-3455`, `bin/genhtml:1269-1278`,
  `bin/genhtml:4400-4498`, `bin/genhtml:4682-4744`.
- External behavior: JSON encodings of `LineData::to_list` and
  `SourceLine::to_list`, or empty strings, are followed by filename and line
  key in a shell command. Stdout is discarded and raw status is boolean.
- Module behavior: receives `LineData` and `SourceLine` objects, not JSON.
- Applicability: `genhtml` only. Selection first applies to coverage lines and
  then expands matching runs and configured context.
- Failure: exit zero drops; every nonzero, signal, and command-not-found selects.
  A module exception selects and records `callback`.
- Required cases: exact object and JSON shapes, undef, real line-key indexing,
  zero/nonzero/127/signal, exception-selects, context expansion, empty selection,
  annotate/base/diff global dependencies, and shell metacharacters.

### `CB-SIMPLIFY-001`

- Sources: `lib/lcovutil.pm:3458-3469`, `bin/genhtml:7205-7327`,
  `bin/genhtml:13911-14049`, `bin/genhtml:14221-14233`.
- Behavior: returns a display name and MUST NOT change stored function identity
  or matching. External callers use the first truthy stdout record; modules
  return a scalar.
- Applicability: `genhtml` function detail display. The implementation still
  constructs and validates the callback before disabling it under
  `--no-sourceview`. The real RC key is `simplify_function`, while the manual
  names `simplify_script`; the Oracle decides.
- Failure: missing output is broken callback behavior. An ignored exception
  retains the original name. External close status is not independently checked.
- Required cases: display identity, RC/manual discrepancy, no-sourceview
  construction, empty/`0`/`0\n`/multiline output, exception fallback, ordering,
  aliases, and lifecycle counters.

### `CB-HISTORY-001`

- Sources: `lib/lcovutil.pm:3472-3485`, `bin/genhtml:6162-6205`,
  `bin/geninfo:1312-1349`, `scripts/history.pm:88-197`.
- Behavior: external argv appends only the item; the first output line is the
  prediction and an empty line is undef. Modules return predicted seconds or
  undef. Values affect scheduling, not coverage meaning.
- Applicability: `genhtml` orders resolved filenames; `geninfo` consults history
  for multi-chunk or forced-parallel work. Capture through `lcov` initializes it
  in the `geninfo` process; non-capture `lcov` may construct but not call it.
- Interactions: the shipped module selects profile schema using
  `$lcovutil::tool_name` and `$main::callFromLcov`.
- Failure: no output is broken history behavior; the call site does not provide
  a uniform local conversion for every failure. External close status is not
  checked independently.
- Required cases: numeric/zero/negative/non-number/empty/undef, unknown item,
  profile schema and globals, multiple profiles, serial/parallel ordering,
  forced parallel, malformed profile, missing executable, signal, and coverage
  output equivalence.

## Auxiliary Callback Reachability

Shared parser exposure MUST NOT be treated as proof that a command calls a
callback. `perl2lcov` and `llvm2lcov` inherit shared callback options, while
`py2lcov` and `xml2lcov` expose narrower version behavior. Each auxiliary command
MUST have a `CB-REACH-001` case that:

1. configures every parser-accepted callback;
2. records constructor, method, lifecycle, and destructor events;
3. triggers every operation that could make the callback applicable;
4. distinguishes constructed-but-unused from invoked; and
5. compares serial, parallel, cleanup, output, and exit behavior.

No auxiliary callback surface may be marked compatible based only on shared
option parsing.

## Installed Support Script Manifest

All files below are installed by upstream from `scripts/`. Installation is a
public surface even when a file is a helper rather than a callback entry point.

| Stable ID | Pinned source and role | Applicability and interactions | Dependencies and failure surface | Required case group |
| --- | --- | --- | --- | --- |
| `support-script.p4version-pm` | `scripts/P4version.pm:1`, `docs/scripts.rst:178-207`; Perforce version module | `--version-script`; local edit, prefix, MD5, allow-missing | Perl, P4, filesystem, `annotateutil.pm`; command/parse/missing/edit failure | `SCRIPT-VERSION-001` |
| `support-script.analyzeinfofiles` | `scripts/analyzeInfoFiles:1`; compare coverpoints across info files | Standalone tracefile analysis utility | Perl, `lcovutil.pm`, readable tracefiles; format/version/count mismatch | `SCRIPT-UTILITY-001` |
| `support-script.annotateutil-pm` | `scripts/annotateutil.pm:1`; annotation/version helper and `AnnotateBase` | Used by Git/P4 annotate and version scripts; cache and local-edit merge | Files, locks, cache, version callback; stale/malformed cache and I/O failure | `SCRIPT-ANNOTATE-001` |
| `support-script.batchgitversion-pm` | `scripts/batchGitVersion.pm:1`, `docs/scripts.rst:144-177`; batched Git version module | `--version-script`; repository scan, submodules, prefix/prepend/token, MD5 | Perl, Git, filesystem; malformed Git output, missing file, subprocess failure | `SCRIPT-VERSION-001` |
| `support-script.context-pm` | `scripts/context.pm:1`; context module and standalone probe | `--context-script`; optional `--comment` mutates tool comments | Perl, `whoami`, `which perl`, environment; option and command-output failure | `SCRIPT-CONTEXT-001` |
| `support-script.criteria` | `scripts/criteria:1`, `docs/scripts.rst:282-309`; executable criteria wrapper | `--criteria-script`; external pair for `criteria.pm` | Perl and module path; JSON/options/status | `SCRIPT-CRITERIA-001` |
| `support-script.criteria-pm` | `scripts/criteria.pm:1`, `docs/scripts.rst:282-309`; criteria module | Checks uncovered differential categories and optional coverage families | Perl; malformed hash/totals/options; semantic reject versus signoff | `SCRIPT-CRITERIA-001` |
| `support-script.get-signature` | `scripts/get_signature:1`, `docs/scripts.rst:560-621`; executable MD5 version callback | `--version-script` extract/compare | Perl, `md5sum`, readable source; argument, command, and file failure | `SCRIPT-VERSION-001` |
| `support-script.getp4version` | `scripts/getp4version:1`, `docs/scripts.rst:178-207`; executable P4 version callback | External pair for `P4version.pm`; MD5, local state, allow-missing | Perl, P4, filesystem; compare argument order and P4 status | `SCRIPT-VERSION-001` |
| `support-script.gitblame` | `scripts/gitblame:1`, `docs/scripts.rst:20-67`; executable annotation wrapper | External pair for `gitblame.pm` | Perl, Git, `annotateutil.pm`; missing repo/file, parse and pipe failure | `SCRIPT-ANNOTATE-001` |
| `support-script.gitblame-pm` | `scripts/gitblame.pm:1`, `docs/scripts.rst:28-67`; Git annotation module | `--annotate-script`; cache, verify, domain, P4 IDs, version callback | Perl, Git, cache/log/filesystem; stale cache, local edits, malformed blame | `SCRIPT-ANNOTATE-001` |
| `support-script.gitdiff` | `scripts/gitdiff:1`, `docs/scripts.rst:243-275`; Git unified-diff generator | Produces data consumed by `--diff-file`; include/exclude/prefix/blank | Perl, Git; bad revision, partial output, signal, malformed path | `SCRIPT-DIFF-001` |
| `support-script.gitversion` | `scripts/gitversion:1`, `docs/scripts.rst:110-141`; executable Git version callback | External pair for `gitversion.pm`; wrapper option surface differs | Perl, Git, filesystem; missing repo/file, dirty state, compare status | `SCRIPT-VERSION-001` |
| `support-script.gitversion-pm` | `scripts/gitversion.pm:1`, `docs/scripts.rst:110-141`; Git version module | `--version-script`; P4-derived IDs, MD5, local change, prefix | Perl, Git, `annotateutil.pm`; constructor versus standalone failure | `SCRIPT-VERSION-001` |
| `support-script.history-pm` | `scripts/history.pm:1`; profile history module | `--history-script`; tool-specific profile schema and scheduling | Perl, JSON profile/glob, tool globals; bad schema, item, number, or file | `SCRIPT-HISTORY-001` |
| `support-script.p4annotate` | `scripts/p4annotate:1`, `docs/scripts.rst:70-97`; executable annotation wrapper | External pair for `p4annotate.pm` | Perl, P4, `annotateutil.pm`; workspace/file/parse/pipe failure | `SCRIPT-ANNOTATE-001` |
| `support-script.p4annotate-pm` | `scripts/p4annotate.pm:1`, `docs/scripts.rst:70-97`; P4 annotation module | `--annotate-script`; cache, verify, log, version callback | Perl, P4, cache/log/filesystem; stale cache, local edits, malformed output | `SCRIPT-ANNOTATE-001` |
| `support-script.p4udiff` | `scripts/p4udiff:1`, `docs/scripts.rst:215-242`; P4 unified-diff generator | Produces data consumed by `--diff-file`; depot/sandbox/include/exclude | Perl, P4; multi-stage fstat/opened/diff/print failure and partial output | `SCRIPT-DIFF-001` |
| `support-script.select-pm` | `scripts/select.pm:1`, `docs/scripts.rst:337-375`; selection module | `--select-script`; TLA, age, owner, SHA/CL; annotate/base/diff globals | Perl and LCOV objects/globals; invalid criteria and lifecycle state | `SCRIPT-SELECT-001` |
| `support-script.simplify-pm` | `scripts/simplify.pm:1`; function display simplifier | `--simplify-script`; regex or pattern file, lifecycle counters | Perl, readable pattern file, regex; option/file/regex/lifecycle failure | `SCRIPT-SIMPLIFY-001` |
| `support-script.spreadsheet-py` | `scripts/spreadsheet.py:1`, `docs/man/spreadsheet.rst:20-90`; profile JSON to XLSX | Standalone analysis of `lcov`, `geninfo`, and `genhtml` profiles | Python, `xlsxwriter`, JSON/filesystem; missing module, bad schema, write failure | `SCRIPT-UTILITY-001` |
| `support-script.threshold-pm` | `scripts/threshold.pm:1`, `docs/scripts.rst:312-335`; threshold criteria module | `--criteria-script`; line/function/branch thresholds and signoff | Perl; invalid thresholds, absent coverage family, semantic rejection | `SCRIPT-CRITERIA-001` |
| `support-script.unreach-pm` | `scripts/unreach.pm:1`; unreachable branch/MC/DC module | `--unreachable-script`; annotated source and live mutable maps | Perl, LCOV objects, readable annotated source; parse and lifecycle failure | `SCRIPT-UNREACH-001` |

Upstream ships no resolve callback example. `SCRIPT-RESOLVE-001` MUST assert
that the option/protocol exists while the 23-file installation manifest contains
no shipped resolve implementation.

For every module/executable pair, cases MUST compare constructor or CLI option
handling, stdout, stderr, exit, missing file, missing dependency, nonzero child,
signal, caching, and semantic output. Pair similarity MUST NOT be assumed.

### Support Script Failure Oracles

| ID | Pinned source | Observable behavior that MUST be characterized |
| --- | --- | --- |
| `SCRIPT-VERSION-FAIL-001` | `scripts/P4version.pm:151-204`, `scripts/batchGitVersion.pm:48`, `scripts/batchGitVersion.pm:160-197`, `scripts/gitversion.pm:131-180` | P4 empty-inventory and later-command failures differ; local edits can be fatal without `--local-edit`. Batch Git can warn and continue with an incomplete database, and its token is package-global across objects. Git discovery failures may fall back to mtime, while later content lookup can be fatal and diff status can be ignored. |
| `SCRIPT-VERSION-PAIR-001` | `scripts/gitversion:45-63`, `scripts/gitversion.pm:87-94`, `scripts/getp4version:89-111`, `scripts/get_signature:69-73` | Executable wrappers do not expose every module option. P4 pipeline failure can become not-in-P4 fallback; output includes exact P4 token bytes. `get_signature` exits using a raw wait status that can truncate modulo process exit range, and a directory can produce empty stdout with zero status. |
| `SCRIPT-ANNOTATE-FAIL-001` | `scripts/annotateutil.pm:73-217`, `scripts/gitblame.pm:83-153`, `scripts/p4annotate.pm:129-255` | Cache support assumes host-loaded LCOV helpers, uses Storable data without a cross-process lock, and permits path traversal through cache keys. Wrapper and module failure categories differ; repository probing may fall back, while a started pipe that closes nonzero can die. No-argument wrappers can treat their own path as the filename. |
| `SCRIPT-DIFF-FAIL-001` | `scripts/gitdiff:120-185`, `scripts/p4udiff:187-464`, `bin/genhtml:4158-4266` | Shell paths/revisions are insufficiently quoted, partial stdout can precede failure, special filenames can be misparsed, and prefix mapping can desynchronize changed and unchanged keys. P4 has an unused startup-hard dependency, mismatches documented and parsed options, and can emit nonstandard add/delete or filtered-file behavior that `genhtml` does not consume as intended. |
| `SCRIPT-CRITERIA-FAIL-001` | `scripts/criteria:51-65`, `scripts/criteria.pm:66-130`, `scripts/threshold.pm:88-94` | The executable wrapper accepts a narrower option set than the module; documented suppress behavior and implemented signoff behavior require Oracle cases. Message newline handling differs across the pair. Invalid and out-of-range threshold values are fatal. |
| `SCRIPT-STATE-FAIL-001` | `scripts/context.pm:59-65`, `scripts/history.pm:98-188`, `scripts/select.pm:135-193`, `scripts/simplify.pm:81-156`, `scripts/unreach.pm:130-259` | Context mutates comments at construction and is sampled again at cleanup. History and select depend on host globals; profile keys can be interpreted as regex. Bad selection criteria, regex, pattern shape, restore length, unreachable group/index, or annotated-source directive can die after observable state mutation. |
| `SCRIPT-UTILITY-FAIL-001` | `scripts/analyzeInfoFiles:245-265`, `scripts/analyzeInfoFiles:330-340`, `scripts/spreadsheet.py:15-17`, `scripts/spreadsheet.py:169-175`, `scripts/spreadsheet.py:694-749` | `analyzeInfoFiles` uses external `wc`, has a last-line boundary to pin, and has nontrivial `--drop` exit behavior. Spreadsheet help requires `xlsxwriter`; bad JSON can be swallowed and skipped, all-bad input can fail later, and threshold CLI values may not update the values actually used. |

Security-sensitive shell, cache, or path observations MUST be captured as Oracle
evidence. Ferricov MUST NOT copy an injection or destructive-path defect merely
to make a test pass. Any intentional correction requires a named divergence,
inverse security tests, and a release claim that does not describe the changed
surface as unexplained parity.

## Installation Manifest

### Expected Upstream Layout

| ID | Pinned source | Upstream payload |
| --- | --- | --- |
| `INST-PATHS-001` | `Makefile:43-64` | Default prefix `/usr/local`; config `etc`; commands `bin`; library `lib/lcov`; man pages `share/man`; shared root `share/lcov`; support scripts `share/lcov/support-scripts`. `DESTDIR+PREFIX` must be absolute. |
| `INST-BIN-001` | `Makefile:74-77`, `Makefile:134-143` | Ten mode-0755 commands: `lcov`, `genhtml`, `geninfo`, `genpng`, `gendesc`, `perl2lcov`, `py2lcov`, `xml2lcov`, `xml2lcovutil.py`, and `llvm2lcov`. |
| `INST-SCRIPT-001` | `Makefile:78-80`, `Makefile:144-153` | Every dynamically enumerated file in `scripts/`, currently the 23 stable entries above, installed mode 0755, including `.pm` files. |
| `INST-LIB-001` | `Makefile:81`, `Makefile:154-162` | `lcovutil.pm` installed mode 0644 under `lib/lcov`. |
| `INST-MAN-001` | `Makefile:82-84`, `Makefile:163-174`, `docs/conf.py:83-153` | Ten generated man pages: nine section-1 pages, including `spreadsheet.py(1)`, plus `lcovrc(5)`. There is no `xml2lcov` man source. |
| `INST-HTML-001` | `Makefile:175-179` | Entire generated Sphinx HTML tree under `share/lcov/html`. |
| `INST-EXAMPLE-001` | `Makefile:181-187` | Current cleaned `example/` and `tests/` trees under `share/lcov`, including executable modes restored for test runners and script files. |
| `INST-CONFIG-001` | `Makefile:188-190` | `lcovrc` installed mode 0644 under `PREFIX/etc/lcovrc`. |
| `INST-REPORT-ASSET-001` | `bin/genhtml:8822-9829` | Report execution generates `gcov.css` and ruby, amber, emerald, snow, glass, and optional updown PNG files in report output. These are runtime report assets, not static install payload. |

### Installation Build And Dependency Contract

- `make install` has documentation generation as a hard prerequisite through
  `doc_finished` (`Makefile:125-134`). Sphinx and its configured theme are
  installation-time dependencies.
- Six primary/auxiliary commands and most support files use Perl. `py2lcov`,
  `xml2lcov`, `xml2lcovutil.py`, and `spreadsheet.py` use Python.
- `genpng` requires `GD.pm`; `perl2lcov` requires Devel::Cover DB and truth-table
  modules; `spreadsheet.py` requires `xlsxwriter`; VCS scripts require Git or P4
  as applicable.
- Python converters import the sibling `xml2lcovutil.py`; `lcov --capture`
  executes sibling `geninfo`; installed-path fixups and sibling discovery are
  therefore interaction contracts, not independent file checks.
- A staged install MUST place payload under `DESTDIR` while compiled and patched
  paths retain `PREFIX` without the staging root.

### Observed Installation Failure And Divergence Matrix

| ID | Pinned source | Oracle observation | Ferricov requirement |
| --- | --- | --- | --- |
| `INST-INTERP-001` | `Makefile:38-41`, `Makefile:134-161`, `bin/fix.pl:89-139` | Install does not pass `--fixinterp`; exact `/usr/bin/env` shebangs are also excluded from rewrite. The advertised Perl/Python override is therefore ineffective. | Differential evidence MUST pin the Oracle. Ferricov MUST document and review any intentional corrected behavior before claiming install parity. |
| `INST-CONFIG-DISCOVERY-001` | `lib/lcovutil.pm:1448-1460` | Runtime checks `$HOME/.lcovrc`, then `$LCOV_HOME/etc/lcovrc`, and stops after the first readable file. The compiled prefix alone does not select the installed system file. | Fresh-install cases MUST cover empty HOME, `LCOV_HOME`, both files, and explicit config. |
| `INST-UNINSTALL-001` | `Makefile:163-174`, `Makefile:194-223` | Uninstall enumerates `man/*` rather than installed build output, so man pages can remain. It recursively removes whole `lib/lcov` and `share/lcov` directories, including foreign sentinels. | Ferricov MUST NOT claim uninstall parity without an explicit reviewed safety decision and evidence. Tests MUST use isolated temporary roots. |
| `INST-PARTIAL-001` | `Makefile:134-190` | Installation is not transactional, has no rollback, and shell loops can leave partial payload or obscure an earlier element failure. | Injected-failure cases MUST record exit and exact partial manifest. Packaging MUST have an explicit atomicity policy. |
| `INST-PATH-001` | `Makefile:45-48`, `Makefile:134-190` | Relative roots are rejected; unquoted paths with spaces and GNU-style `install -D` create platform-specific failure. | Test relative, empty, absolute, staged, and space-containing paths on every claimed platform. |
| `INST-DIRTY-ASSET-001` | `Makefile:78-80`, `Makefile:181-187` | Scripts, examples, and tests come from dynamic working-tree enumeration rather than a pinned manifest. Untracked ordinary files can enter the install. | Ferricov generation MUST reject a dirty Oracle and MUST use a reviewed content-addressed manifest. |
| `INST-DOC-FAIL-001` | `Makefile:125-134`, `docs/Makefile:4-22`, `docs/conf.py:34-63` | Missing Sphinx or theme fails before payload install. Install also cleans source-tree example/test content. | Cases MUST verify pre-payload failure and source-tree effects in an isolated Oracle checkout. |
| `INST-TEST-RUN-001` | `tests/common.mak:2-18`, `tests/common.mak:76-83`, `tests/README.md:13-18` | Installed tests without explicit `LCOV_HOME` derive paths that can point to nonexistent `share/lcov/bin`, despite documentation suggesting direct use. | Test both unset and explicit `LCOV_HOME`; record the first real failure and resolved tool paths. |
| `INST-DOC-PATH-001` | `README.rst:125-139`, `Makefile:50-64` | Some README paths differ from the actual `share/man` and `share/lcov/tests` layout. | Installation truth comes from filesystem evidence; documentation mismatch MUST be recorded, not normalized away. |
| `INST-LICENSE-001` | `Makefile:71-72`, `Makefile:134-190` | `COPYING` enters the source archive but not `make install` payload. | Ferricov distribution MUST include or provide complete corresponding source, GPL text, retained notices, and dependency license metadata. Upstream omission is not permission to omit them. |

## `perl2lcov` And Devel::Cover Contract

The `perl2lcov` adapter direction is proposed. Architecture, implementation,
runtime, and compatibility qualification remain blocked until the runtime
manifest and all applicable `P2L-*` cases pass and ADR 0002 is updated.

### Required Runtime Manifest

Every result MUST record:

- Perl executable path, version, and content identity;
- Devel::Cover version, package version, and installed module identities;
- `Devel::Cover::DB` and `Devel::Cover::Truth_Table` identities;
- the `cover` preprocessing command and version;
- `grep`, gzip, locale, filesystem, and operating-system identities;
- database fixture identity and whether preprocessing completed; and
- LCOV Oracle image and executable identities.

LCOV v2.5 does not pin a Devel::Cover version. Package-manager latest versions
MUST NOT be treated as a stable runtime contract. The first candidate matrix is
Perl 5.36.0 with Devel::Cover 1.38; every other combination requires an
explicit matrix row and differential evidence.

### Runtime And Model Matrix

| ID | Pinned source | Normative Oracle behavior | Failure and interaction requirements |
| --- | --- | --- | --- |
| `P2L-LOAD-001` | `bin/perl2lcov:42-50` | `Devel::Cover::DB` and `Devel::Cover::Truth_Table` load at compile time before option parsing. | Missing either module fails even help/version through raw Perl load failure; it is not an ignorable LCOV `package` error. |
| `P2L-DEP-001` | `README.rst:159-174`, `.github/workflows/run_test_suite.yml:56-87` | Upstream names dependencies but does not content-pin the installed package. | Runtime/package drift is a matrix change, not implicit compatibility. |
| `P2L-CLI-001` | `bin/perl2lcov:154-164`, `lib/lcovutil.pm:1433-1525` | Default output is `perlcov.info`; default test name is empty; `--output/-o` and `--testname` extend shared parsing. | Invalid option exits one with usage hint; help/version require dependencies and otherwise exit zero. No-DB behavior is governed by empty output, not an explicit positional-count check. |
| `P2L-RC-001` | `lib/lcovutil.pm:1331-1508` | Config includes, environment expansion, deprecated keys, CLI list override, and `--rc` use shared rules. | Explicit unreadable config, loops, unknown keys, bad values, and discovery precedence MUST be tested. |
| `P2L-DB-001` | `bin/perl2lcov:168-181` | Each argument opens a Devel::Cover DB and traverses `cover->items`. A raw or unprocessed DB can appear empty and should direct the user to run `cover`. | Constructor and object-shape exceptions are raw Perl failures. Empty is an LCOV `empty` error that can be ignored before continuing to another DB. |
| `P2L-DB-002` | `bin/perl2lcov:182-207` | Files from multiple DBs merge into the same LCOV model by original file and test identity; substitution affects initial filtering/logging but the stored key remains original. | DB order, duplicate file, duplicate test, and object-method mismatch MUST be differential cases. |
| `P2L-PATH-001` | `bin/perl2lcov:183-195`, `bin/perl2lcov:243-249` | Substitution, initial include/exclude, stored path, source existence, checksum/version, later filters, resolve, and serialization occur at different stages. | These stages MUST NOT be collapsed into one path normalization. Existence before and after substitution requires inverse cases. |
| `P2L-CRIT-001` | `bin/perl2lcov:204-240` | `statement`, `branch`, `condition`, and `subroutine` are recognized; `pod`, `time`, and `path` are ignored; unknown categories enter the category error path; statement is mandatory. | Ignored unknown category is dropped. Missing statement uses `unsupported` and skips the file. Bad object shape is raw Perl failure. |
| `P2L-CONSIST-001` | `bin/perl2lcov:251-264` | Every branch, condition, and subroutine location must also have statement location. | Missing line location is `inconsistent`; ignore may continue. Hit-count consistency is a separate downstream concern. |
| `P2L-STMT-001` | `bin/perl2lcov:266-269` | Statement location supplies line count and drives the conversion loop. | Negative, string, undef, very large, and malformed nested values require exact behavior cases. |
| `P2L-SUB-001` | `bin/perl2lcov:200-228`, `bin/perl2lcov:271-283`, `bin/perl2lcov:378-427` | Subroutine data defines functions; names containing `BEGIN` or `__ANON__` are skipped; source `grep` supplies package/sub extents and end-line correction. | Process creation and malformed grep output can die. Pipe close status is not checked. Package/global/nested/same-line functions and partial grep output MUST be tested. |
| `P2L-COND-001` | `bin/perl2lcov:285-353` | Condition truth-table blocks take precedence over raw branch data on the same line. Inputs map to expression parts; `X` is omitted and zero adds negation. Arity mismatch falls back to the original expression. | Truth-table order and expression reconstruction are runtime-version-sensitive and require exact fixture output, not logical-equivalence normalization. |
| `P2L-BR-001` | `bin/perl2lcov:355-370` | Without condition data, branch data produces true/false elements in one block. A zero statement count forces taken values to `-`. | Nested object shape, nonnumeric count, and coexistence with condition data MUST be tested. |
| `P2L-MODEL-001` | `bin/perl2lcov:266-427` | Lines, functions, and branches accumulate into per-test and summary maps; function end lines are written back to testcase objects. | Duplicate DB/file/line/function/branch behavior belongs to the LCOV model contract and MUST NOT be implemented as unverified last-write-wins. |
| `P2L-FILTER-001` | `bin/perl2lcov:432`, `lib/lcovutil.pm:8793-8831` | All DB conversion completes before shared filters. Filters may read source, invoke callbacks, derive data, and remove coverpoints/files. | The adapter is not a pure DB decoder. Source, callback, filter, format, and partial-mutation behavior MUST remain in the Oracle comparison. |
| `P2L-OUT-001` | `bin/perl2lcov:433-434`, `lib/lcovutil.pm:9455-9682` | Comments are added before sorted tracefile output. Function and branch coverage start enabled but shared `--no-*` settings may override serialization. Ignored empty can create a zero-byte output. | Ordinary paths truncate; stdout and gzip use shared output paths. Open failure is fatal; late close/gzip/disk failure may not affect exit and requires dedicated fixtures. |
| `P2L-CHECKSUM-001` | `bin/perl2lcov:243-249`, `lib/lcovutil.pm:9513-9672` | Checksum requires the original source path. Version callback runs only when that source exists and a nonempty result writes `VER`. | Source/substitution inversion, callback cache, missing source, ignore, and output checksums MUST be compared. |
| `P2L-CRITERIA-001` | `bin/perl2lcov:436-438`, `lib/lcovutil.pm:3164-3217` | Output is written before fail-under and criteria evaluation. Any nonzero final criteria status becomes process exit one. | A criteria failure leaves a complete output file. Callback exception and multiple criteria statuses require exact message/status evidence. |
| `P2L-EXIT-001` | `bin/perl2lcov:438-444` | Normal explicit exit is zero or one based on coverage criteria. Pattern warnings, filter summary, and message summary follow writing. | Shared keep-going errors are not unconditionally folded into final exit; a non-criteria error may leave exit zero. This MUST be pinned before compatibility. |
| `P2L-CLEANUP-001` | `bin/perl2lcov:432-444`, `lib/lcovutil.pm:1049-1068` | `perl2lcov` does not call `cleanup_callbacks()` and does not install the same cleanup path as primary tools. | Context/finalize/destructor timing and teardown failure MUST be recorded. Parser construction is not proof of callback invocation. |

### Shared Option Applicability

| Family | Required interpretation for `perl2lcov` |
| --- | --- |
| Output identity | Output, test name, comments, tool name, and test-name forgetting can directly change tracefile or messages. |
| Coverage selection | Function and branch start enabled; no-function/no-branch may override. MC/DC parses but has no native Devel::Cover construction path in this converter. |
| Path and source | Substitute, include/exclude, source directory, resolve, filters, erase, omit, checksum, and version act at different phases and MUST retain those phases. |
| Error policy | Ignore count, suppression, keep-going, expected message count, and final exit require exact category and ordering evidence. |
| Callbacks | Version, criteria, resolve, context, unreachable, and history may be constructed by shared parsing; only runtime call logs establish applicability. |
| Performance | Parallel, memory, sort, temporary directory, and preserve mostly affect shared processing; the DB traversal loop remains ordered by DB argv. |
| Logging | Quiet, verbose, debug, profile, and message log change observable channels/files and MUST NOT be discarded by default normalization. |

## Required Differential Case Registry

### Callback Cases

- `CB-CFG-001`: split rules, repeated values, module suffix, constructor args.
- `CB-ARGS-001`: legacy PipeHelper counts, nonexistent first path, exact argv,
  shell strings, quotes, whitespace, glob, and metacharacters.
- `CB-ENV-001`: CWD, PATH, locale, environment, umask, stdin, descriptors,
  signals, and tool globals.
- `CB-IO-001`: empty and multiline output, bytes, CRLF, missing newline, stderr,
  large output, broken pipe, and child capture.
- `CB-FAIL-001`: load, constructor, process creation, nonzero, command-not-found,
  signal, method/lifecycle exception, ignore count, keep-going, and per-callback
  status interpretation.
- `CB-CACHE-001`: exact filename keys, version/resolve caching, and parent/child
  state merge.
- `CB-GLOBAL-001`: shipped globals, cross-callback state, same-basename `%INC`,
  constructor/destructor, CWD/environment/umask, and partial mutation.
- `CB-LIFECYCLE-001`: serial/parallel/forced-parallel constructor, start, save,
  restore, finalize, destructor, save failure, Storable failure, and identity.
- `CB-LIFE-START-FAIL-001`, `CB-LIFE-SAVE-FAIL-001`,
  `CB-LIFE-RESTORE-FAIL-001`, `CB-LIFE-FINALIZE-FAIL-001`, and
  `CB-LIFE-SAVE-INDEX-001`: independent failure points and positional payload
  identity, cross-linked to `PAR-CALLBACK-LIFECYCLE-FAIL-001`.
- `CB-HOST-001`: negotiation, arbitrary byte scalars, truncation, oversize,
  host death/signal, writeback order, partial mutation, and unsafe restart.
- Each `CB-<SURFACE>-001` section above is a separately executable suite.
- `CB-REACH-001` covers every parser-accepted callback on every auxiliary
  command and records constructed versus invoked behavior.

### Support And Installation Cases

- `SCRIPT-PAIR-001`: Git blame, P4 annotate, Git version, P4 version, and
  criteria module/executable pairs.
- `SCRIPT-VERSION-001`, `SCRIPT-ANNOTATE-001`, `SCRIPT-DIFF-001`,
  `SCRIPT-CRITERIA-001`, `SCRIPT-CONTEXT-001`, `SCRIPT-SELECT-001`,
  `SCRIPT-SIMPLIFY-001`, `SCRIPT-HISTORY-001`, `SCRIPT-UNREACH-001`, and
  `SCRIPT-UTILITY-001` cover every manifest row.
- `INST-LAYOUT-001`: exact path, mode, command, library, 23 scripts, man, HTML,
  ten examples, 205 tests, and configuration manifest.
- `INST-STAGE-001`: staged root versus embedded prefix.
- `INST-INTERP-001`: custom Perl/Python settings and installed shebang bytes.
- `INST-CONFIG-DISCOVERY-001`: HOME, `LCOV_HOME`, explicit file, and precedence.
- `INST-UNINSTALL-001`: before/after manifest, man residue, and foreign sentinel
  behavior in an isolated root.
- `INST-PARTIAL-001`: injected failure at each install loop family.
- `INST-DOC-FAIL-001`: missing builder, theme, and build failure before payload.
- `INST-PATH-001`: relative, empty, staged, absolute, and space-containing roots.
- `INST-DIRTY-ASSET-001`: untracked sentinels and dirty-Oracle rejection.
- `INST-TEST-RUN-001`: installed tests with unset and explicit `LCOV_HOME`.
- `INST-LICENSE-001`: source archive and binary/install distribution license
  manifests.

### `perl2lcov` Cases

- `P2L-DEP-001`: missing DB, missing Truth_Table, complete dependencies, and
  help/version/normal invocation with recorded runtime identities.
- `P2L-DB-001`: nonexistent, raw, empty, corrupt, mixed empty/valid, multiple
  valid, and DB order reversal.
- `P2L-CRIT-001` and `P2L-SHAPE-001`: every supported/ignored/unknown criterion
  and malformed, undef, string, negative, and large nested values.
- `P2L-MERGE-001`: same file/test, same file/different test, same basename/different
  path, duplicate coverpoints, and DB order reversal.
- `P2L-PATH-001`: substitution and existence inversions combined with include,
  exclude, missing filter, checksum, version, and resolve.
- `P2L-SUB-001`, `P2L-GREP-001`, `P2L-COND-001`,
  `P2L-PRECEDENCE-001`, `P2L-TAKEN-001`, and `P2L-ENDLINE-001` pin conversion
  and external-source behavior.
- `P2L-FILTER-001`, `P2L-OUT-001`, `P2L-EMPTY-001`, `P2L-ERROR-001`,
  `P2L-EXIT-001`, and `P2L-CALLBACK-001` pin shared runtime, failure, output,
  close, keep-going, and cleanup behavior.
- `P2L-DETERMINISM-001`: repeated fixed DB, DB order, locale, and hash-seed
  variation.
- `P2L-UPSTREAM-REG-001`: preserve and extend
  `tests/perl2lcov/perltest1.sh:22-205`, including downstream `lcov` and
  `genhtml` consumption.

## Evidence And Comparison Requirements

Every case MUST retain, before normalization:

- argv and working directory;
- environment and declared runtime manifest;
- raw stdout and stderr bytes;
- exit status, signal, and child status;
- ordered callback and lifecycle transcript;
- tracefile/model semantics where applicable;
- filesystem contents, raw path bytes, modes, links, and partial artifacts; and
- Oracle and candidate executable identities.

Only approved normalizers may be used. Callback argument/order/status, tracefile
bytes, install path/mode, license presence, or state writeback MUST NOT be
normalized away.

The expected execution form is:

```bash
cargo run -p ferricov-oracle --bin differential -- \
  compat/cases/<suite>.json \
  compat/launchers/lcov-v2.5-oracle.json \
  compat/launchers/<ferricov-candidate>.json \
  <evidence-directory>

python3 compat/verify.py --results <evidence-directory>
```

Before M1 differential model work, the Oracle runner MUST support real
`coverage_model` and `tracefile` comparisons and MUST reject reverse fixtures
that alter path bytes, a record, or a counter. Existing exit/stdout/stderr and
filesystem collection alone is not evidence of M1 semantic compatibility.

## Release Gates

| Claim | Required gate |
| --- | --- |
| Native external callback runner | All common external and applicable callback-specific cases pass. This claim is independent of the Perl host. |
| Perl module callback support | State/wire design accepted; all PM, global, lifecycle, host, object, mutation, and module cases pass for a published Perl/platform matrix. |
| `perl2lcov` support | Launcher contract implemented; all `P2L-*` cases pass for a published Perl/Devel::Cover/cover/grep matrix. |
| Installed support scripts | All 23 manifest entries have reviewed classification, dependencies, interactions, cases, and evidence. |
| Installation compatibility | Fresh install, staging, config, asset, dependency, uninstall policy, license, and platform cases pass or have reviewed declared divergences. |
| M5 complete installed suite | Every applicable row above passes. Proposed host status, missing runtime matrix, unreviewed support entry, or unexplained installation difference blocks the claim. |

Correctness evidence for a fixture MUST pass before its performance result is
valid. Host startup, serialization, fork scaling, callback ordering, RSS, and
converter performance MUST NOT weaken state, data, failure, or installation
semantics.
