# Oracle Verification

Initially verified on 2026-07-17 with:

```bash
DOCKER_CONFIG=/tmp/ferricov-docker-config compat/upstream/build.sh
```

Reverified on 2026-07-28 through `python3 compat/verify.py`. The formal run
performed two independent no-cache builds and matched their package closure,
321-entry installed tree, 18 key files, and 10-command help smoke output. It
also matched the committed package and installed-tree locks. The retained
environment record is
`compat/manifests/oracle-lcov-v2.5-smoke.json` and passes both static and Docker
runtime validation.

The reproducibility identities from that run are:

- package closure: `sha256:e41c5a77487657a65e03309ac262a25088e8c020c20a630ed8ae5a3f1e0946b6`
- installed tree: `sha256:75edeea2799a5f13715df5dd119bc10614ee347aa5fc33e37fbeb21cafd8fd24`
- key files: `sha256:0f7579cbdcf10ee522eb76cc69a315cf4a083565c62b6ed6e0941b68054a5eb3`
- smoke output: `sha256:26778dbb6876544d5fa4cadeccf7a77cfa0e9e7424e68acdeb14e69f457a2a0a`

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
