# M0 Resource CI Rebuild-Image Fix Delivery Ledger

## Delivery Identity

- Source authorized delivery: `c2111e90f23b5590dcd7bc5d88e54709ac8b9022`
  (`c2111e9`)
- Repair branch: `fix/resource-ci-rebuild-image`
- Repair starting SHA: `c2111e90f23b5590dcd7bc5d88e54709ac8b9022`
- Downstream target: `main`
- Repair commit SHA: `19566ae6bdf6bac4ac0fc8bd6df08bab5791a22a`
- Push state: repair commit pushed to `origin/fix/resource-ci-rebuild-image`
- Integration step: reviewed fast-forward completed on `main` at
  `11631d607bab845a8658ab2b50265b7c2b39d68d`

## Failed Run

- Hosted CI run: `30509026860`
- Failed job/step: `Oracle Evidence / Exercise resource capture path`
- Symptom: after `compat/verify.py` successfully rebuilt and validated the
  Oracle, canonical `compat/resources/capture.py` tried to inspect historical
  image ID
  `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`,
  which is not present on a clean hosted runner.
- Root cause: `compat/upstream/build.sh` proves reproducible package,
  installed-tree, key-file, and smoke closures, but Docker image configuration
  IDs legitimately vary between closure-equivalent builds. The CI step
  incorrectly treated historical canonical image identity as a rebuild output.

## Repair Scope

- Add `compat/resources/exercise.py`, a CI-only adapter outside the canonical
  six-file resource harness.
- Validate the committed canonical contract before making an in-memory copy.
- Resolve the job-local `ferricov/lcov-oracle:v2.5` alias once to an immutable
  image ID, then use only that ID for runtime verification and all 13 profiles.
- Preserve the canonical LCOV executable SHA-256 requirement.
- Validate exact ordered profile identity, input, clean outcome, streams,
  semantic summary, canonical raw metrics schema/values, artifact descriptor
  schema, cleanup, samples-only tree closure, and adapter-local sample schema
  semantics with deterministic dotted-path failures.
- Reject caller output-root symlinks before path resolution, image inspection, or
  profile execution.
- Emit no `result.json` and retain no rebuilt resource result.
- Replace the hosted CI canonical capture invocation with the rebuilt-image
  exercise after the existing closure-verified build.
- Add focused adapter tests and synchronize CI/SSoT/review documentation.

## Canonical Invariants

- Canonical contract SHA-256 remains
  `4de3f0b2474034c96dcac068909bcb7f8a2d23240ae0265b7797e653c8777ada`.
- Canonical retained result SHA-256 remains
  `526d2c81b33776928cbd1e049a32c16cf5229f2764fd36c9063c35ee453894f4`.
- Canonical retained image remains
  `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`.
- `compat/resources/exercise.py` is not canonical evidence, a product limit, a
  compatibility result, or performance evidence.
- `M1-MD-020`, `M1-TF-063`, and `M1-TF-064` remain blocked.

## Verification

- Focused adapter tests: 11/11 pass
- Existing canonical resource tests: 42/42 pass
- Combined resource tests: 53/53 pass
- Python compilation: pass
- BasedPyright: 0 errors, 0 warnings
- Canonical contract/result validation: pass
- Canonical contract SHA-256 unchanged:
  `4de3f0b2474034c96dcac068909bcb7f8a2d23240ae0265b7797e653c8777ada`
- Canonical result SHA-256 unchanged:
  `526d2c81b33776928cbd1e049a32c16cf5229f2764fd36c9063c35ee453894f4`
- `compat/verify.py --skip-oracle`: pass
- CI YAML parse: pass
- `git diff --check`: pass
- Local real alias exercise: pass against rebuilt immutable image
  `sha256:86cb121dfb4bb4d33f2547416953eb1dbf383b8f72bec88635e7a077616a9221`,
  with 13 profiles and no `result.json`
- Hosted CI rerun: GitHub Actions run `30512678167` passed `Rust 1.85.0`,
  `Rust stable`, `Behavior Contract`, and `Oracle Evidence`; the rebuilt-image
  resource exercise passed on the clean hosted runner

## Review And Integration

- Independent Critical review: attested after three adversarial review rounds
- Review findings: no blocker; 479 schema-invalid sample mutations, coherent raw
  metric mutations, caller-root symlink handling, immutable alias resolution,
  canonical LCOV identity, and the exact samples-only tree were independently
  verified
- Controller dev-workbench checkpoint: recorded after hosted CI success
- Commit/push authorization: granted by the user for delivery and repair
- Target integration: fast-forward the reviewed repair into `main`, then confirm
  the `Oracle Evidence` job passes the rebuilt-image resource exercise
