# M1-CORE-009 bounded fuzz harness

This package owns the nine named `M1-FZ-*` libFuzzer entry points. It is
excluded from the release workspace because it requires nightly Rust and
`cargo-fuzz`; the shared harness remains ordinary safe Rust in
`ferricov-tracefile` and is covered by stable deterministic property tests.

CI uses exactly 64 runs per target, `max_len=1048576`, a two-second per-input
timeout, a 512 MiB RSS limit, and a 60-second target ceiling. These are harness
safety caps from the activation contract, not product limits. Scheduled runs
may use the separately recorded scheduled caps.

libFuzzer writes a raw failure artifact. Minimize it under the same caps with
`cargo +nightly fuzz tmin TARGET ARTIFACT`, replay the minimized bytes without
minimizer instrumentation, and retain it under `fuzz/corpus/TARGET/` together
with a JSON sidecar containing target ID, seed, raw SHA-256, first failing
operation, semantic snapshots, streams/status, runtime manifest, and links to
the originating `M1-MD-*`, `M1-TF-*`, `M1-PROP-*`, and `M1-FZ-*` IDs. Corpus
entries may be removed only when redundant coverage is demonstrated; every
bug-derived minimized entry is permanent.

This campaign does not execute the LCOV Oracle, close `M1-MD-020`,
`M1-TF-063`, or `M1-TF-064`, or provide product compatibility evidence.
