# Oracle Baselines

This directory defines M0 Oracle-only performance workloads and the Linux
measurement helper used inside the pinned Oracle container. These results are
raw baseline observations. They are never Ferricov compatibility or performance
claims while a candidate implementation and passing compatibility evidence do
not exist.

The initial suite contains one owner-approved representative workload for each
required family: startup, tracefile, operation, and report. Every sample runs in
a fresh work directory with the network disabled. Fixture preparation, Docker
startup, artifact hashing, and schema validation are outside the measured
interval.

The suite may name a convenience image tag. Before measurement, the runner
requires that tag to resolve to the immutable image ID in the execution
manifest, then uses only that immutable ID for every sample.

Run the suite after recording and validating the Oracle execution manifest:

```bash
cargo run --locked -p ferricov-oracle --bin oracle-baseline -- \
  compat/benchmarks/m0-oracle-baseline.json \
  compat/manifests/oracle-lcov-v2.5-smoke.json \
  /tmp/ferricov-m0-baseline
```

Validate the suite and retained result:

```bash
python3 compat/benchmarks/validate.py --suite \
  compat/benchmarks/m0-oracle-baseline.json
python3 compat/benchmarks/validate.py --result \
  compat/benchmarks/results/oracle-x86_64-linux-20260728/result.json
```

The retained 2026-07-28 baseline contains 16 raw samples across the four
families. Its canonical result SHA-256 is
`851fe9ca0b81e5af95139d1daad84afad413e0da083cdee21266f3644e348131`.

The result status is always `baseline_only` and its performance gate is always
`not_evaluated`. A future candidate comparison must reference real
`compatibility` evidence with a passing correctness result; harness self-tests
cannot unlock a performance gate.
