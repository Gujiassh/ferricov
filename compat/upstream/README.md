# Pinned Upstream Oracle

`Dockerfile` builds LCOV 2.5 at the exact commit declared in the compatibility
contract. Build and smoke-test it with:

```bash
compat/upstream/build.sh
```

If the local Docker installation requires an isolated configuration, set
`DOCKER_CONFIG` for the command. The release benchmark runner will execute the
Perl and Rust binaries inside the same environment.
