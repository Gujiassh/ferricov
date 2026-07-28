# ADR 0002: Callback And Perl Runtime Boundary

## Status

Accepted on 2026-07-27 only for the architecture and core boundary: the
canonical model remains Perl-neutral, callback-free core workflows require no
Perl, and every optional Perl-dependent lane remains outside that core.

The native external callback runner, a separate `.pm` compatibility host or
pinned same-interpreter front end, and a `perl2lcov` launcher/adapter are
**proposed**, not accepted implementations. Perl 5.36.0 with Devel::Cover 1.38
is an environment candidate only. No callback behavior, Perl runtime,
`perl2lcov` behavior, or implementation is qualified by this ADR.

## Decision Scope

This decision covers the installed callback protocols and Perl-dependent
runtime behavior of LCOV `v2.5` at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`:

- `--context-script`
- `--version-script`
- `--annotate-script`
- `--criteria-script`
- `--resolve-script`
- `--unreachable-script`
- `--select-script`
- `--simplify-script`
- `--history-script`
- `perl2lcov` and its `Devel::Cover` database input

The word "script" in the upstream option names does not imply one execution
model. Except for `--unreachable-script`, LCOV accepts either an external
executable or a Perl module selected solely by a `.pm` filename suffix. Those
forms have different argument, data, process, state, and failure contracts.

This ADR does not make internal Perl package structure part of Ferricov's Rust
architecture. Any accepted Perl integration must expose the object and state
protocols that LCOV 2.5 deliberately publishes to user callbacks.

## Context

Ferricov must replace LCOV 2.5 without requiring Perl for ordinary `lcov`,
`geninfo`, or `genhtml` workflows. It must also preserve workflows that provide
existing callback modules and workflows that translate `Devel::Cover`
databases. A standalone Rust process cannot execute arbitrary Perl modules or
read every `Devel::Cover::DB` representation faithfully.

The upstream implementation makes the boundary observable:

1. A callback whose first configured argument ends in `.pm` is loaded with
   `require`; all other callback commands are external processes.
2. A module class is derived from the module filename, constructed once in the
   parent, and may run later in forked children.
3. Module callbacks can access the Perl interpreter, LCOV packages and globals,
   inherited environment, current directory, and arbitrary host resources.
4. External callbacks use stdout and process status as protocol fields. Some
   paths use direct argument-vector execution while version comparison and
   selection construct a shell command.
5. Parallel callback state is explicitly transferred through optional
   `start`, `save`, `restore`, and `finalize` methods and Perl `Storable` data.
6. `perl2lcov` loads `Devel::Cover::DB` and
   `Devel::Cover::Truth_Table` before command-line parsing and traverses the
   processed coverage database through those APIs.

The public manuals contain discrepancies with the pinned implementation. The
executable at the pinned commit remains the behavioral Oracle:

- The manual presents module version comparison as a true-on-match operation,
  but the implementation and shipped modules use `0` for match and non-zero
  for mismatch.
- The manual's external version comparison example puts the filename before
  the IDs, but the implementation invokes `--compare first_id second_id
  filename`. The meanings of the two ID positions depend on the call site.
- The manual names the unreachable arguments as summary then per-test data,
  while the implementation and shipped `unreach.pm` pass per-test data then
  summary data.
- The `select_script` manual describes a zero-indexed line number; the code
  passes the coverage map key. That value must be pinned with an Oracle case
  rather than normalized to the prose description.

No implementation may resolve these discrepancies by intuition.

## Audited Protocols

### Common Callback Construction

The configured option is a list of strings. When exactly one string is
present, LCOV splits it on the configured `split_char` (comma by default).
When an option is repeated, its strings are concatenated without that split.
This produces observably different constructor and executable arguments.

For a path ending in `.pm`, LCOV 2.5:

1. takes the directory and basename of the first argument;
2. removes `.pm` from the basename to derive the class name;
3. temporarily prepends the directory to Perl `@INC`;
4. executes `require basename.pm`;
5. invokes `Class->new(module_path, callback_args...)`; and
6. rejects an undefined constructor result as a `package` error.

For every other path, LCOV constructs a `ScriptCaller` with the configured
arguments. Required operation arguments are appended after user arguments.
There is no callback sandbox.

Pipe-backed external callbacks also have a legacy argument rewrite. When
`PipeHelper` receives exactly two arguments, or exactly four for `criteria`, and
the first argument does not name an existing path, it splits that first argument
on spaces and then appends the operation arguments. This rewrite occurs before
list-form `open` and is distinct from both the configured `split_char` behavior
and shell parsing.

### Per-Callback Contracts

| Callback | Perl module call and return | External process protocol | Tools and semantic effect |
| --- | --- | --- | --- |
| context | `context() -> hashref` | No required arguments. Every stdout line is split at the first run of spaces into key and value; repeated keys concatenate values with `\n`. | `lcov`, `geninfo`, and `genhtml`. Collected at cleanup into profile `context`; configuring it enables profile collection. Constructor side effects occur at configuration time. |
| version extract | `extract_version(file) -> scalar or undef` | Appends `file`; the first stdout line is the version, with line ending removed. Empty output is `undef`; an empty line is an empty version. | Shared capture, merge, filtering, conversion, and report checks. Results are cached by the exact filename string. File existence may be checked first. |
| version compare | `compare_version(first_id, second_id, file) -> 0 on match` | Shell command with `--compare first_id second_id file`; stdout is not protocol data and process wait status determines match. | Exact unequal IDs trigger the callback; equal defined strings bypass it. The ID positions vary by merge/filter/report call site. Non-zero means mismatch and enters `version` handling. |
| annotate | `annotate(file) -> (system_style_status, arrayref)` where each entry is `[text, abbreviated_author, full_author_or_undef, W3CDTF_date, commit_id]` | Appends `file`. All stdout lines are split into at most four pipe-delimited fields: `commit_id|author_data|date|source_text`; `author_data` is split once on `;`. | `genhtml`. Annotation controls source text, owner/date bins, tooltips, and selection. `NONE` is semantic. A file cannot mix committed and `NONE` rows. |
| criteria | `check_criteria(name, type, hashref) -> (status, message_arrayref)` | Appends `name`, `type`, and compact JSON data. Non-empty stdout lines are messages; wait status is the criteria status. | File/directory/top selection is controlled by `criteria_callback_levels`. Date/owner bins are optional and `genhtml`-only. Any non-zero result makes the final tool result non-zero after processing; it is not merely a callback transport failure. |
| resolve | `resolve(file) -> path or undef` | Appends `file`; first stdout line is the path with line ending removed. Empty/no output means not found. | Runs after substitutions and search paths fail. A returned path may be absolute or relative to callback CWD. Successful results are cached by requested filename. `geninfo` also resolves GCNO paths. |
| unreachable | `exclude(type, ReadCurrentSource, per_test_map, summary_map) -> changed` | Not supported. A `.pm` module is required. | `type` is `branch` or `mcdc`. The callback may mutate summary and every testcase map, including excluded flags and totals. Its return reports whether data changed. |
| select | `select(LineData_or_undef, SourceLine_or_undef, file, line_key) -> boolean` | Appends JSON encodings of `LineData::to_list` and `SourceLine::to_list` (or empty strings), then file and line key. It executes through a shell command; process wait status is used as the result, so exit zero is false and non-zero is true. Stdout is not the result. | `genhtml`. False removes the coverpoint unless it is retained as configured context around another selected line. Module arguments are objects, not JSON. |
| simplify | `simplify(original_name) -> display_name` | Appends original name; first stdout line is the display name. Missing output is a broken callback. | `genhtml` function-detail display only. It must not change the stored coverage function identity or matching behavior. |
| history | `history(element_name) -> predicted_seconds or undef` | Appends element name; first stdout line is the prediction. An empty line means unknown; missing output is a broken callback. | `lcov`, `geninfo`, and `genhtml`. It affects task ordering and load balancing, not coverage meaning. |

External callbacks receive no structured input on stdin. Their stdin is simply
inherited. Pipe callbacks have stdout consumed by LCOV while stderr remains on
the tool's stderr path, subject to the parent tool's parallel output capture.
The pinned implementation removes CR from consumed line endings. Path and text
arguments are Perl strings and are not declared to be UTF-8.

The actual external execution mechanism is part of compatibility:

- context, version extraction, annotate, criteria, resolve, simplify, and
  history use Perl's list-form `open(..., "-|", @argv)`;
- version comparison and selection build one command string and execute it via
  the shell; and
- callback commands are trusted arbitrary code. Ferricov will document this
  and will not present them as sandboxed or safe for untrusted input.

### Callback Failure And Ignore Semantics

The following failure classes are distinct and must remain distinct:

- module load, constructor failure, or `save` without `restore`: `package`;
- module method and lifecycle exceptions: `callback` unless a more specific
  call-site class applies;
- direct `PipeHelper` process creation failure: `callback`; non-zero status on
  pipe close is handled according to that pipe callback's own error checking;
- annotation non-zero status: `annotate`, with source-load or synthesis
  fallback only when the applicable error is ignored;
- version disagreement: `version`; shell command-not-found during external
  version comparison is a non-zero wait status and is therefore interpreted as
  a version mismatch, not as `callback`;
- external selection uses shell wait status as its boolean result, so shell
  command-not-found and other non-zero statuses select the item rather than
  producing a callback failure;
- source existence check before version or annotation: `source`;
- criteria rejection: retained as a criteria result and final non-zero tool
  status after other processing;
- child serialization/reaping failure: `parallel` or child-process failure in
  addition to the originating callback message.

Call-site recovery is also observable. A selection exception selects the item
instead of dropping it. A simplify exception retains the original name. A
resolve failure can leave the original path in use. Annotation failure can
fall back to normal source loading. Unreachable mutation before an exception
may be visible and therefore needs a reverse case. Error suppression must use
the same `--ignore-errors` categories and message-count behavior as other LCOV
errors.

### Parallel Module Lifecycle

A Perl callback object is initialized once in the parent. If parallel work is
enabled, including through `LCOV_FORCE_PARALLEL`, LCOV registers lifecycle
methods as follows:

1. `start()` is optional and runs when a child begins work, but only for a
   module that implements both `save()` and `restore()`.
2. `save()` runs in the child before it exits. Its scalar result is included in
   the child's `Storable` payload.
3. `restore(saved)` runs in the parent when that child is reaped.
4. Implementing `save()` without `restore()` is a `package` error.
5. `finalize()` is optional and runs late in the parent in both serial and
   parallel execution.

Multiple child processes can invoke the inherited callback object
simultaneously. Module-global state, open files, locks, caches, PIDs, signal
handlers, and output ordering can therefore be observed by user code. External
callbacks do not receive lifecycle calls and must coordinate their own state.

## `perl2lcov` Runtime Contract

The pinned `perl2lcov` is not a generic tracefile parser. It is a Perl program
that imports `Devel::Cover::DB` and `Devel::Cover::Truth_Table` at compile time.
It expects one or more processed coverage database directories, normally after
the user has run `cover DB -silent 1`. A raw or empty database produces the
specific `empty` path that suggests running `cover` first.

The converter:

- defaults to `perlcov.info` in CWD and accepts `--output/-o` and `--testname`;
- accepts shared LCOV options through `lcovutil.pm`, including configuration,
  filters, checksums, version callbacks, criteria, errors, and comments;
- merges multiple database directories into one tracefile model;
- uses statement data for lines, subroutine data for functions, condition data
  in preference to branch data, and ignores `pod`, `time`, and `path` data;
- invokes external `grep` while deriving package and subroutine extents from
  readable source files;
- emits `unknown category`, `unsupported`, `source`, `inconsistent`, and
  `empty` behavior through the shared LCOV error system;
- applies shared filters before writing and criteria after writing; and
- exits according to criteria status after summary and message reporting.

Devel::Cover databases are runtime-versioned external data, not a stable format
owned by Ferricov. The first candidate environment is the existing Oracle
image: Debian bookworm, Perl `5.36.0`, Debian `libdevel-cover-perl` `1.38-1+b1`
(`Devel::Cover` 1.38). Other Perl and Devel::Cover combinations require explicit
matrix entries and differential evidence. They are not implied compatible.

The Oracle image installs `perl`, `libdevel-cover-perl`, and the callback
support dependencies. A base Ferricov workflow must not require them, but a
full-suite package claiming compatible `perl2lcov` behavior must supply or
require a qualified Perl runtime and Devel::Cover installation.

## Decision

### 1. Proposed Native External Callback Runner

Ferricov proposes to implement external executable callbacks behind a Rust
boundary without a Perl dependency. If accepted after the contract and Oracle
gates below, the runner will preserve per-operation argument order, option
splitting, CWD, inherited environment, stdout/stderr routing, CR/LF handling,
process status interpretation, caching, failure category, and parallel call
placement.

The runner will reproduce the pinned distinction between direct argv execution
and shell command execution. This is required for compatibility, despite the
security and quoting liabilities. Callback configuration is trusted code.

### 2. Proposed Perl Compatibility Host For `.pm` Callbacks

The separate Perl compatibility host is a candidate architecture, not yet an
accepted implementation decision. Before host implementation begins, Ferricov
must specify a per-tool readable/writable Perl state contract that covers:

- every tool and package global exposed to callback code, including its initial
  value, ownership, lifetime, and permitted mutation;
- state shared across different callback objects and successive callback calls;
- `%INC` identity, load ordering, and collisions between modules with the same
  basename;
- constructor and destructor timing and their observable side effects;
- callback changes to CWD, environment variables, and umask; and
- propagation and writeback order across constructor, callback, lifecycle,
  child, parent, and tool state.

This contract is required by shipped modules, not only adversarial user code.
For example, `scripts/context.pm:59-65` appends to
`@lcovutil::comments`; `scripts/select.pm:174-193` reads
`@SourceFile::annotateScript`, `@main::base_filenames`, and
`$main::diff_filename`; and `scripts/history.pm:98-104` reads
`$lcovutil::tool_name` and `$main::callFromLcov`.

The host wire contract must likewise be specified before implementation. It
must define protocol negotiation, byte-preserving scalar and object framing,
size limits, truncated or oversized frame handling, host exit and signal
handling, mutation writeback ordering, and the point after which a host cannot
be silently restarted because observable mutation may already have occurred.

If the contracts and Oracle evidence show that a separate process can reproduce
the documented arbitrary same-interpreter access, Ferricov may accept the host
design. If that access cannot be reproduced, affected `.pm` workflows must run
through a pinned Perl front-end in the same interpreter context instead of
receiving a full compatibility claim. Neither outcome changes the accepted
Perl-neutral core boundary.

The proposed host would avoid embedding a Perl interpreter in the main Rust
process and would start only when a configured callback path ends in `.pm`. No
host would start for callback-free or executable-only workflows. If accepted,
the host must:

- use the user-provided qualified `perl` selected by the installed launcher
  environment;
- load the callback and derive its class exactly as LCOV 2.5 does;
- initialize one parent callback object;
- expose typed, length-delimited requests to Rust without using stdout as both
  protocol and user-log transport;
- execute child calls through fork when Ferricov's equivalent LCOV work is
  parallel;
- preserve `start/save/restore/finalize` ordering and Perl `Storable`
  serializability at the callback boundary;
- construct LCOV 2.5-compatible Perl objects for object-valued protocols;
- return callback stdout, stderr, status, exceptions, profile updates, and
  mutations without changing their semantic order; and
- run with inherited CWD, environment, umask, file descriptors, and host
  permissions unless an Oracle case proves LCOV changes one of them.

For `unreachable`, any accepted host design must transfer the full affected source
and coverage maps losslessly, allow the callback to mutate LCOV-compatible Perl
objects, and apply returned model mutation only according to Oracle behavior.
For `select`, it must provide the pinned `LineData` and `SourceLine` object
behavior rather than passing JSON to a module.

An accepted host or pinned Perl front-end may reuse or adapt pinned upstream
GPL-licensed Perl code. It must not be generalized into Ferricov's core coverage
model, and Rust code must not depend on Perl package layout.

### 3. Proposed Optional Perl Adapter For `perl2lcov`

The candidate installed `perl2lcov` entry point is a Ferricov launcher backed
by a versioned GPL Perl adapter using `Devel::Cover::DB` and
`Devel::Cover::Truth_Table`. If this direction is accepted after launcher,
runtime, and differential qualification, it starts only for this command. The
adapter would own database interpretation; Ferricov would own supervision,
evidence capture, and integration with the public command installation.

The first compatible adapter will preserve the pinned conversion and shared
option behavior before any Rust-native replacement is considered. Replacing
the adapter is allowed only when all runtime, model, tracefile, diagnostic,
filesystem, and exit cases remain differential passes.

Missing Perl or Devel::Cover is a feature-runtime failure, not permission to
silently emit an empty tracefile, skip the command, or fall back to a guessed
database parser.

### 4. Release Claims

- Base `lcov`, `geninfo`, and `genhtml` workflows must run without Perl when no
  `.pm` callback is configured.
- External callback support may be claimed independently after its matrix
  passes.
- Perl-module callback support may be claimed only for the published Perl
  matrix and after shipped examples plus adversarial callbacks pass in serial
  and parallel modes.
- `perl2lcov` compatibility may be claimed only for published Perl and
  Devel::Cover versions.
- A missing qualified optional runtime narrows the installed-suite claim. It
  must be visible in package metadata and compatibility reports.

## Considered Options

### Rewrite Every Callback As A Rust Plugin API

Rejected. Existing command lines, executable protocols, `.pm` modules, Perl
objects, process status, and fork lifecycle would stop working. A new Rust API
may be added only after LCOV 2.5 compatibility and cannot replace this surface.

### Require Perl For The Entire Tool Suite

Rejected. This would keep implementation simple but violate the project goal
that normal primary-command workflows are standalone Rust. Perl is necessary
only when the selected public feature requires it.

### Embed `libperl` In Every Ferricov Process

Rejected. It imposes Perl ABI and packaging constraints on the base binaries,
expands unsafe in-process state, and still does not automatically reproduce
LCOV's parent/fork/restore lifecycle.

### Spawn A Fresh Perl Process For Every Module Call

Rejected. It loses constructor-once behavior, module state, callback caches,
fork inheritance, lifecycle methods, PID behavior, and performance. It is not
compatible with stateful modules.

### Translate Arbitrary Perl Modules To Rust

Rejected. Translation cannot preserve arbitrary Perl execution, dependencies,
side effects, or dynamic use of LCOV objects.

### Parse Devel::Cover Databases Directly In Rust Now

Rejected for the first compatible release. The database is governed by
Devel::Cover runtime APIs and has no pinned stable wire contract in this
project. Direct parsing would create an unsupported format implementation
before semantic fixtures exist.

### Declare Perl Features Unsupported

Rejected. `.pm` callbacks, installed support modules, and `perl2lcov` are public
LCOV 2.5 surfaces and are explicitly in Ferricov's complete-compatibility
scope.

## Compatibility Cases Required Before Implementation Claims

All cases compare raw stdout, stderr, exit status, ordered callback logs,
filesystem effects, output tracefile/report semantics, and child status before
any allowed normalization.

### Common Loading And Process Cases

- `CB-LOAD-001`: `.pm` suffix detection, relative and absolute module paths,
  basename-to-class mapping, `@INC`, constructor first argument, and undefined
  constructor result.
- `CB-ARGS-001`: one comma-separated option versus repeated option arguments,
  empty arguments, custom `split_char`, whitespace, quotes, glob characters,
  shell metacharacters, and the nonexistent-first-path legacy rewrite at the
  two-argument and criteria four-argument counts.
- `CB-ENV-001`: CWD, PATH, locale, umask, inherited environment, stdin state,
  file descriptors, and module access to tool globals.
- `CB-IO-001`: empty output, empty first line, multiple lines, CRLF, missing
  trailing newline, non-UTF-8 bytes, stderr, large output, and broken pipe.
- `CB-FAIL-001`: missing executable/module/dependency, constructor exception,
  process launch failure, signal death, exit codes 1 and 255, method exception,
  ignored versus fatal category, keep-going behavior, shell command-not-found,
  and the distinct version-mismatch and select-truthy interpretations of
  external shell status.
- `CB-CACHE-001`: exact filename cache keys and parent/child cache merge for
  version and resolve callbacks.
- `CB-GLOBAL-001`: shipped context `--comment` mutation, select and history
  globals, cross-callback shared globals, same-basename `%INC` behavior,
  destructor timing, and CWD, environment, and umask mutation.
- `CB-HOST-001`: protocol negotiation, arbitrary byte scalars, truncated and
  oversized frames, host death and signal handling, writeback ordering, and no
  silent restart after partial mutation.

`CB-GLOBAL-001` and `CB-HOST-001` block Perl-host implementation claims. They do
not block evaluation of the proposed native external callback runner, whose own
qualification remains blocked on the applicable external `CB-*` cases.

### Callback-Specific Cases

- `CB-CONTEXT-001`: script line parsing, repeated keys, missing values, module
  hash validation, constructor side effects, profile auto-enable, and cleanup
  timing.
- `CB-VERSION-001`: equal-ID bypass, extract empty/undef, executable actual
  compare order at every call site, module zero-on-match convention, mismatch diagnostics,
  `check_existence_before_callback`, compute-missing-version, and cache use.
- `CB-ANNOTATE-001`: executable and module rows, `|` in source text, `;` in
  author data, CRLF, W3CDTF parsing, `NONE`, mixed committed/uncommitted rows,
  wrong line counts, non-zero status, ignore, ordinary source fallback, and
  synthesis.
- `CB-CRITERIA-001`: file/directory/top levels, line/function/branch/MC/DC
  totals, differential categories, date/owner bins, empty bins, JSON versus
  hash input, multiline messages, signoff, delayed final failure, and serial
  versus parallel aggregation.
- `CB-RESOLVE-001`: source and GCNO resolution after substitution/search,
  relative result against callback CWD, empty/undef, nonexistent returned path,
  aliases, cache, exception, and ignored source/callback errors.
- `CB-UNREACH-001`: module-only enforcement; actual per-test/summary argument
  order; branch and MC/DC mutation; excluded flags and total recomputation;
  false changed result after mutation; partial mutation before exception; and
  serial/parallel lifecycle.
- `CB-SELECT-001`: module objects versus exact external JSON arrays, undef
  inputs, Oracle line-key indexing, shell invocation, exit-zero/drop and
  exit-nonzero/select, exception-selects behavior, context expansion, and an
  empty selected set.
- `CB-SIMPLIFY-001`: display-only identity, ordered calls, empty/multiline
  output, exception retaining original, and lifecycle counter aggregation.
- `CB-HISTORY-001`: number/zero/negative/non-number/empty/undef predictions,
  unknown items, multiple profiles, tool-specific profile keys, ordering and
  segmentation, serial/parallel output equivalence, and malformed history.
- `CB-LIFECYCLE-001`: constructor once, child `start`, child `save`, parent
  `restore`, late serial/parallel `finalize`, save-without-restore, each method
  throwing, multiple simultaneous children, and Storable failure.

### `perl2lcov` Cases

- `P2L-RUNTIME-001`: qualified runtime, missing Perl, missing
  `Devel::Cover::DB`, missing `Truth_Table`, help/version behavior, and module
  load channel/status.
- `P2L-DB-001`: raw database before `cover`, processed empty database, one and
  multiple databases, duplicate files/test names, and a database generated by
  every declared Devel::Cover version.
- `P2L-MODEL-001`: statements, package-qualified and global subroutines,
  anonymous/BEGIN exclusion, plain branch, compound condition truth tables,
  unevaluated branches, missing statement data, ignored categories, and
  function end-line derivation.
- `P2L-SHARED-001`: default and explicit output, test name, checksum, include,
  exclude, substitute, omit/filter, version callback, comments, criteria,
  configuration precedence, ignored inconsistency, and empty-output behavior.
- `P2L-FS-001`: missing/unreadable source, relative/absolute/non-UTF-8 paths,
  source names with spaces and metacharacters, external `grep` failure, output
  permissions, and partial-write cleanup.
- `P2L-E2E-001`: run the pinned `tests/perl2lcov/perltest1.sh` behavior against
  Oracle and Ferricov, compare semantic tracefiles, then consume both with
  `lcov --summary` and `genhtml`.

## Licensing And Distribution

ADR 0001 sets Ferricov to `GPL-2.0-or-later`, matching the option in upstream
LCOV source headers. Any upstream callback-host or `perl2lcov` code reused or
adapted by Ferricov remains GPL-2.0-or-later with copyright and license notices
retained. The pinned LCOV `COPYING` file contains GPL version 2.

Distributed adapted artifacts include or provide complete corresponding source,
GPL text, retained notices, and dependency license metadata.

The Oracle's Debian Devel::Cover 1.38 package metadata declares
`Artistic or GPL-1+`. Ferricov will initially depend on a user or distribution
provided Devel::Cover rather than vendor it. Packaging Devel::Cover later
requires retaining its own notices and a separate dependency-license review.

Callbacks are user-supplied programs with arbitrary side effects. This ADR does
not make a blanket legal determination about whether loading a particular user
module creates a derivative work; distributors and callback authors remain
responsible for their code and dependency licenses. Ferricov documentation
must not imply that callback execution is isolated.

## Consequences

- The common Rust binaries remain independent of Perl in callback-free and
  executable-callback workflows.
- Full compatibility includes an optional but first-class Perl runtime lane,
  not a silent fallback.
- A separate callback host would add a high-risk cross-process model boundary,
  especially for `unreachable`. State and wire contracts plus Oracle baselines
  must precede implementation; differential correctness evidence must precede
  compatibility and performance claims.
- External callback shell behavior preserves compatibility and therefore also
  preserves trusted-command injection risk.
- If the separate host is accepted, Perl callback performance will include host
  startup and serialization costs. The host would need to be persistent, and
  callback benchmarks remain subject to the performance contract after parity.
- Exact diagnostics can vary with Perl and Devel::Cover versions; release
  claims are tied to a published runtime matrix.

## Unresolved Risks And Required Follow-Up

1. **Interpreter state surface:** custom modules may inspect undocumented array
   slots, class names, `main::` and package globals, `%INC`, or any
   `lcovutil.pm` method. The per-tool readable/writable state contract must
   determine whether a separate host can reproduce that access. Shipped modules
   are necessary but not sufficient fixtures.
2. **Fork equivalence:** the lifecycle contract must preserve PIDs, signal
   behavior, output order, inherited state, and `start/save/restore/finalize`
   transfer without forking the multithreaded Rust process.
3. **Mutation atomicity:** upstream may retain partial module mutations before
   a callback exception. The writeback contract must not impose transactional
   behavior until reverse cases establish the Oracle result.
4. **Byte fidelity:** JSON is unsuitable as the only bridge representation for
   non-UTF-8 paths/text and arbitrary `save()` scalars. The wire contract and
   size limits remain to be specified before implementation.
5. **Host failure boundary:** the protocol contract must define truncated
   messages, signal death, partial mutation, writeback order, and when restart
   is observably unsafe.
6. **Runtime discovery and architecture selection:** the launcher contract
   shared by `.pm` callbacks and `perl2lcov` must select a qualified Perl runtime
   and choose the accepted host or pinned front-end path without adding an
   accidental public environment-variable surface.
7. **External shell behavior:** exact shell selection, quoting, signals, and
   wait-status conversion for version compare and select need executable Oracle
   fixtures before external shell compatibility is claimed.
8. **Devel::Cover matrix:** only Debian's 1.38 database is currently qualified
   as an environment candidate; no cross-version database evidence exists.
9. **Performance and platform behavior:** whole-file object transfer for
   `unreachable` can dominate filtering time and memory, while Perl, fork,
   shell, path bytes, and process status differ on macOS and non-POSIX
   environments. Optimization cannot narrow the object protocol or alter
   callback timing, and this ADR makes no Windows claim.
10. **Auxiliary command reachability:** every converter that inherits shared
    option parsing still needs an inventory case proving which callbacks it
    actually configures and calls.

Items 1-5 block Perl-host implementation until their contracts are specified.
Item 6 blocks both proposed Perl-host implementation and the proposed
`perl2lcov` entry-point implementation until the launcher contract is specified.
Items 7-10 block the corresponding compatibility or performance claims. The
external runner remains an architecture proposal until its contract cases pass;
these blockers do not alter the accepted Perl-neutral core boundary.

## M0 Decision Boundary And Blockers

| Decision or case family | M0 state | Required source/evidence boundary |
| --- | --- | --- |
| `CORE-PERL-BOUNDARY-001` | `accepted_architecture` | `lib/lcovutil.pm:990-1068`, `bin/perl2lcov:42-50`; core crates remain Perl-neutral and optional runtime lanes stay outside them |
| Native external runner (`CB-ARGS-001`, `CB-IO-001`, `CB-FAIL-001`, and applicable surface cases) | `blocked_proposal` | Exact argv/shell, stream, status, cache, and caller-specific differential evidence |
| Separate `.pm` host (`CB-GLOBAL-001`, `CB-LIFECYCLE-001`, `CB-HOST-001`) | `blocked_proposal` | Same-interpreter state, lifecycle identity, byte framing, mutation, failure, and restart contracts |
| Pinned same-interpreter front end | `proposed_alternative` | Required when a separate host cannot reproduce the qualified state contract; no behavior claim exists yet |
| `perl2lcov` launcher/adapter (`P2L-*`) | `blocked_proposal` | Runtime discovery plus complete conversion, diagnostic, filesystem, and exit differential matrix |
| Perl 5.36.0 / Devel::Cover 1.38 | `candidate_only` | Content-addressed runtime manifest and passing matrix; local package presence is not qualification |

M0 may accept or reject the proposed directions only after the listed Oracle
cases have executable definitions and retained evidence. M1 may implement only
the Perl-neutral model/tracefile core authorized by the accepted boundary. M2
through M5 must not infer callback, Perl, or `perl2lcov` implementation approval
from this ADR.

## Audit Evidence

### Pinned Sources

- `docs/man/genhtml.rst:189`: script/module conventions, public module methods,
  callback arguments, and parallel lifecycle.
- `docs/man/genhtml.rst:638`: annotate, criteria, version, resolve, select,
  simplify, and unreachable user documentation.
- `docs/man/genhtml.rst:1546`: profile and history options.
- `docs/man/lcovrc.rst:1568`: callback configuration, selection JSON, resolve,
  and module-only unreachable behavior.
- `docs/man/lcov.rst:467` and `docs/man/geninfo.rst:317`: history and shared
  callback reachability.
- `lib/lcovutil.pm:990`: callback selection, module loading, construction, and
  lifecycle registration.
- `lib/lcovutil.pm:2127`: child state initialization and callback state
  transfer.
- `lib/lcovutil.pm:2828`: version extraction/comparison and source existence.
- `lib/lcovutil.pm:3247` and `lib/lcovutil.pm:3254-3265`: external callback
  argv, shell, stdout, status, data parsing, and the legacy `PipeHelper`
  argument rewrite.
- `lib/lcovutil.pm:3730`: resolution cache and fallback.
- `lib/lcovutil.pm:8208`: actual unreachable argument order and mutation call.
- `bin/genhtml:2158` and `bin/genhtml:4501`: select callback object and JSON
  representations.
- `bin/genhtml:5714`: annotation validation, failure, fallback, and synthesis.
- `scripts/context.pm`, `criteria.pm`, `history.pm`, `select.pm`,
  `simplify.pm`, `unreach.pm`, `gitversion.pm`, `P4version.pm`,
  `gitblame.pm`, and `p4annotate.pm`: shipped module behavior, including direct
  reads and writes of LCOV tool and package globals.
- `bin/perl2lcov:1`: runtime imports, DB traversal, conversion, shared options,
  output, and exit behavior.
- `tests/perl2lcov/perltest1.sh`, `tests/genhtml/errs/msgtest.sh`,
  `tests/genhtml/simple/script.sh`, and `tests/lcov/extract/extract.sh`:
  existing upstream behavioral cases and gaps.
- `Makefile:35`: interpreter/install paths, ten installed commands, installed
  `lcovutil.pm`, and all support scripts.
- `COPYING` and per-file headers: upstream license terms.

### Audit Commands

The audit used the following commands against the local immutable reference:

```bash
git -C /home/cc/code1/lcov-upstream-reference rev-parse HEAD
git -C /home/cc/code1/lcov-upstream-reference describe --tags --always --dirty
git -C /home/cc/code1/lcov-upstream-reference log -1 --format=fuller v2.5
find /home/cc/code1/lcov-upstream-reference -type f \
  -not -path '*/.git/*' -exec wc -l {} + | sort -nr | head -n 60
rg -n '^package |^sub (new|annotate|context|check_criteria|history|resolve|select|simplify|exclude|extract_version|compare_version|start|save|restore|finalize)' \
  lib/lcovutil.pm bin/genhtml bin/geninfo bin/lcov scripts/*.pm
rg -n '(ScriptCaller->new|configure_callback|callback_save_restore|callback_start_list|callback_finalize|resolveCallback)' \
  lib/lcovutil.pm bin/genhtml bin/geninfo bin/lcov
rg -n --glob '*.sh' --glob Makefile \
  '(annotate-script|criteria-script|version-script|resolve-script|select-script|context-script|simplify-script|history-script|unreachable-script|LCOV_FORCE_PARALLEL)' \
  tests example
git -C /home/cc/code1/lcov-upstream-reference show v2.5:bin/perl2lcov | sha256sum
git -C /home/cc/code1/lcov-upstream-reference show v2.5:lib/lcovutil.pm | sha256sum
docker image inspect ferricov/lcov-oracle:v2.5 --format '{{.Id}}'
docker run --rm --network none --entrypoint sh ferricov/lcov-oracle:v2.5 -c \
  'perl -e '\''print "$^V\n"'\''; \
   perl -MDevel::Cover -e '\''print "$Devel::Cover::VERSION\n"'\''; \
   dpkg-query -W -f='\''${Package} ${Version}\n'\'' perl libdevel-cover-perl'
docker run --rm --network none --entrypoint sh ferricov/lcov-oracle:v2.5 -c \
  "sed -n '1,180p' /usr/share/doc/libdevel-cover-perl/copyright"
```

Observed identities:

- upstream commit: `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- upstream describe: `v2.5`
- Oracle image ID:
  `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
- `bin/perl2lcov` SHA-256:
  `e04a94a77a6d3da06a84b3ec18ef71883fe125db73dd7af8dd209dced28699b9`
- `lib/lcovutil.pm` SHA-256:
  `d3d975aa796af854ed5ca8a073d855642f7c1d370dd41c2e6e26d3fd4c5057b1`
- Oracle Perl: `5.36.0`
- Oracle Devel::Cover: `1.38` (`libdevel-cover-perl 1.38-1+b1`)

### Large-File Read Boundary

The audit identified four upstream source files over 2,000 lines:

- `bin/genhtml`: 14,234 lines
- `lib/lcovutil.pm`: 10,184 lines
- `bin/geninfo`: 4,152 lines
- `bin/lcov`: 2,042 lines

They were not read in full. The audit used symbol searches and narrow numbered
line windows around callback construction, call sites, lifecycle, process I/O,
error handling, and serialization. No other file over 2,000 lines was needed
for this decision; large generated XML and coverage-data fixtures were also not
read in full.
