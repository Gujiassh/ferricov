# Oracle Correctness Baselines

This directory retains raw observations from the pinned LCOV 2.5 Oracle. An
Oracle correctness baseline records what the reference implementation did; it
does not compare Ferricov and cannot provide product compatibility evidence.

Record the M0 CLI baseline from the repository root with:

```bash
cargo run -p ferricov-oracle --bin oracle-correctness-baseline --locked -- \
  compat/fixtures/m0-cli-contract/case-contract.json \
  compat/manifests/oracle-lcov-v2.5-smoke.json \
  compat/launchers/lcov-v2.5-oracle.json \
  compat/correctness/baselines/m0-cli-oracle-v2.5
```

The output directory must not exist or must be empty. The runner copies the
case contract, execution manifest, launcher, and suites into the retained
result. Every case records the immutable container image and executable
SHA-256 identities, exact effective environment, execution user, exit or
signal result, raw stdout and stderr, filesystem tree, timeout state, cleanup
evidence, and measurement metadata.

Validate the retained baseline with:

```bash
python3 compat/correctness/validate.py
```

To check reproducibility, record another baseline in an empty directory and
compare its semantic observations with the retained result:

```bash
python3 compat/correctness/validate.py \
  compat/correctness/baselines/m0-cli-oracle-v2.5/result.json \
  --compare /path/to/replay/result.json
```

Replay comparison ignores timing measurements and independently reproducible
image IDs. It requires the same case identities, commands, arguments, exit or
signal results, stdout, stderr, and filesystem trees. The only semantic replay
normalization is replacing Perl's random `/tmp/<tempfile>` token in `geninfo`
failure diagnostics; raw stderr remains unchanged on disk. Both inputs must
first pass their complete schema, artifact-integrity, execution-identity,
environment, timeout, and cleanup validation.

The retained documents deliberately set `product_compatibility_evidence` to
`false`. Only a later differential run against a distinct Ferricov executable
may produce product compatibility evidence.
