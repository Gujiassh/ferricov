# Oracle Verification

Verified on 2026-07-17 with:

```bash
DOCKER_CONFIG=/tmp/ferricov-docker-config compat/upstream/build.sh
```

Observed version output:

```text
lcov: LCOV version 2.5-beta
genhtml: LCOV version 2.5-beta
geninfo: LCOV version 2.5-beta
```

These strings are emitted by the commands after the upstream `make install`
flow. The immutable source target remains the GitHub `v2.5` release tag and
commit below; Ferricov does not rewrite the installed upstream version string.

The build checked that `/opt/lcov` resolved to commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` before creating image
`ferricov/lcov-oracle:v2.5`.

The image installs all 10 commands under `/usr/local/bin` with mode `0755`,
including `xml2lcovutil.py`. That helper accepts `--help` with an empty output;
its public classification relies on the install manifest and source behavior,
not extracted help options.
