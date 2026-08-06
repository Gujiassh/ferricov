# M0 Installation Wave-2 Review Note

## Scope

Lane-local wave-2 implementation for installation Oracle/reference capture
evidence. This note covers only:

- `compat/installation/**` including `compat/installation/wave2/**`
- `compat/schema/installation-contract.schema.json`
- this review note

Shared `tasks.md`, root README, SSoT docs, crates, tracefile, diagnostics, and
behavior surfaces were intentionally not edited in this lane. No Rust product
code was changed. Baseline `compat/upstream/installed-tree.sh` remains
byte-stable (directory companion lives under wave2 only).

## Decision

Accept as a bounded M0 Oracle-reference capture batch after replayable harness
rework:

- all 13 planned `INST-*` identities bind replayable per-case capture envelopes
  under `compat/installation/wave2/cases/**` (raw `stdout.bin`/`stderr.bin`,
  process metadata, file-tree effects, observation hash);
- an independent expected-case table
  (`compat/installation/wave2/expected-case-table.json`) is authoritative and
  is cross-checked against captures (captures are not self-authenticated);
- `INST-PATH-001` binds dual relative and space envelopes;
- records remain `evidence_status=oracle_reference` and
  `execution_status=planned` at the product/case level;
- independent facts promote only `oracle_execution_status=captured` with
  hashed observation artifacts;
- baseline installed-tree lock remains 321 file/symlink entries with
  `directory_entries_retained=false`;
- companion directory lock retains 57 directories at mode `755`;
- root `product_compatibility_evidence` remains false;
- no Ferricov installer, packaging, uninstall, or report renderer was
  implemented.

This is not product compatibility and does not authorize M1 or M5 installation
claims.

## Classification

- Review class: `Critical`
- Product code changed: no
- Public Suite/Result/tracefile contracts changed: no
- Installation contract extended with replayable wave-2 capture bindings,
  independent expected-case table checks, dual PATH artifacts, and directory
  companion evidence

## Semantic Oracle

1. Installed-tree lock remains 321 ordered `/usr/local` entries with SHA-256
   file digests and one legacy man symlink; Docker baseline diff still uses the
   default recorder (`INCLUDE_DIRECTORIES` unset/false).
2. Wave-2 directory companion records 57 payload directories under `/usr/local`
   with uniform mode `755` and lexicographic paths.
3. Staged DESTDIR install yields payload files without the image-only legacy
   man symlink; compiled paths retain PREFIX without DESTDIR embedding.
4. Interpreter override advertised by the Makefile is ineffective for
   `#!/usr/bin/env` shebangs; custom interpreter matches observed as 0.
5. Config discovery order is `$HOME/.lcovrc` then `$LCOV_HOME/etc/lcovrc` and
   stops after the first readable file.
6. Uninstall on an isolated DESTDIR removes recursive lib/share payload and
   source-glob man pages; foreign sentinels and non-source man pages remain;
   observed exit status is 0 with rmdir warnings on residual foreign content.
7. Induced install-loop failure leaves a non-transactional partial payload
   without rollback (exit 2).
8. Missing `sphinx-build` fails documentation before payload install
   (`PAYLOAD_FILES=0`, exit 2).
9. Relative DESTDIR/PREFIX roots are rejected; space-containing DESTDIR failed
   on the pinned GNU/Linux path (dual envelopes retained).
10. Untracked ordinary scripts can enter the install payload via dynamic `ls`.
11. Installed tests require explicit `LCOV_HOME`; unset path can resolve a
    nonexistent `/usr/local/share/lcov/bin`.
12. README path claims (`share/lcov/man`, `share/test`) mismatch retained
    filesystem roots.
13. Report-asset sample binding remains open for optional updown/HTML variants.
14. `COPYING` is present in the source archive manifest but not in the install
    payload.

## Evidence Artifacts

Pinned Oracle image id:

`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

Upstream commit:

`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

Capture format:

`replayable_case_records_v1` with ptrace live process observation (`process-observer.py`), transactional staging, runner signal/timeout qualification probes, and deterministic TEST-RUN `make -n info` with `env -i` execution, observed env/argv/cwd, full tree rows, fail-closed docker inspect + git rev-parse provenance, and an independently authored expected-case table that recapture never rewrites.

Primary capture index:

`compat/installation/wave2/oracle-capture.json`

Independent expected table:

`compat/installation/wave2/expected-case-table.json`

Per-case envelopes:

`compat/installation/wave2/cases/INST-*/{capture.json,stdout.bin,stderr.bin,...}`

Directory companion:

`compat/installation/wave2/installed-directories.lock` (57 entries, mode 755)

Harness:

- `compat/installation/wave2/capture-driver.sh` (in-container driver)
- `compat/installation/wave2/recapture.py` (host orchestrator; normalizes
  Docker-produced ownership/mode without changing bytes)

## Residual Gaps

- Baseline lock still excludes directory rows; companion is wave-2-only and not
  part of the Docker image tree diff.
- Staged DESTDIR installs omit the image-only legacy `/usr/local/man` symlink.
- Optional genhtml updown variants and HTML-reference qualification remain open.
- Space-containing path behavior is observed on this GNU/Linux install path only.
- Partial install used a fake `install` wrapper rather than native Makefile
  fault-injection points.
- No multi-platform install root matrix beyond the pinned x86_64 Linux image.
- Packaging/RPM license policy remains uncaptured.
- No Ferricov product installer/uninstall/report-renderer evidence.
- M1 parser/model installation surfaces remain blocked.
- Wave2 captures are Oracle-reference only and keep `execution_status=planned`.
- Directory companion is not verified inside the Docker image build diff against
  `installed-tree.lock`.
- Config discovery probe mirrors lcovutil search order without executing every
  consumer binary path.
- Report-asset capture scans genhtml symbols and does not execute HTML rendering.

## Validation Performed

- `python3 -m unittest compat.installation.test_contract` (68 tests)
- Contract regenerate/validate against pinned upstream checkout
- Independent expected-table co-mutation reverse tests (image, upstream, exit,
  argv, raw stdout bytes, observation hash, status promotion)
- Per-case capture schema validation (15 capture.json records including PATH
  dual parts + parent)
- `compat/verify.py --skip-oracle` (exit 0) and installation schema/contract
  checks

## Non-Claims

- Not product compatibility
- Not an evaluated gate promotion
- Not a packaging or distribution certification
- Not an authorization to change public Suite/Result APIs
