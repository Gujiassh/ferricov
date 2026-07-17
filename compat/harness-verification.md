# Differential Harness Verification

Verified on 2026-07-17 with the pinned LCOV 2.5 Oracle image. The complete
workspace format, check, test, and Clippy gates passed with Rust 1.85.0 and
1.95.0. Both toolchains passed all 15 unit tests.

The final Docker-backed differential run used Rust 1.85.0. All two suite, two
launcher, and seven generated result documents passed their JSON Schemas.
Every result records the actual reference and candidate executable SHA-256;
Docker executions also record the immutable image ID.

## Positive Self-Test

The `harness-self-test` suite passed all six cases:

- `lcov-version`
- `lcov-help`
- `lcov-unknown-option`, including reference exit status 1
- `genhtml-version`
- `geninfo-version`
- `oracle-workdir-mount`

The mount case copied `input.txt` into each isolated working directory and
created `generated.txt` inside the container. Both files appeared in the
captured file tree with byte length and SHA-256 digest.

The suite is explicitly marked `harness_self_test` and is not product
compatibility evidence.

## Reverse Test

The `harness-reverse-test` suite compared LCOV with an intentionally different
launcher. The case was recorded as failed, artifacts were retained, and the
runner returned process status 1 with:

```text
differential suite failed: 0 passed, 1 failed
```

CI runs this reverse case and rejects an unexpected zero exit status before it
validates the retained failure result.

## False-Pass Guards

Two independently reproduced false-pass paths are now release-blocking guards:

- renaming a launcher that resolves to the same Docker image and executable is
  rejected by actual runtime identity, not launcher JSON equality;
- duplicate case IDs and duplicate comparison dimensions are rejected before
  any output directory can be replaced or summary status overwritten.

Filesystem evidence also records raw path bytes, Unix mode and ownership,
symlink target hashes, and hardlink relationships where supported.
