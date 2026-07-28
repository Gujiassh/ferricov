# ADR 0004: Upstream Defect Safety Policy

## Status

Accepted on 2026-07-27 as an architecture and safety decision.

Qualification state: **blocked**. The decision selects the bounded Ferricov
behavior, but the deviation cannot be marked qualified, used to close M4, or
claimed in a release until the evidence package defined below is retained in a
content-addressed or reproducibly built form.

This ADR accepts one intentional compatibility deviation for the pinned LCOV
2.5 Oracle: Ferricov must terminate a failed `geninfo` parallel operation in a
bounded way instead of reproducing the upstream infinite wait loop identified
as `DEV-GENINFO-CHILD-001`.

No other behavior is changed by this decision. In particular, deterministic
and bounded oddities remain compatibility requirements unless a later ADR
demonstrates a corruption, security, or unbounded-resource risk and accepts a
separate deviation.

## Evidence Qualification State

The M0 audit ran against local image tag `ferricov/lcov-oracle:v2.5` with image
ID
`sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`.
The image had no RepoDigest. The fixture and semantic observations are recorded
below, but the raw stdout, stderr, output tree, and cleanup manifest existed
only inside `docker run --rm` containers and were not retained in the
repository.

That local image ID and this session's transcript are not portable
qualification evidence. Before M4 implementation acceptance or any public
compatibility claim, M0 must recapture the complete matrix with:

- a retained content-addressed Oracle image or reproducible image manifest;
- the exact fixture files and hashes;
- raw stdout, stderr, status, and filesystem results for every command;
- watchdog and descendant-cleanup results; and
- a manifest containing executable hashes, toolchain versions, locale,
  timezone, and optional dependency state.

Until those artifacts exist, all `DEV-GENINFO-CHILD-001` cases are `blocked`,
not `pass`. Acceptance of this ADR records the intended safety boundary and
does not waive the evidence gate.

| Item | Decision state | Qualification state |
| --- | --- | --- |
| Safety policy and bounded worker-ownership rule | `accepted` | Architecture decision is in force |
| `DEV-GENINFO-CHILD-001` deviation semantics | `accepted` | Required Ferricov behavior is fixed |
| Local Oracle observations below | `observed_unqualified` | Raw container artifacts and a reproducible manifest were not retained |
| `PAR-GENINFO-CHILD-STOP-001` control | `blocked` | Byte-identical control evidence must be recaptured |
| Keep-going, one-ignore, and two-ignore asymmetric pairs | `blocked` | Both Oracle and Ferricov evidence members must exist; no pair is currently a pass |

The accepted policy is therefore usable for design, while every compatibility
or release qualification claim remains blocked. These states are intentionally
independent.

## Decision Scope

The compatibility Oracle remains LCOV `v2.5` at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`. This ADR defines:

- how Ferricov distinguishes a compatibility trap from an upstream defect;
- the evidence required before intentionally diverging from the Oracle;
- the one accepted bounded-safety deviation for `geninfo` worker failure;
- the required Oracle and Ferricov expectations for that deviation;
- public release disclosure requirements; and
- limits that prevent this decision from becoming a general license to clean
  up unusual upstream behavior.

The detailed diagnostic and parallel behavior contract is recorded in
[`diagnostics-parallel-contract.md`](../../specs/001-full-lcov-compatibility/diagnostics-parallel-contract.md).

## Context

Ferricov is a behavior-compatible rewrite, not a redesign of LCOV. Observable
bugs can therefore be part of the compatibility surface. Replacing every
surprising result with a locally preferred result would make the compatibility
claim subjective and untestable.

Compatibility also cannot require an implementation to hang indefinitely,
consume unbounded resources, corrupt user data, or preserve an exploitable
security failure. Those outcomes prevent deterministic testing, reliable
automation, and a truthful release contract. A narrow and disclosed deviation
is required when preserving the Oracle would violate those safety properties.

The M0 diagnostic and parallel audit found both kinds of behavior:

- bounded compatibility traps, such as `perl2lcov` and `llvm2lcov` reporting
  error messages under `--keep-going` and still exiting zero; and
- an unbounded `geninfo` parallel worker failure path that never terminates
  after all real children have already been reaped.

These categories require different treatment.

## Classification Rules

### Compatibility Trap

A compatibility trap is an observable upstream behavior that is surprising or
internally inconsistent but remains bounded. It is preserved when all of the
following are true:

1. the process terminates without an external kill under a bounded fixture;
2. CPU, memory, file, process, and output growth are bounded by the operation;
3. the behavior does not create an identified security violation or corrupt
   data outside the operation's declared output boundary;
4. the result can be represented by a deterministic or explicitly normalized
   differential case; and
5. reproducing it does not prevent Ferricov from enforcing its public resource
   and lifecycle guarantees.

Compatibility traps retain the Oracle's exit status, streams, artifacts, and
message semantics. They must have explicit regression cases so a future
maintainer does not "fix" them accidentally.

The following audited behaviors are compatibility traps, not deviations:

- `perl2lcov --keep-going` can print an error summary and exit `0` because the
  command does not apply the shared `saw_error()` finalizer;
- `llvm2lcov --keep-going` has the same exit-zero behavior;
- raw Perl `die` paths have command- and phase-specific exit statuses;
- Python converter errors can be written to stdout rather than stderr;
- `xml2lcovutil.py` accepts arbitrary arguments and exits `0` without output;
- a single ignored error becomes a warning while a duplicate ignored error is
  silent; and
- parallel child output can be replayed in completion order rather than input
  order where the applicable case permits nondeterministic ordering.

These behaviors can only be reclassified through a later accepted ADR with new
evidence. This ADR does not authorize their normalization.

### Known Upstream Defect

An upstream behavior is eligible for an intentional safety deviation only when
reproducible evidence proves at least one of these conditions:

- nontermination after the operation has no remaining productive work;
- unbounded process, output, CPU, memory, retry, or file growth;
- corruption of input or unrelated user data;
- an identified security failure that Ferricov cannot safely reproduce; or
- a conflict with a previously accepted Ferricov safety guarantee.

The deviation must then satisfy every requirement below:

1. identify the exact upstream commit, fixture, command, and timeout or failure
   evidence;
2. isolate the smallest faulty state transition;
3. preserve the upstream diagnostic category and intended success/failure
   result where doing so is safe;
4. change no adjacent bounded behavior without separate evidence;
5. define positive and reverse differential cases;
6. disclose the deviation in public compatibility documentation; and
7. record a stable deviation identifier that can be referenced by releases and
   test evidence.

## Accepted Deviation: `DEV-GENINFO-CHILD-001`

### Upstream Symptom

LCOV 2.5 `geninfo` can enter an infinite wait loop when a parallel worker exits
non-zero and the `child` error is nonfatal because of `--keep-going` or
`--ignore-errors child`.

The exact source fixture used by the M0 audit is shown below.

`a.c`:

```c
int a(int x){return x+1;}
```

`b.c`:

```c
int b(int x){return x+2;}
```

`main.c`:

```c
int a(int); int b(int); int main(void){return a(1)+b(1)==5?0:1;}
```

Each file ends with one newline. Their SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `a.c` | `3299eca4d87337210531320e68409727733995891030dc38df23575442266862` |
| `b.c` | `759fe88339e0446e993f524696cb915bed0f4cd6a3fe82190da0fc3e8dc67770` |
| `main.c` | `c00eeaedfdb7ae78ab5e48350f85c386096b29f40152dde57cc78465edbab78a` |

The exact callback is:

```perl
package ExitStart;
use POSIX ();
sub new { my ($class) = @_; bless {}, $class }
sub start { POSIX::_exit(7) }
sub save { return undef }
sub restore { return }
sub extract_version { return "v" }
sub compare_version { return 1 }
1;
```

`ExitStart.pm` ends with one newline and has SHA-256
`d49c1cd6b95161f13541849f20bbfc3dd633ec03f1fe7d82700fdf128c854525`.
The fixture was built and executed with:

```sh
gcc --coverage -O0 a.c b.c main.c -o app
./app
```

This produces three `.gcno`/`.gcda` pairs and a three-chunk `geninfo` worklist.
It was generated inside a fresh network-disabled Oracle container with no host
mount for temporary output.

The timeout is evidence about this finite fixture, not a universal three-second
product limit. The fixture's serial control completes well below the watchdog.

### Pinned Oracle Evidence

The local, not-yet-qualified evidence matrix is:

| Case | Oracle result |
| --- | --- |
| `--parallel 1` | Exit `0`; non-empty info output; empty stderr. The callback lifecycle does not force a worker process. |
| `--parallel 2` | Exit `1`; no info output; one or more `child` diagnostics reporting child exit status `7`. |
| `--parallel 2 --keep-going` | Watchdog exit `124`; no info output; real worker failure diagnostics followed by repeated `found unknown process -1`. |
| `--parallel 2 --ignore-errors child` | Watchdog exit `124`; no info output; worker failure is downgraded according to ignore policy, then repeated `found unknown process -1`. |
| `--parallel 2 --ignore-errors child,child` | Watchdog exit `124`; no info output; child failures and the PID `-1` loop are console-silent because the class is ignored twice. |

The exact observed invocations were:

```sh
timeout --signal=TERM --kill-after=1s 3s geninfo --parallel 1 \
  --output-filename serial.info --version-script ./ExitStart.pm .

timeout --signal=TERM --kill-after=1s 3s geninfo --parallel 2 \
  --output-filename stop.info --version-script ./ExitStart.pm .

timeout 4 geninfo --parallel 2 --output-filename keep.info \
  --version-script ./ExitStart.pm --keep-going .

timeout --signal=TERM --kill-after=1s 3s geninfo --parallel 2 \
  --output-filename ignore-child.info --version-script ./ExitStart.pm \
  --ignore-errors child .

timeout --signal=TERM --kill-after=1s 3s geninfo --parallel 2 \
  --output-filename ignore-twice.info --version-script ./ExitStart.pm \
  --ignore-errors child,child .
```

The non-uniform watchdog in the original keep-going observation is another
reason this matrix must be recaptured under one retained execution manifest.

PIDs, temporary paths, timestamps, and the number of repeated `-1` messages are
volatile. The keep-going and one-ignore Oracle cases must require at least one
real child-status-7 diagnostic followed by at least one
unknown-process-`-1` diagnostic before the watchdog kills the process. They
must not require a fixed repeat count. The two-ignore case must instead prove
the live nonterminating state through the watchdog and process-state evidence;
it must require empty stderr rather than inventing a suppressed diagnostic.

### Upstream Root Cause

The root cause is a stale active-worker count:

- `bin/geninfo:1129` calls `wait()` and receives the child PID, or later `-1`
  after no children remain;
- `bin/geninfo:1225-1255` reports a failed worker and returns false;
- `bin/geninfo:1428-1429` and `bin/geninfo:1570-1572` decrement
  `currentParallel` only when the merge function returns true; and
- `lib/lcovutil.pm:1582-1583` makes errors nonfatal under `--keep-going`.

The failed PID has already been reaped, but it remains represented by the
active count. The scheduler waits again, obtains `-1`, reports an unknown child,
and repeats without a state transition that can reach completion.

### Ferricov Required Behavior

Ferricov must not reproduce the infinite loop. Its parallel runtime must:

1. remove every successfully reaped PID from the active-worker set exactly
   once, regardless of worker success, decode success, or ignore policy;
2. preserve the originating `child` diagnostic fact and the observed child
   exit status `7`, while applying the normal error, warning, or silent-ignore
   console policy;
3. discard the failed worker's incomplete chunk rather than merging it as a
   success;
4. continue draining already-running siblings when policy permits;
5. continue admitting pending chunks when keep-going or explicit ignore policy
   would ordinarily permit that work, so process ownership is the only changed
   state transition;
6. terminate after pending work and the active-worker set are empty;
7. for this all-failing three-chunk fixture, report `empty` after the last
   failed chunk because no coverage data was committed;
8. return exit `1`: through `saw_error()` for keep-going, or through the
   unignored `empty` error for the one-ignore and two-ignore cases;
9. retain one-ignore warning and two-ignore silent-message/count behavior for
   every real failed child; and
10. never report synthetic unknown PID `-1` messages from a normal exhausted
   child set.

If internal state claims an active worker after the operating system reports
that no children remain, Ferricov must fail closed with a bounded internal
parallel-state error. It must not spin, retry without a budget, or silently
claim success.

This rule bounds child bookkeeping. It does not impose a general wall-clock
timeout on legitimate compiler, callback, or report work.

### Differential Acceptance

The deviation requires three asymmetric Oracle/Ferricov pairs:

| Pair | Pinned Oracle | Required Ferricov result |
| --- | --- | --- |
| `PAR-GENINFO-CHILD-EXIT-{ORACLE,FERRICOV}-001` | Keep-going reaches watchdog `124`; real status-7 `ERROR` records precede the PID `-1` loop; no artifact | Process all three failed chunks, retain three status-7 `ERROR` facts, report `empty`, emit no PID `-1`, create no artifact, exit `1` through `saw_error()` |
| `PAR-GENINFO-CHILD-IGNORE1-{ORACLE,FERRICOV}-001` | One ignore reaches watchdog `124`; real status-7 `WARNING` records precede warning PID `-1` loop; no artifact | Process all three failed chunks, emit three status-7 `WARNING` records, report unignored `empty`, emit no PID `-1`, create no artifact, exit `1` |
| `PAR-GENINFO-CHILD-IGNORE2-{ORACLE,FERRICOV}-001` | Two ignores reach watchdog `124` with empty stderr and no artifact; process-state evidence proves the silent loop | Process all three failed chunks, emit no child console records, retain child ignore count `3`, report unignored `empty`, emit no PID `-1`, create no artifact, exit `1` |

The comparison is intentionally asymmetric. A generic byte-for-byte runner
must not mark the Ferricov result incompatible merely because it terminates.
Each case manifest must reference `DEV-GENINFO-CHILD-001` and apply its exact
approved expected-result pair. The default-stop control remains byte-identical
and is not part of the deviation. `PAR-GENINFO-CHILD-STOP-001` freezes that
control as exit `1` after the first fatal status-7 child diagnostic, with no
output artifact and no PID `-1` message.

Each row above is a complete two-member acceptance pair. An Oracle-only timeout
observation, a Ferricov-only bounded result, or a missing ignore-count variant
leaves the corresponding pair `blocked`. The three pairs are independent: a
pass for keep-going cannot qualify either explicit-ignore behavior.

A reverse case must inject a stale-active-set condition into the Ferricov
parallel runtime and prove that the runtime returns a bounded internal failure.
Tests that only use a global timeout without checking the state transition are
insufficient.

## Timeout And Process Policy

All failure-focused Oracle and Ferricov cases must use an outer watchdog and a
process-group cleanup policy. The execution manifest records:

- soft timeout;
- kill grace period;
- final kill signal;
- observed process exit or watchdog status;
- whether child processes remained after cleanup;
- stdout and stderr captured before termination; and
- output and temporary-file state after cleanup.

The watchdog is an evidence boundary, not an output normalizer. A timeout is a
first-class result. It cannot be converted to an ordinary exit status or
discarded from a compatibility report.

Tests that expect upstream timeout must run in an ephemeral environment with
network disabled and bounded writable storage. They must verify that no
container or child process remains after the case.

## Explicit Non-Decisions

This ADR does not approve deviations for other audited parallel oddities,
including:

- `genhtml` retry-count plumbing around missing or killed worker dumps;
- shifted wait-status interpretation in aggregate workers;
- `lcov --capture` signal-status forwarding;
- release order of child stdout, stderr, or message-log entries;
- two-worker admission before the current memory gate applies; or
- converter exit-zero behavior after bounded keep-going errors.

Each remains an Oracle requirement or an unqualified risk until a focused case
proves the behavior and a later ADR classifies it. Suspected nontermination in
another path blocks that path's implementation or release qualification; it
does not inherit this deviation automatically.

## Public Disclosure

Every release that implements `geninfo` parallel capture must publish this
deviation in its compatibility exceptions. The disclosure must state:

- the upstream version and commit;
- the deviation ID `DEV-GENINFO-CHILD-001`;
- that upstream may hang after a failed parallel worker under keep-going or an
  ignored child error;
- that Ferricov preserves the failure diagnostic and failed result but
  terminates in bounded time; and
- the Ferricov case evidence and execution manifest used for qualification.

Release notes must not describe the result as fully byte-identical behavior.
They may describe it as an intentional safety deviation within an otherwise
qualified compatibility surface.

## Governance

A new deviation requires an accepted ADR. A test expectation, implementation
comment, issue, or pull request is not sufficient authorization.

Reviewers must reject a proposed deviation when:

- the behavior is merely inconvenient or surprising;
- the evidence fixture is not pinned and reproducible;
- a bounded compatibility implementation is feasible;
- the proposed change alters adjacent behavior without cases; or
- the release disclosure and reverse tests are absent.

This deviation may be reconsidered if a later upstream release fixes the loop,
but Ferricov 1.0 remains pinned to LCOV 2.5. A newer upstream result is evidence
for the chosen bounded behavior, not a replacement for the pinned Oracle.

## Consequences

Ferricov's compatibility process now has an explicit exception mechanism that
is narrow enough to remain falsifiable. Most bugs and oddities remain part of
the Oracle. A behavior can cross the safety boundary only with reproducible
evidence, a stable deviation ID, exact expected semantics, reverse tests, and
public disclosure.

The accepted `geninfo` behavior removes an infinite loop without hiding the
worker failure or converting it into success. It also establishes a required
parallel-runtime invariant: reaping and worker-set ownership are independent
of the worker's business result.
