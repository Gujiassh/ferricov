# LCOV 2.5 Installation And Asset Contract

This directory contains the standalone, fail-closed M0 contract for the
installed LCOV 2.5 layout and report assets. It records the pinned Oracle tree,
the Makefile/source closure, the planned installation case identities, exact
Oracle reference-only case records for all 13 `INST-*` identities, retained
report-asset observations, and wave-2 Oracle capture evidence under `wave2/`.
It does not implement installation, packaging, report rendering, or Ferricov
product compatibility.

The retained baseline tree contains 321 file or symlink entries from the pinned
Oracle: 320 SHA-256-identified files and one legacy
`/usr/local/man -> share/man` symlink. Paths must be canonical,
lexicographically ordered, absolute, and under `/usr/local`. Directory entries
are still excluded from `compat/upstream/installed-tree.lock` so the Docker
image baseline remains byte-stable. Wave 2 retains a companion directory lock
with 57 payload directories (uniform mode `755`) at
`compat/installation/wave2/installed-directories.lock`. The tree recorder
supports optional directory rows via `INCLUDE_DIRECTORIES=1` without changing
the default 321-entry baseline.

The four report samples retain the same seven generated assets; each output
tree is bound through its sample metadata and duplicate asset paths are
rejected. The 13 installation case records in `oracle-case-records.json` are
independent-fact Oracle references only; every case remains
`execution_status=planned` with empty product evidence. Wave-2 captures bind
`oracle_execution_status=captured` observation artifacts for each identity while
keeping product compatibility evidence false.

## Wave-2 replayable captures

Wave-2 replaces curated text summaries with replayable per-case envelopes:

- Host orchestrator: `wave2/recapture.py`
- In-container driver: `wave2/capture-driver.sh`
- Strict per-case schema: `wave2/oracle-case-capture.schema.json`
- Capture index: `wave2/oracle-capture.json` (`capture_format=replayable_case_records_v1`)
- Independent expected table: `wave2/expected-case-table.json` (authoritative;
  contract does not trust capture JSON alone)
- Envelopes: `wave2/cases/INST-*/` with raw `stdout.bin`/`stderr.bin`,
  `status.env`/`meta.env`, `tree-effects.json`, and `capture.json`
- `INST-PATH-001` retains dual `relative/` and `space/` envelopes

After each Docker run, `recapture.py` rewrites capture files byte-for-byte as
the invoking user so reverse-mutation tests can restore originals without sudo
and without changing observation hashes.

Validate against a clean pinned checkout:

```sh
export LCOV_SOURCE_ROOT=/tmp/lcov-upstream-reference
python3 compat/installation/contract.py \
  --upstream-root "$LCOV_SOURCE_ROOT"
python3 -m unittest compat.installation.test_contract
```

Regenerate only after an intentional reviewed contract change:

```sh
export LCOV_SOURCE_ROOT=/tmp/lcov-upstream-reference
python3 compat/installation/contract.py \
  --upstream-root "$LCOV_SOURCE_ROOT" \
  --write
```

Replay captures (pinned image + upstream) only when intentionally refreshing
Oracle envelopes:

```sh
export LCOV_SOURCE_ROOT=/tmp/lcov-upstream-reference
python3 compat/installation/wave2/recapture.py
# then regenerate contract hashes/document under review
```


Wave-2 captures use `process-observer.py` (ptrace exec-stop) for live exe/argv/cwd/wait evidence, transactional recapture staging, and retained runner qualification probes under `wave2/cases/_runner/`.


Executable identity is hashed from the open `/proc/<pid>/exe` file descriptor at post-exec ptrace stop. Recapture replacement of cases/index/directory-lock is transactionally rolled back on Python exceptions (not crash-atomic). Runner qualification captures are production-loaded via `validate_wave2_runner_qualification()`.


Executable identity retains path + content hash from the open `/proc/<pid>/exe` FD only. Container-local device/inode numbers are never persisted in status/meta/capture surfaces so cross-clone strict replay remains byte-stable.
