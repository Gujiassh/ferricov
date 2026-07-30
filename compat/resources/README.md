# LCOV 2.5 Oracle Resource Observation

This directory owns the executable M0 `M0-RSRC-MEASURE-001` resource
contract. It generates 13 deterministic controlled scale profiles covering
four field sizes, three data-record counts, three section counts, and three
four-family cardinalities. Each profile has one primary scale axis; every
induced input dimension is recorded, including source-scoped coverage-point
cardinality.

`capture.py` runs each profile through `/usr/local/bin/lcov
--branch-coverage --mcdc-coverage --summary input.info` in the
content-addressed LCOV 2.5 Oracle. The command environment is cleared, network
access is disabled, and the documented harness memory, PID, and timeout budgets
are applied. The host-side bounded `docker run` is the only deadline observer;
`subprocess.TimeoutExpired` is a timeout, while an Oracle exit code of 124
before that deadline is an ordinary nonzero outcome. Each retained successful
sample includes raw `metrics.json`, stdout, stderr, wall/user/system CPU time,
peak RSS, exact outcome, input immutability, unexpected-output inspection, and
cleanup evidence. The successful result tree is closed exactly over
`result.json` and the three artifacts for each of 13 samples. The result also
records host kernel, architecture, CPU, logical CPU count, memory, Docker, and
cgroup identity so the single-run observations remain interpretable.

All 13 reviewed stdout hashes and semantic summaries are part of the static
contract. Branch and MC/DC flags are explicit because plain `lcov --summary`
does not surface those families. One logical generated MC/DC condition emits
two condition outcomes; the reviewed summary therefore expects one hit of two
outcomes per logical condition.

When the fresh output storage remains writable, post-generation capture
failures retain canonical diagnostics under `failures/<profile-id>/` before
`capture.py` raises. The directory contains the exact generated input, every
available raw metric/stream artifact, Docker client streams and status, failure
class/reason, configured host deadline, measured outcome when available, and
post-cleanup facts. If artifact or manifest retention itself fails, the final
error reports both the original capture failure and the retention failure and
does not claim a failure manifest exists. Named-container and temporary
work/evidence cleanup is still attempted unconditionally and reported fail
closed. A failed capture directory is diagnostic evidence, not a successful
result and cannot pass `validate.py --result`.

This is bounded Oracle acceptance/resource evidence, not a repeatable
performance benchmark. Timing and RSS are single-run observations without a
stable distribution. Harness budgets are not Ferricov product limits,
allocations are not observable through the current backend, and no product
compatibility or product-limit claim is present.

Regenerate and validate the static contract:

```sh
python3 compat/resources/contract.py --write
python3 compat/resources/contract.py
python3 compat/resources/validate.py --contract
```

Capture only after the pinned Oracle image has been built and validated. The
output path must be new or empty; do not point capture at the committed retained
result directory:

```sh
output="$(mktemp -d)"
python3 compat/resources/capture.py --output "$output"
python3 compat/resources/validate.py --result "$output/result.json"
```

Promote a new capture only after independent review of the fresh directory,
its contract and harness hashes, runtime identity, exact stream semantics, and
all raw metrics. Replace the canonical uncommitted result as an explicit
reviewed operation; `capture.py` never overwrites a nonempty directory.

Run the 42 focused positive/reverse tests. Failure-path coverage includes raw
signal evidence and a combined original-capture, output-retention, and
container-cleanup failure diagnostic:

```sh
python3 -m unittest compat/resources/test_contract.py
```
