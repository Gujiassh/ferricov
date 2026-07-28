# Execution Manifests

Execution manifests bind an observed process run to the exact Oracle source,
container image, installed package closure, executables, toolchain, platform,
launcher configuration, command, environment, mounts, fixtures, and outputs.
Schema validity is necessary evidence hygiene; it is not a compatibility claim.

The canonical schema is `compat/schema/execution-manifest.schema.json`. The
validator pins that schema's SHA-256, validates Draft 2020-12 structure, checks
repository-local material hashes, enforces semantic uniqueness and claim
rules, and optionally re-runs Docker-backed evidence.

## Evidence Scope

- `environment_smoke` records the Oracle build and smoke behavior. It must not
  name inventory entries and never counts as Ferricov compatibility.
- `differential_behavior` names reviewed public inventory entries exercised by
  an Oracle/candidate differential case.
- `capture_qualification` names reviewed public capture entries and the exact
  compiler/platform lane that produced their evidence.
- `platform_qualification` names reviewed public entries qualified on the
  observed platform.

For claim-bearing scopes, every inventory ID must exist, be classified
`public`, have reviewed applicability, and appear in sorted order. This prevents
a structurally valid manifest from turning an unknown, generated, internal, or
unreviewed candidate into evidence.

## Launcher Environment

`launcher.environment_variables` is the effective explicit environment passed
to the process. It is hashed with the complete command, work directory, user,
network policy, and mount description in `launcher.configuration_sha256`.
Executable hashes remain separate, so changing a launcher profile does not
change the command executable's identity.

The dedicated POSIX parser-policy launcher uses profile `posixly_correct` and
must record:

```json
{
  "POSIXLY_CORRECT": "1"
}
```

The default profile rejects `POSIXLY_CORRECT`; it cannot silently inherit or
masquerade as the POSIX profile.

## Hash Rules

- All hashes use lowercase `sha256:<64 hex digits>` identities.
- Manifest JSON is ASCII, sorted by key, indented by two spaces, and ends with
  one newline.
- Launcher configuration hashes use compact, sorted-key ASCII JSON plus one
  newline.
- File fixtures hash their raw bytes.
- Tree fixtures hash compact sorted-key JSON entries plus one newline. Entries
  are ordered by raw relative path bytes and record `path_bytes_hex`, file type,
  Unix mode, and either file SHA-256 or symlink target bytes. This preserves
  non-UTF-8 names inside an otherwise repository-addressable fixture tree.
- stdout and stderr hash their exact raw bytes. Filesystem output hashes refer
  to the exact canonical snapshot artifact produced by the runner.

## Validation

Validate all committed records without executing Docker:

```bash
python3 compat/manifests/validate.py
```

Validate one record and prove that the current Docker tag still resolves to
the recorded image, package set, executables, toolchain, and output:

```bash
python3 compat/manifests/validate.py --verify-runtime \
  compat/manifests/oracle-lcov-v2.5-smoke.json
```

Run focused mutation tests:

```bash
python3 -m unittest discover -s compat/manifests/tests -v
```

`--verify-runtime` supports manifests without bind mounts. Differential runs
with bind mounts require the runner to resolve the abstract mount source IDs
and produce the manifest during capture; a hand-authored post-run manifest is
not accepted as proof of what the runner mounted.

## Oracle Build

`compat/upstream/build.sh` performs two no-cache builds from the pinned base
image, dated Debian snapshots over a content-addressed CA bundle, exact direct
package versions, and deterministic local archive of the exact LCOV commit.
It then writes and runtime-validates
`compat/manifests/oracle-lcov-v2.5-smoke.json`. The manifest records a Docker
image ID separately from its mutable convenience tag.

The recorded Linux `x86_64` environment is the M0/M1 Oracle baseline only. It
does not claim GCC/LLVM capture lanes, Linux `aarch64`, macOS, WSL2, MSYS2, or
native Win32 qualification.
