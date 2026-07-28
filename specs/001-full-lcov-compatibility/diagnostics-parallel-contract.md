# Diagnostics And Parallel Execution Contract

## Status And Authority

This is a proposed normative M0-M5 contract and a reviewed M0 decision draft.
It freezes case identities and evidence requirements, but no diagnostic,
environment, callback-lifecycle, or parallel behavior is qualified until the
applicable Oracle and Ferricov evidence passes. M1 remains blocked by the
project go/no-go gate.

## 1. Purpose

This document freezes the observable diagnostic and parallel-execution
contract for LCOV `v2.5` at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.

It defines:

- named error and warning classes;
- raw and parser-owned diagnostic surfaces;
- severity, ignore, keep-going, warning-promotion, and message-count rules;
- stdout, stderr, message-log, and exit-status boundaries;
- command-specific startup failures;
- child status, signal, retry, memory, ordering, and state-transfer behavior;
- stable compatibility case identifiers; and
- milestone ownership and acceptance gates.

This contract does not claim Ferricov compatibility. Every case remains
planned until raw Oracle evidence and a Ferricov result satisfy its acceptance
rule. The only approved non-identical result is
`DEV-GENINFO-CHILD-001`, defined in
[`ADR 0004`](../../docs/adr/0004-upstream-defect-safety-policy.md).

## 2. Scope And Inventory Links

The shared Perl diagnostic policy applies to these commands:

- `lcov`
- `genhtml`
- `geninfo`
- `perl2lcov`
- `llvm2lcov`

Their primary control IDs are:

- `command.<tool>.option.ignore-errors`
- `command.<tool>.option.keep-going`
- `command.<tool>.option.expect-message-count`
- `command.<tool>.option.msg-log`
- `command.<tool>.option.quiet`
- `command.<tool>.option.verbose`
- `command.<tool>.option.debug`
- `command.<tool>.option.parallel`
- `command.<tool>.option.memory`
- `command.<tool>.option.fail-under-lines`
- `command.<tool>.option.fail-under-branches`

The corresponding reviewed or pending configuration IDs are:

- `lcovrc.ignore-errors`
- `lcovrc.max-message-count`
- `lcovrc.stop-on-error`
- `lcovrc.treat-warning-as-error`
- `lcovrc.warn-once-per-file`
- `lcovrc.parallel`
- `lcovrc.memory`
- `lcovrc.memory-percentage`
- `lcovrc.max-fork-fails`
- `lcovrc.fork-fail-timeout`
- `lcovrc.max-tasks-per-core`
- `lcovrc.fail-under-lines`
- `lcovrc.fail-under-branches`

The executable configuration key is `expected_message_count` at
`lib/lcovutil.pm:1144`; reviewed inventory ID
`lcovrc.expected-message-count` now exists. The manual instead documents
`expect_message_count` at `docs/man/lcovrc.rst:609`. Their failure contracts
are path-qualified: an unknown key in a config file is silently skipped at
`lib/lcovutil.pm:1404-1406`, while the same unknown key supplied through
`--rc` becomes a deferred `usage` error at `lib/lcovutil.pm:1483-1489` and
`1656-1662`. M0 must freeze all three spellings/paths rather than claiming one
universal rejection.

`py2lcov` and `xml2lcov` have native Python control IDs
`command.py2lcov.option.keep-going` and
`command.xml2lcov.option.keep-going`. They do not use the shared 32-class
registry.

`command.perl2lcov.option.ignore-error` and
`command.llvm2lcov.option.ignore-error` are documentation candidates, not
independent parser definitions. Under the default pinned launcher profile, the
singular spelling resolves as a unique Getopt prefix of `--ignore-errors` for
every shared front end. With `POSIXLY_CORRECT=1`, Getopt auto-abbreviation is
disabled and the same token is rejected as an unknown option with status `1`.
M0 must record both launcher profiles as parser-resolution observations rather
than treating the spelling as a canonical converter-only alias. The parser
definition is `ignore-errors=s` at `lib/lcovutil.pm:1270`; early parsing sets
`no_auto_abbrev` and later restores the Getopt default at
`lib/lcovutil.pm:1433-1444,1511-1524`. The Oracle manifest MUST pin Perl and
Getopt::Long identity (currently Getopt::Long 2.52), not only the LCOV SHA.

### 2.1 Configuration Discovery And Environment Contract

The reviewed M0 audit artifacts are
`/tmp/ferricov-upstream-test-env-audit.json` with SHA-256
`af941f951f7ca95540f1862c6935aaeb0b5cc77cfc404f181cc80d104acfa29c`
and `/tmp/lcov-make-install-env-audit.json` with SHA-256
`4d427a709b08c8db191a255d6b1a9e911d2b084f28e66adad3e81946d2ac9d4d`.
They are ephemeral read-only provenance inputs, not contract authorities or
retained release evidence. The reviewed facts needed by this contract are
embedded below. M0 MUST reproduce them as executable cases and retain a
content-addressed evidence manifest; disappearance of either `/tmp` file cannot
change the contract.

Configuration discovery and include processing at
`lib/lcovutil.pm:1335-1460` follows this observable order:

1. One or more explicit `--config-file` values disable automatic discovery;
   every explicit file is read in CLI order.
2. Otherwise the first readable `$HOME/.lcovrc` wins.
3. Only when that file is not selected does
   `$LCOV_HOME/etc/lcovrc` become a candidate.
4. The compiled installation prefix alone does not select the installed
   `etc/lcovrc`.
5. A `config_file = ...` statement is processed inline. A relative include is
   resolved from process CWD, and include loops are `usage`.
6. An unreadable explicit/include file and an include loop fail before CLI
   ignore parsing and cannot be rescued by that invocation's
   `--ignore-errors`. Malformed statements and missing environment references
   are deferred until after ignore parsing.
7. Unknown keys in files are silent; unknown `--rc` keys are deferred
   `usage` errors.

Every RC value also exposes a dynamic public environment namespace through
`$ENV{<arbitrary-name>}` expansion at `lib/lcovutil.pm:1377-1390`.
Present values are substituted textually before key validation. If any named
variable is absent, LCOV records a deferred `usage` error and ignores that
configuration statement. The fixture name `ENV_IGNORE` is only one example;
it MUST NOT be mistaken for the fixed public variable.

Environment roles MUST remain distinct:

- LCOV-code-read public names: `HOME`, `LCOV_HOME`, `COVERAGE_FILE`,
  `COVERAGE_COMMAND`, `PWD`, `SOURCE_DATE_EPOCH`, `LCOV_SHOW_LOCATION`,
  `LCOV_VALIDATE`, `PERL5LIB`, `LOG_P4ANNOTATE`, `P4USER`, `P4PORT`,
  `P4CLIENT`, `USER`, `HOSTNAME`, and `MACHTYPE`;
- implicit parser profile: `POSIXLY_CORRECT`;
- dynamic public namespace: arbitrary `RC:$ENV{*}`;
- ambient launcher/process inputs recorded but not promoted to LCOV-specific
  options: `PATH`, `PERL5OPT`, Python path controls, `LANG`/`LC_*`, `TZ`,
  `TMPDIR`, CWD, umask, stdin, and descriptors;
- internal/test forcing: `LCOV_FORCE_PARALLEL` and test-only variables; and
- build/install roles, classified by use site rather than globally. In
  particular, `SOURCE_DATE_EPOCH` has both runtime-genhtml and build/fix uses.

The primary anchors are `lib/lcovutil.pm:639-644,901-902,1377-1460`,
`bin/genhtml:5682-5687,7217-7273`, `bin/py2lcov:118-120,150,163-188`,
`scripts/context.pm:79-80`, and `scripts/p4annotate.pm:76-97,153`.
The implicit Getopt input `POSIXLY_CORRECT` remains on a manual allowlist
because direct `ENV` scans cannot discover it. `LCOV_FORCE_PARALLEL` is a
separately classified internal regression/runtime forcing knob at
`lib/lcovutil.pm:1013,8616-8688,9889` and `bin/geninfo:1321`; its presence is
still recorded in parallel manifests but does not become a supported public
configuration interface.

Build/install variables such as `DESTDIR`, `PREFIX`, `BUILD_DATE`,
`SPHINXBUILD`, and `SOURCE_DATE_EPOCH` in `bin/fix.pl`, test-only variables
such as `TESTCASE_ARGS`, and internal derived Make variables MUST remain
separately classified. A test injection does not promote a name into the
installed-command environment contract.

All Oracle probes outside an environment-specific case MUST run under a
declared clean environment with a fixture-owned `HOME`, no inherited
`LCOV_HOME`, and explicit locale/timezone. This prevents accidental host RC
discovery. Environment cases MUST cover unset, empty, `0`, nominal, malformed,
and CLI/config precedence where the consumer distinguishes them.

The following M0 gaps remain blocked: no upstream test sets `LCOV_VALIDATE`;
`POSIXLY_CORRECT` has no direct upstream fixture; `LCOV_SHOW_LOCATION` lacks
empty, `0`, and greater-than-one coverage; and broad harness use of
`LCOV_HOME` can conceal discovery bugs.

## 3. Named Message Registry

`lib/lcovutil.pm:169-200` defines 32 case-insensitive message names. Numeric
IDs are assigned in array order at runtime by `define_errors()` at
`lib/lcovutil.pm:1889-1903`. Ferricov must use stable semantic names in its own
model; upstream numeric IDs are evidence details, not a public storage format.

| Name | Upstream role and primary emitters | Primary source references |
| --- | --- | --- |
| `annotate` | `genhtml` annotation process failure | `bin/genhtml:5820,7967` |
| `branch` | Reserved class with no production emitter at the pinned commit | `lib/lcovutil.pm:143,170` |
| `callback` | Callback load, method, lifecycle, or protocol failure | `lib/lcovutil.pm:1055,1920,2162,2199,2236,2863,3150,3272`; `bin/genhtml:1275,5775` |
| `category` | Unknown report or converter category | `bin/genhtml:5093,5388,5427,5455,5529,5585,5647`; `bin/perl2lcov:232` |
| `child` | Child exit, unknown child, or failed child result | `lib/lcovutil.pm:2421-2430`; `bin/genhtml:7027`; `bin/geninfo:1238` |
| `corrupt` | Unreadable or unserializable coverage input | `bin/geninfo:3290,3321`; `lib/lcovutil.pm:9787` |
| `count` | Message-count constraint or suppression-limit diagnostic | `lib/lcovutil.pm:1926,2309` |
| `deprecated` | Deprecated configuration or behavior | `lib/lcovutil.pm:1289-1296,1656-1662` |
| `empty` | No data, empty trace, or empty coverage surface | `bin/lcov:650`; `bin/genhtml:4391`; `bin/geninfo:494,565,1654,1735,3174`; `bin/perl2lcov:179`; `lib/lcovutil.pm:9710,9727,9743,9769` |
| `excessive` | Suspiciously large coverage count | `lib/lcovutil.pm:3950,4137,4995` |
| `format` | Malformed record, numeric value, or external format | `bin/genhtml:4182`; `bin/geninfo:437,1296,2292,3773,3932`; `bin/llvm2lcov:460`; `lib/lcovutil.pm:3937,4127,4626` |
| `fork` | `fork()` syscall failure and retry | `lib/lcovutil.pm:2433-2454` |
| `gcov` | gcov input, execution, or capture failure | `bin/geninfo:487,2127,2847-3026,2985` |
| `graph` | gcov graph-data failure | `bin/geninfo:3264` |
| `inconsistent` | Semantically inconsistent coverage records | `bin/genhtml:2265,2752,2807,5705`; `bin/geninfo:2343,2654`; `bin/perl2lcov:259`; `lib/lcovutil.pm:4619,4962,5030,5186,5210,5333` |
| `internal` | Invariant violation inside LCOV bookkeeping | `lib/lcovutil.pm:839,858,866,2247,2254`; `bin/genhtml:1084,4192` |
| `mismatch` | Incompatible source, checksum, function, or merge identity | `bin/genhtml:4039-4059`; `bin/geninfo:1769`; `lib/lcovutil.pm:4251,4263,4283,4730,5307,6295` |
| `missing` | Pattern result or file is not readable | `lib/lcovutil.pm:9734-9738` |
| `negative` | Unexpected negative coverage count | `lib/lcovutil.pm:3942,4132,4991` |
| `package` | Missing runtime package or invalid module lifecycle | `lib/lcovutil.pm:702,723,758,1024,1036,2929` |
| `parallel` | Scheduler, serialization, join, or parallel runtime failure | `lib/lcovutil.pm:2437,2479-2492,8397,8459,10004,10055`; `bin/genhtml:6669,6928,7008`; `bin/geninfo:1160,1220,1536` |
| `parent` | Child detects that its parent died | `lib/lcovutil.pm:2514-2528` |
| `path` | Source, build, or gcov path failure | `bin/genhtml:7875`; `bin/geninfo:866,2866,2875`; `lib/lcovutil.pm:3097,3112,3699` |
| `range` | Source or diff line lies outside its valid range | `bin/genhtml:5910`; `lib/lcovutil.pm:6740,6759,6807-6808` |
| `source` | Source file cannot be found, read, or resolved | `bin/genhtml:5721-5733,5898`; `bin/perl2lcov:245`; `lib/lcovutil.pm:2839,6464` |
| `unmapped` | Differential coverage line cannot be mapped | `bin/genhtml:4841,4963,5119,5472,5497,5506,5549,5559,5607,5616` |
| `unreachable` | Invalid or inconsistent unreachable-coverpoint state | `lib/lcovutil.pm:7558,8145,8258` |
| `unsupported` | Recognized feature is unsupported in this mode or toolchain | `bin/geninfo:368`; `bin/perl2lcov:239`; `lib/lcovutil.pm:8485,8490` |
| `unused` | Include, exclude, source, build, or callback pattern had no effect | `lib/lcovutil.pm:1794-1811,3121,3765-3774` |
| `usage` | Invalid option combination or configuration value after parsing | `bin/lcov:264,270,291,338,604,634`; `bin/genhtml:460,7375,7380`; `bin/geninfo:282,408,418,518,524`; `lib/lcovutil.pm:1343,1357,1385,1642,1990-2027` |
| `utility` | Required external utility failed | `bin/geninfo:950,1740`; `lib/lcovutil.pm:9723` |
| `version` | Source or coverage version mismatch | `bin/genhtml:5750,5756`; `bin/geninfo:2802`; `lib/lcovutil.pm:2900,9122,9129,9145` |

`branch` must be represented as `reserved_no_emitter`. Its name is accepted by
`--ignore-errors`, but no pinned production call site emits it. A compatibility
case must test acceptance of the name without inventing a synthetic branch
diagnostic.

## 4. Raw And Unclassified Surfaces

The 32-class registry is not the complete error surface. Ferricov must model
the following families separately:

### 4.1 Parser Errors

- Shared Getopt front ends generally write parser diagnostics to stderr and
  exit `1` for an unknown option.
- Python argparse writes usage plus the parser error to stderr and exits `2`.
- `xml2lcovutil.py` has no command parser or main entry point. Arbitrary
  arguments are ignored and the process exits `0` without output.

Parser errors do not gain a named registry class merely because their text
contains "warning" or "error".

### 4.2 Raw Perl Failures

Direct `die`, open, close, assertion, and module-load failures can bypass
`ignorable_error()`. They normally use the installed warning/die handlers when
those handlers have already been registered, but they have no named class and
are not controlled by `--ignore-errors`.

Examples include:

- `gendesc` missing input;
- `llvm2lcov` missing JSON input;
- invalid direct option combinations outside an ignorable call site; and
- deserialization or internal assertions that occur outside a named wrapper.

Raw Perl exit status depends on the command and catch boundary. Ferricov must
not assign one universal status to `die`.

### 4.3 Native Python Diagnostics

`py2lcov`, `xml2lcov`, and imported `xml2lcovutil.py` emit application errors
and warnings with direct `print()`, normally to stdout. Caught failures under
`--keep-going` can leave a partial output file and still exit `0`.

Uncaught `FileNotFoundError`, XML parse errors before a local `try`, assertion
failures, and command-not-found failures produce a Python traceback on stderr
and exit `1`. `--keep-going` does not apply outside the explicit catch blocks.

### 4.4 Early Dependency Failures

`genpng` imports shared code at `bin/genpng:39-42`, then probes/loads `GD.pm`
at `bin/genpng:57-65,158-161` before handlers and option parsing at
`bin/genpng:68-90`. A missing module writes exactly
`ERROR: required module GD.pm not found on this system (see www.cpan.org).
`
to stderr, leaves stdout empty, and exits `2`. `genpng` exposes no shared
ignore/keep-going options, and help, version, no-argument, and unknown-token
requests cannot bypass the dependency. Paired GD-present/missing images are
required because the current Oracle image contains GD 2.76.

These raw families require stable case IDs and exact per-emitter expectations.
They must not be silently coerced into the nearest named class.

## 5. Severity And Continuation State Machine

### 5.1 Ignore Parsing

`parse_ignore_errors()` at `lib/lcovutil.pm:1962-1981`:

1. splits every supplied string by the configured `split_char`;
2. matches names case-insensitively;
3. rejects an unknown name immediately; and
4. increments an integer ignore count for every occurrence.

Repeated names are semantic. They are not redundant input.

If the CLI supplies no `--ignore-errors`, configuration `ignore_errors` values
are used. The first CLI occurrence replaces the complete configuration list;
CLI and configuration lists are not merged.

### 5.2 Error Ladder

For `ignorable_error(class, message)`, the observable ladder is:

| State | Continuation | Console message | Summary bucket | Final status rule |
| --- | --- | --- | --- | --- |
| Ignore count `0`, normal stop policy | Stop through fatal handler | stderr `ERROR` with class and first-occurrence bypass hint | `error` | Command- and phase-specific fatal status |
| Ignore count `1` | Continue | stderr `WARNING` with suppression hint | `warning` | Success if no other failure or threshold applies |
| Ignore count `2+` | Continue | No console message | `ignore` | Success if no other failure or threshold applies |
| `stop_on_error=0` or `--keep-going`, no explicit ignore | Continue | stderr `ERROR` | `error` | `lcov`, `geninfo`, and `genhtml` force final `1` through `saw_error()` |

`--keep-going` sets `stop_on_error=0` at `lib/lcovutil.pm:1582-1583`.
`is_ignored()` therefore permits continuation for every named class, but an
unlisted class remains an `error` rather than a warning or silent ignore.

Raw failures outside `ignorable_error()` do not become continuable merely
because `--keep-going` is present.

### 5.3 Warning Ladder

For `ignorable_warning(class, message)`:

- without promotion and without ignore, emit stderr `WARNING` and count a
  warning;
- without promotion and with one or more ignores, suppress the console message
  and count an ignore; and
- with `treat_warning_as_error=1`, route through the complete error ladder, so
  counts `0`, `1`, and `2+` mean fatal error, warning, and silent ignore.

The promotion occurs at `lib/lcovutil.pm:2385-2390`.

### 5.4 Converter Compatibility Traps

`perl2lcov` and `llvm2lcov` use the shared continuation engine but do not call
`saw_error()` before exit. A keep-going run can therefore:

- emit `ERROR` messages;
- summarize them under the `error` bucket;
- write an empty or partial output artifact; and
- exit `0`.

This bounded behavior is a required compatibility trap. It must not be
normalized to exit `1` under ADR 0004.

The Python converters have their own trap: a caught conversion or structural
error under `--keep-going` can print `Error:` to stdout, retain a partial
`TN:` output, and exit `0`.

## 6. Message Counting And Suppression

`max_message_count` defaults to `100`. A positive value limits console output
per named class; `0` disables the limit.

The class counter increments before suppression. Therefore:

- warnings, errors, explicitly ignored messages, and over-limit messages all
  contribute to `expected_message_count`;
- the first over-limit event is moved to the `ignore` summary bucket;
- a single `count` warning reports that the class limit was reached when the
  original class ignore count is at most one; and
- duplicate ignores can suppress both the original message and its normal
  suppression guidance while the semantic count still changes.

Expected-count constraints are evaluated before the final message summary at
`lib/lcovutil.pm:1905-1929`. A false constraint emits class `count`; class
`count` itself follows the same ignore and keep-going ladder.

## 7. Streams, Logging, And Ordering

### 7.1 Serial Streams

| Output family | Default channel | Control |
| --- | --- | --- |
| Informational progress and summaries | stdout | quiet/verbose level through `info()` |
| Debug output | stderr | debug level |
| Named warnings and errors | stderr | severity, ignore, and keep-going policy |
| Parser diagnostics | parser-specific, normally stderr | parser policy |
| Python application errors and warnings | stdout unless traceback or argparse | native converter code |
| Message summary | stdout | hidden only by sufficiently negative verbosity or explicit silent summary call |

The common formatter is `_msg_handler()` at `lib/lcovutil.pm:635-663`. It
normalizes the tool, severity, and message prefix and removes Perl source
locations unless debug, verbosity, or `LCOV_SHOW_LOCATION` enables them.

### 7.2 Message Log

`--msg-log` and `message_log` copy formatted warning/error records to a file.
Each write uses `flock`, so individual records are not byte-interleaved. The
lock does not establish a global semantic order between processes.

The log does not receive:

- informational stdout;
- message summaries;
- messages suppressed by duplicate ignore or message-count limits; or
- raw failures that bypass `_msg_handler()`.

### 7.3 Parallel Replay

Workers capture stdout and stderr separately. The parent replays complete
worker chunks in reap/completion order, not input order. Within one replayed
chunk, stdout is printed before stderr even if the worker originally
interleaved them. Cross-worker order and message-log order are not deterministic
unless a focused call site supplies stronger ordering.

Normalizers may replace PID, temporary path, timestamp, and explicitly
nondeterministic worker order. They must not discard:

- message class;
- severity;
- multiplicity when the case asserts it;
- child exit or signal meaning;
- final exit status; or
- artifact presence and content.

## 8. Exit Status Boundaries

There is no universal fatal status by class. Exit status is the tuple:

```text
command + parser/emitter + execution phase + catch boundary + fixture
```

The network-disabled pinned Oracle no-argument baseline is:

| Command | Status | stdout | stderr semantic oracle |
| --- | ---: | --- | --- |
| `lcov` | `2` | empty | Invalid command line, required operation list, usage hint |
| `genhtml` | `2` | empty | No files specified |
| `geninfo` | `255` | gcov version and intermediate-format progress | No directory specified plus usage hint |
| `genpng` | `1` | empty | Handler-formatted no-filename error |
| `gendesc` | `255` | empty | Handler-formatted no-input error plus usage hint |
| `perl2lcov` | `2` | empty | Named `empty` error for missing coverpoints |
| `py2lcov` | `1` | `Error:  no input files` | empty |
| `xml2lcov` | `1` | `Error:  no input files` | empty |
| `xml2lcovutil.py` | `0` | empty | empty |
| `llvm2lcov` | `2` | empty | Raw JSON-file-required Perl failure |

These are exact behavioral cases, not a proposed normalized interface.

`lcov`, `geninfo`, and `genhtml` use top-level eval boundaries for selected
business phases and later force exit `1` after a continued named error through
`saw_error()`. Errors before, after, or outside those boundaries may retain
other statuses.

Coverage thresholds are separate from named error policy. A line or branch
threshold can produce a non-zero result after an otherwise successful output
artifact. Threshold cases must assert both the exit status and retained output.

## 9. Parallel Runtime Contract

### 9.1 Worker Ownership

The parent owns the active worker set. A PID enters the set once after a
successful spawn and leaves exactly once after reap, regardless of:

- worker exit status;
- signal;
- missing or corrupt serialized data;
- callback failure;
- explicit ignore policy; or
- keep-going policy.

Business-result merge and process ownership are separate state transitions.
Ferricov must never keep a reaped PID active because its result was rejected.

### 9.2 Child Exit And Signal

`report_exit_status()` at `lib/lcovutil.pm:2457-2477` interprets raw wait
status. Ordinary child exit and signal death are different result fields.
Signal diagnostics include the signal number/name and an out-of-memory hint;
they must not be inferred by shifting a status twice.

Default fatal child handling may terminate remaining siblings. Keep-going or
an ignored child class may permit sibling drain, but it must not merge a failed
chunk as success or lose the final failure intent.

`lcov --capture` delegates to `geninfo`; its wrapper status, signal, stdout,
stderr, and generated artifact require their own cases rather than inheriting
non-capture `lcov` expectations.

### 9.3 Retry Budget

Fork and resource retries require:

- one owner for the retry counter;
- a finite configured maximum;
- a state transition on every attempt;
- a finite delay policy;
- cancellation when the parent operation stops; and
- a terminal diagnostic when the budget is exhausted.

`max_fork_fails=0` and other edge values must have explicit Oracle cases. A
missing or corrupt worker payload is not automatically equivalent to a failed
`fork()` and cannot silently receive an unlimited fork retry budget.

Potential `genhtml` retry defects identified in M0 are not approved deviations.
They remain blocked pending focused reproducible evidence and a later ADR if
they prove unbounded.

### 9.4 Memory Admission

The pinned schedulers combine `--parallel`, `--memory`,
`memory_percentage`, `/proc`, and optional `Memory::Process` behavior. The
execution manifest must record whether `Memory::Process` is installed and
whether `/proc` is available.

Current upstream code can admit two workers before the memory wait predicate
applies. This bounded oddity remains an Oracle requirement unless a later
resource-safety ADR accepts a deviation.

Memory cases must assert worker concurrency and admission order, not merely
that the option parses.

### 9.5 Child State Serialization

Parallel workers transfer coverage results, message state, callback state, and
profile information through temporary serialized data. Cases must distinguish:

- successful payload;
- missing payload;
- truncated or corrupt payload;
- payload with unexpected shape;
- worker success with unreadable logs;
- worker failure with a stale payload; and
- callback `start`, `save`, `restore`, and `finalize` failures.

No partially decoded result may be committed after a terminal payload error.
Successful sibling data may only be retained when the call site's keep-going
contract explicitly permits partial completion and the artifact semantics are
defined.

Lifecycle source/call-site binding is:

- registration and missing save/restore pairing:
  `lib/lcovutil.pm:1013-1032`, category `package`;
- child `start`: `lib/lcovutil.pm:2158-2164`, called at
  `bin/genhtml:6585`, `bin/geninfo:1458`,
  `lib/lcovutil.pm:8513,9962`;
- child `save`: `lib/lcovutil.pm:2191-2201`, called at
  `bin/genhtml:6656`, `bin/geninfo:1531`,
  `lib/lcovutil.pm:8593,9999`; enclosing serialization may later surface
  `parallel` at `bin/genhtml:6669`, `bin/geninfo:1536`, and
  `lib/lcovutil.pm:8598,10004`;
- parent `restore`: `lib/lcovutil.pm:2231-2238`, called at
  `bin/genhtml:6962`, `bin/geninfo:1192`,
  `lib/lcovutil.pm:8414,10078`;
- late parent `finalize`: `lib/lcovutil.pm:1822-1828`, reached from
  `bin/lcov:453`, `bin/genhtml:7606`, `bin/geninfo:577`, and
  `bin/perl2lcov:440`; and
- cleanup/destructor: `lib/lcovutil.pm:1049-1067`, reached by
  lcov/genhtml/geninfo/llvm2lcov but not the same perl2lcov cleanup path.

An ignored `save()` exception appends no placeholder before positional
restore. `CB-LIFE-SAVE-INDEX-001` MUST first freeze whether a later callback
value shifts onto an earlier callback. Ferricov must preserve any bounded
qualified Oracle trap. Atomic rejection or identity framing that changes the
continued result requires a separate accepted safety-deviation ADR; it is not
authorized by `DEV-GENINFO-CHILD-001`.

### 9.6 Accepted Safety Deviation

`DEV-GENINFO-CHILD-001` overrides byte-identical behavior only for the
documented exhausted-child infinite loop. Ferricov removes the reaped worker,
preserves the `child` diagnostic, drains bounded remaining work, emits no
unknown PID `-1` loop, reaches the ordinary final `empty` failure for the
all-failing fixture, and exits `1`. Separate expected-result pairs freeze the
keep-going, one-ignore, and two-ignore console and message-count semantics.

ADR acceptance selects this behavior but its qualification state remains
blocked. None of these cases may become `pass`, close M4, or support a release
claim until raw evidence is recaptured under a retained content-addressed
Oracle artifact or reproducible image manifest.

No other parallel path inherits this exception.

## 10. Stable Interaction Groups

The canonical interaction groups are:

| ID | Scope |
| --- | --- |
| `diagnostics.severity-ignore` | Fatal, warning, silent-ignore, and warning-promotion transitions |
| `diagnostics.keep-going-artifact` | Continued errors, completed or partial artifact, and final status |
| `diagnostics.message-accounting` | Expected counts, suppression thresholds, summary buckets, and message log |
| `diagnostics.config-precedence` | CLI versus config list replacement, invalid keys, and discovery order |
| `diagnostics.threshold-output` | Line/branch threshold status with retained output |
| `diagnostics.raw-failure` | Parser, raw Perl, dependency, native Python, and traceback boundaries |
| `converter.keep-going` | Perl, LLVM, Python, and XML converter-specific continuation traps |
| `parallel.serial-parity` | Explicit serial versus forced parallel model, artifacts, messages, and status |
| `parallel.worker-failure-propagation` | Non-zero child, sibling handling, failed chunk, and final status |
| `parallel.signal-and-status` | Raw wait status, signal identity, wrapper propagation, and OOM hints |
| `parallel.retry-and-resource-failure` | Fork, missing dump, corrupt dump, retry budget, and terminal failure |
| `parallel.message-ordering` | Worker replay, multiplicity, streams, and message-log ordering |
| `parallel.memory-throttle` | Parallel count, memory gates, `/proc`, and `Memory::Process` |
| `parallel.child-state-serialization` | Payload identity, callback lifecycle state, and atomic merge |

Inventory entries for the applicable options and config keys must reference
these IDs before M0 closes.

## 11. Stable Case Catalog

### 11.1 Registry And Severity

| Case ID | Required Oracle |
| --- | --- |
| `DIAG-REGISTRY-001` | Exactly 32 case-insensitive names in pinned order; `branch` accepted but has no emitter |
| `DIAG-IGNORE-ERROR-001` | Ignore count zero: named fatal error, stderr, bypass hint, command-specific status |
| `DIAG-IGNORE-WARN-001` | Ignore count one: continued warning and warning summary |
| `DIAG-IGNORE-SILENT-001` | Ignore count two: no console message and one ignore summary count |
| `DIAG-IGNORE-PRECEDENCE-001` | CLI ignore list replaces rather than merges config list |
| `DIAG-IGNORE-UNKNOWN-001` | Unknown class fails during shared option initialization with exact command-specific status |
| `DIAG-KEEP-GOING-001` | Unlisted named error continues as ERROR; `lcov` completes applicable work and exits `1` |
| `DIAG-WARNING-PROMOTE-001` | Warning-as-error follows fatal, warning, silent ladder for counts zero, one, and two |
| `DIAG-MAX-MESSAGES-001` | Limit suppresses later messages, emits `count` warning once, preserves semantic count |
| `DIAG-EXPECTED-COUNT-FILE-001` | File key `expected_message_count` evaluates the constraint; false constraint freezes semantic count, stream, artifact, and command-specific status |
| `DIAG-EXPECTED-COUNT-MANUAL-FILE-001` | Manual spelling `expect_message_count` in a file is an unknown key and is silently ignored |
| `DIAG-EXPECTED-COUNT-MANUAL-RC-001` | Manual spelling through `--rc` is a deferred `usage` error; exact ignore/keep-going and final-status path |
| `DIAG-MESSAGE-LOG-001` | Log contains formatted unsuppressed warnings/errors and excludes summary/info/silent ignores |

### 11.2 Configuration And Environment

| Case ID | Required Oracle |
| --- | --- |
| `DIAG-CONFIG-DISCOVERY-001` | No explicit file; HOME first-readable, LCOV_HOME fallback, neither file, unreadable automatic candidate, and compiled-prefix non-discovery |
| `DIAG-CONFIG-EXPLICIT-001` | One and repeated explicit files, CLI order, automatic-discovery bypass, duplicate assignments, and explicit unreadable file |
| `DIAG-CONFIG-INCLUDE-001` | Inline absolute/relative include, CWD resolution, nested order, duplicate include, and include-loop early `usage` |
| `DIAG-CONFIG-UNKNOWN-KEY-001` | Unknown file key is silent; unknown `--rc` key is deferred `usage`; executable/manual expected-message spellings bind to their three cases |
| `DIAG-CONFIG-ENV-EXPAND-001` | One and multiple arbitrary `$ENV{NAME}` references; present empty/`0`/text values; missing reference defers `usage` and ignores the complete statement before key validation |
| `DIAG-CONFIG-EARLY-ERROR-001` | Unreadable explicit/include file and include loop occur before CLI ignore parsing; malformed line and missing environment reference are deferred |
| `DIAG-ENV-CLEAN-001` | Parameterized benign invocation of every installed command under a minimal declared environment cannot inherit host RC, locale, timezone, Perl/Python paths, profile metadata, or support-script state |
| `DIAG-ENV-PRECEDENCE-001` | Per-consumer subcases for every public runtime variable with competing CLI/config control; unset, empty, `0`, nominal, malformed |
| `DIAG-ENV-ALLOWLIST-001` | M0 verifier over fixed code-read names, implicit parser input, dynamic `RC:$ENV{*}`, ambient launcher inputs, internal/test forcing, and build/install roles |
| `DIAG-ENV-LCOV-VALIDATE-001` | `genhtml` absent/present/empty/`0` environment value versus `--validate`, dead-link validation, streams, and status |
| `DIAG-ENV-SHOW-LOCATION-001` | `LCOV_SHOW_LOCATION` unset/empty/`0`/1/>1 and debug/verbose interactions, including stack-trace boundary |
| `DIAG-ENV-LCOV-HOME-001` | Isolated HOME/LCOV_HOME discovery without broad harness injection and exact selected file |
| `DIAG-ENV-POSIX-PROFILE-001` | Five shared front ends under default and POSIXLY_CORRECT profiles with pinned Perl/Getopt identity; binds singular-ignore parser case |

All rows are `blocked` until executable definitions retain the complete
environment, selected config path and bytes, expanded statement, diagnostic,
streams, status, output artifact, and Oracle identity.

### 11.3 Raw And Startup

| Case ID | Required Oracle |
| --- | --- |
| `DIAG-NOARGS-LCOV-001` | Status `2`, empty stdout, invalid-command stderr |
| `DIAG-NOARGS-GENHTML-001` | Status `2`, empty stdout, no-files stderr |
| `DIAG-NOARGS-GENINFO-001` | Status `255`, gcov progress stdout, missing-directory stderr |
| `DIAG-NOARGS-GENPNG-001` | Status `1`, empty stdout, missing-filename stderr |
| `DIAG-NOARGS-GENDESC-001` | Status `255`, empty stdout, missing-input stderr |
| `DIAG-NOARGS-PERL2LCOV-001` | Status `2`, named empty stderr |
| `DIAG-NOARGS-PY2LCOV-001` | Status `1`, stdout error, empty stderr |
| `DIAG-NOARGS-XML2LCOV-001` | Status `1`, stdout error, empty stderr |
| `DIAG-NOARGS-XML2LCOVUTIL-001` | Status `0`, empty streams, arbitrary argv ignored |
| `DIAG-NOARGS-LLVM2LCOV-001` | Status `2`, raw JSON-required stderr |
| `DIAG-PARSER-FAMILY-001` | Getopt, argparse, and no-parser unknown-token statuses and streams remain distinct |
| `DIAG-IGNORE-PREFIX-PROFILE-001` | `lcov`, `genhtml`, `geninfo`, `perl2lcov`, and `llvm2lcov` run `--ignore-error empty --version` under default and `POSIXLY_CORRECT=1`; default exits 0, POSIX exits 1, with handler-formatted versus raw stderr preserved and Perl/Getopt 2.52 pinned |
| `DIAG-RAW-PERL-001` | Parameterized per-emitter and catch-boundary matrix preserves exact uncaught Perl text, stream, status, and artifact state |
| `DIAG-PYTHON-TRACEBACK-001` | Failure outside native keep-going catch produces traceback stderr and status `1` |
| `DIAG-DEPENDENCY-GENPNG-001` | Paired GD 2.76-present and reproducibly dependency-masked images; missing GD exact stderr/status 2 precedes help/version/no-args/unknown tokens, while present GD reaches each later parser/startup path |
| `DIAG-CALLBACK-FINALIZE-FAIL-001` | Command-specific late `finalize` failure across lcov/genhtml/geninfo/perl2lcov call sites; category, ignore/keep-going, prior artifact/state, teardown, and exit |
| `DIAG-CALLBACK-CLEANUP-001` | Cleanup/destructor reachability and failure for lcov/genhtml/geninfo/llvm2lcov versus perl2lcov non-cleanup path |

### 11.4 Converter Traps

| Case ID | Required Oracle |
| --- | --- |
| `DIAG-PERL2LCOV-KEEP-001` | Continued named errors, error summary, output artifact, exit `0` |
| `DIAG-LLVM2LCOV-KEEP-001` | Continued named errors, error summary, output artifact, exit `0` |
| `DIAG-PY2LCOV-KEEP-001` | Caught child conversion error on stdout, partial `TN:` artifact, exit `0` |
| `DIAG-XML2LCOV-KEEP-001` | Caught structural XML error on stdout, partial `TN:` artifact, exit `0` |
| `DIAG-CONVERTER-KEEP-BOUNDARY-001` | Missing executable or pre-try XML parse bypasses keep-going and exits `1` |

### 11.5 Parallel Runtime

| Case ID | Required Oracle or approved pair |
| --- | --- |
| `PAR-SERIAL-PARITY-001` | Explicit `--parallel 1` and forced parallel preserve semantic coverage and defined artifact set |
| `PAR-CHILD-EXIT-001` | Non-zero child reports class, raw exit meaning, sibling policy, failed chunk, and final status |
| `PAR-GENINFO-CHILD-STOP-001` | Default stop remains byte-identical: first fatal status-7 child diagnostic, no output, exit `1`, no PID `-1` |
| `PAR-GENINFO-CHILD-EXIT-ORACLE-001` | Pinned keep-going case reaches watchdog `124` after child status `7` and PID `-1` loop |
| `PAR-GENINFO-CHILD-EXIT-FERRICOV-001` | Approved keep-going result: all three real child errors, final `empty`, no PID `-1`, no output, exit `1` |
| `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001` | Pinned one-ignore case reaches watchdog `124` after status-7 warnings and warning PID `-1` loop |
| `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001` | Approved one-ignore result: three child warnings, final unignored `empty`, no PID `-1`, no output, exit `1` |
| `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` | Pinned two-ignore case reaches watchdog `124` with console-silent child loop and no output |
| `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001` | Approved two-ignore result: child ignore count `3`, final unignored `empty`, no PID `-1`, no output, exit `1` |
| `PAR-CHILD-SIGNAL-001` | SIGTERM and SIGKILL remain signals, not shifted ordinary statuses |
| `PAR-LCOV-CAPTURE-STATUS-001` | `lcov --capture` preserves delegated ordinary exit and signal meaning |
| `PAR-FORK-RETRY-001` | Retry count, delay, recovery, and exhausted terminal failure are finite |
| `PAR-PAYLOAD-MISSING-001` | Missing serialized data follows documented retry/failure policy without stale merge |
| `PAR-PAYLOAD-CORRUPT-001` | Corrupt serialized data is rejected atomically with parallel failure |
| `PAR-UNKNOWN-CHILD-001` | Real unknown child is distinguished from exhausted `wait()` returning `-1` |
| `PAR-PARENT-DEATH-001` | Child detects dead parent and terminates without writing a successful payload |
| `PAR-MESSAGE-ORDER-001` | Completion-order normalization preserves per-message class, severity, stream, and count |
| `PAR-MSG-LOG-001` | Concurrent log records are individually complete; ordering is not overclaimed |
| `PAR-MEMORY-ADMISSION-001` | Worker concurrency under explicit memory limit matches pinned admission behavior |
| `PAR-MEMORY-FALLBACK-001` | `Memory::Process`, `/proc`, and unavailable-memory branches are manifest-qualified |
| `PAR-CALLBACK-STATE-001` | Child `start/save`, parent `restore`, and parent `finalize` retain identity and order |
| `PAR-CALLBACK-LIFECYCLE-FAIL-001` | Parallel projection of `CB-LIFE-START-FAIL-001`, `CB-LIFE-SAVE-FAIL-001`, `CB-LIFE-RESTORE-FAIL-001`, and `CB-LIFE-SAVE-INDEX-001`; parameterize command/call-site, serial/parallel/forced profile, stop/keep/ignore1/ignore2, and callback index; freeze transcript, payload index, sibling/business merge, partial state, artifact, and status |
| `PAR-PARTIAL-COMMIT-001` | Failed payload cannot partially mutate committed parent coverage state |

## 12. Oracle Probe Requirements

Every direct diagnostic or parallel Oracle probe must:

- run the pinned image identity in a fresh `--rm --network none` container;
- use a fresh work directory and no host write mount unless the case explicitly
  tests mount or filesystem behavior;
- close stdin unless stdin is part of the case;
- apply a per-process timeout and a bounded outer container timeout;
- capture stdout, stderr, raw exit/wait result, output tree, and process cleanup;
- record locale, timezone, executable hashes, Perl/Python/compiler versions,
  and optional package availability in the execution manifest; and
- retain raw evidence before normalization.

Unknown option, missing input, and parser-only cases must not accidentally
perform business work. Parallel cases may create source, object, coverage, and
callback fixtures only inside the ephemeral work directory.

Timeout cases must distinguish:

- process exit before timeout;
- watchdog soft termination;
- watchdog forced kill after grace; and
- cleanup failure with surviving descendants.

## 13. Upstream Test Cross-Reference

The primary reviewed upstream evidence is:

| Upstream test | Existing map group | Contract coverage |
| --- | --- | --- |
| `tests/genhtml/errs/msgtest.sh` | `genhtml.diagnostics-and-config` | Severity, config, message count, callback, and selected parallel lifecycle paths |
| `tests/lcov/errs/errs.sh` | `lcov.diagnostics` | Malformed, mismatch, empty, utility, inconsistent, and ignore behavior |
| `tests/lcov/format/format.sh` | `lcov.format` | Fatal/warning/silent transitions and keep-going output completion |
| `tests/lcov/extract/extract.sh` | `lcov.capture-and-filter` | Capture ignore/config/callback and keep-going behavior |
| `tests/genhtml/simple/script.sh` | `genhtml.report-options` | Version/path failures, threshold output, expected counts, and logging |
| `tests/genhtml/synthesize/synthesize.sh` | `genhtml.tracefile-synthesis` | Range warnings and per-file suppression |
| `tests/perl2lcov/perltest1.sh` | `converter.perl` | Empty database, ignored empty, and converter output |
| `tests/py2lcov/py2lcov.sh` | `converter.python` | Version callback failure and keep-going output |
| `tests/xml2lcov/xml2lcov.sh` | `converter.xml` | Usage and source failure; keep-going path is currently disabled |
| `tests/llvm2lcov/llvm2lcov.sh` | `converter.llvm` | Empty result ignore and invalid option |

The upstream suite does not provide reliable direct coverage for:

- branch-threshold failure;
- config-based line threshold;
- `genhtml --fail` token behavior;
- real fork failure and retry exhaustion;
- worker SIGTERM/SIGKILL or OOM;
- missing, corrupt, or stale child payload;
- unknown child and parent death;
- sibling termination after fatal child error;
- serial/parallel exact diagnostic parity;
- memory worker admission; or
- exact cross-worker message ordering.

`tests/common.tst` commonly supplies `--parallel 0`, so broad upstream test
execution is parallel exposure, not proof of explicit serial-versus-parallel
parity. Focused cases must set `--parallel 1` for serial controls and force more
than one real worker for parallel controls.

## 14. Milestone Ownership

### M0: Contract And Evidence Planning

M0 owns:

- completing interaction, applicability, planned-case, and evidence links for
  the existing reviewed `lcovrc.expected-message-count` inventory entry;
- correcting singular `--ignore-error` candidate interpretation;
- adding registry and raw-surface inventory ownership;
- freezing configuration discovery, arbitrary RC environment expansion, the
  fixed public runtime allowlist, clean-environment execution, and the known
  uncovered environment cases without changing the inventory schema;
- linking all applicable option/config entries to the interaction groups and
  planned case IDs in this document;
- producing reproducible Oracle manifests and raw baselines; and
- retaining ADR 0004's accepted deviation metadata.

M0 does not close while applicable entries have empty interaction or planned
case links.

### M1: Tracefile Core

M0 inventories every trigger/category/catch boundary and captures the Oracle
baseline. M1 owns only diagnostic facts produced by tracefile parsing and model
validation; category names such as `mismatch`, `inconsistent`, `range`, and
`unreachable` also have later report/source/callback emitters and are not
owned wholesale by M1.

M1 supplies typed category, source/record context, parse disposition, retained
or rejected semantic state, and atomic model mutation. It does not own final
formatted text, ignore/keep-going policy, stream, or process exit. M2 renders
the shared policy and owns lcov wrapper transformations such as an inner parser
failure becoming `corrupt`; M3-M5 own command-specific emitters.

M1 unit/property/fuzz tests MUST prove that a rejected record cannot partially
mutate committed coverage state.

### M2: Shared Runtime And `lcov`

M2 owns:

- the 32-name registry and reserved `branch` behavior;
- shared error/warning/ignore/keep-going/warning-promotion state machines;
- message counts, summaries, logging, and stdout/stderr routing;
- shared parser and raw-failure boundaries used by `lcov`;
- non-capture `lcov` exit and threshold semantics;
- aggregate/filter parallel ownership, status decoding, retry, message replay,
  memory gates, and serialization; and
- compatibility traps that apply to the shared runtime.

M2 cannot claim shared runtime compatibility until every applicable
`DIAG-*` case and non-capture `PAR-*` case passes.

### M3: `genhtml` Extension

M3 reuses the M2 shared runtime and owns `genhtml` emitters, report worker
scheduling, annotation/callback failures, and report-specific parallel cases.
Potential unbounded `genhtml` retry behavior blocks the affected case until it
is proven and classified; ADR 0004 does not authorize a deviation.

### M4: Capture And `geninfo`

M4 owns:

- `geninfo` and `lcov --capture` diagnostic emitters;
- gcov, graph, child, parent, fork, utility, package, and capture path errors;
- capture worker lifecycle, chunk serialization, sibling drain, signal and
  wrapper-status propagation, retry, and memory admission;
- both sides of `DEV-GENINFO-CHILD-001` differential evidence; and
- public proof that the bounded Ferricov result preserves the intended error
  category and status without the PID `-1` loop.

M4 cannot close if a worker can remain active after reap, if a timeout leaves
descendants, or if capture can convert a signaled child into success.

### M5: Converter Traps

M5 owns the bounded `perl2lcov`, `llvm2lcov`, `py2lcov`, and `xml2lcov`
keep-going traps plus `genpng`, `gendesc`, and other auxiliary
startup/dependency surfaces in installed-suite qualification. Converter
exit-zero/partial-output and GD-present/missing precedence remain required
unless a later accepted ADR proves a safety boundary.

## 15. Acceptance Rules

For every case, evidence must classify the case as `pass`,
`not_applicable`, or `blocked`, and mark each field `pass`,
`not_applicable`, or `blocked` so verifier-only and non-process cases do not
invent command arguments:

- inventory and interaction IDs;
- command and exact arguments;
- fixture and executable identity;
- complete environment, selected configuration path/bytes, and parser profile;
- named class or raw-surface family;
- severity and continuation decision;
- stdout, stderr, and message-log expectations;
- raw and normalized exit/status meaning;
- output artifact state;
- child and temporary-process state; and
- applicable accepted deviation ID.

Tests must prove semantic invariants, not only message substrings. A
keep-going case that checks only exit status is incomplete. A parallel case
that checks only output coverage is incomplete. A timeout case that does not
check descendant cleanup is incomplete.

Ferricov must preserve every bounded compatibility trap in this contract.
Only the exact `DEV-GENINFO-CHILD-001` result pair may intentionally differ
from the pinned Oracle without another accepted ADR.
