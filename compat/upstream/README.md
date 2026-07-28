# Pinned Upstream Oracle

`Dockerfile` builds LCOV 2.5 at the exact commit declared in the compatibility
contract. The build uses the pinned Debian base digest, the Debian
`20260713T000000Z` package snapshots, and every direct package version in
`packages.lock`. `packages.full.lock` also pins the complete installed package
closure, including the base image and transitive dependencies. The build fails
if either lock differs. `installed-tree.lock` additionally pins all installed
LCOV files, modes, and symlink targets, including `lcovutil.pm`, support
scripts, assets, and manuals. The source archive is regenerated from the exact
LCOV commit rather than trusting the mutable release tag or a network checkout.

The pinned slim base does not contain a CA bundle before package installation.
`snapshot-ca-certificates.crt` is deterministically assembled from the exact
`ca-certificates=20230311+deb12u1` package recorded in `build-inputs.lock`.
APT uses that content-addressed bundle to verify HTTPS snapshot transport, then
still verifies signed Debian metadata and exact package versions.

Build, smoke-test, record the content-addressed Docker image ID, and validate
the observed execution manifest with:

```bash
compat/upstream/build.sh
```

The standalone script reads the clean upstream checkout from
`LCOV_SOURCE_ROOT`, defaulting to a sibling `lcov-upstream-reference` directory.
`python3 compat/verify.py` is the portable full gate: it clones the pinned tag,
validates its commit and test map, and passes that checkout to the build.

If the local Docker installation requires an isolated configuration, set
`DOCKER_CONFIG` for the command. The release benchmark runner will execute the
Perl and Rust binaries inside the same environment.

`build.sh` always performs a clean package/source build, writes a run-specific
manifest under `/tmp`, and refreshes `ferricov/lcov-oracle:v2.5` as a local
convenience alias for the first verified image. Set `ORACLE_MANIFEST` explicitly
when recording reviewed evidence at another path. The build never overwrites
the committed observed record by default; CI must not validate evidence that it
just replaced. The manifest records the image, source, installed packages,
installed tree, executables, toolchain, platform, launcher environment,
command, mounts, fixtures, and output identities. The portable verifier reads
the immutable image ID back from this manifest for every later probe rather
than trusting the alias. Its `environment_smoke` scope proves only the Oracle
environment and installation; it is not Ferricov compatibility evidence.

The build uses Docker's default build network. Set `ORACLE_BUILD_NETWORK` when
another build network is required. Network access is disabled for every
recorded Oracle execution regardless of the network used to retrieve signed
build inputs.

Validate committed manifests without Docker:

```bash
python3 compat/manifests/validate.py
```

Re-check the observed image, installed files, package set, and smoke output:

```bash
python3 compat/manifests/validate.py --verify-runtime \
  compat/manifests/oracle-lcov-v2.5-smoke.json
```

Image tags remain convenience aliases. Formal evidence uses the
`sha256:<digest>` recorded in the execution manifest.
