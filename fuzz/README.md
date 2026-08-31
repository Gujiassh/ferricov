# M1-CORE-009 bounded fuzz harness

This package owns the nine named `M1-FZ-*` libFuzzer entry points. It is
excluded from the release workspace because it requires nightly Rust and
`cargo-fuzz`; the shared harness remains ordinary safe Rust in
`ferricov-tracefile` and is covered by stable deterministic property tests.

CI uses exactly 64 runs per target, `max_len=1048576`, a two-second per-input
timeout, a 512 MiB RSS limit, and a 60-second target ceiling. These are harness
safety caps from the activation contract, not product limits. Scheduled runs
may use the separately recorded scheduled caps.

libFuzzer uses the fixed seed `12648430` in CI and writes a raw failure artifact.
Run `python3 fuzz/scripts/retain_finding.py TARGET CASE_ID ARTIFACT
--runtime-manifest RUNTIME.json --origin M1-PROP-...` to minimize under the
same caps, replay without minimizer instrumentation, validate the staged
sidecar, and atomically install the finding plus canonical manifest entry.
Retain it under `fuzz/corpus/TARGET/` together
with a JSON sidecar containing target ID, seed, raw SHA-256, first failing
operation, semantic snapshots, streams/status, runtime manifest, and links to
the originating `M1-MD-*`, `M1-TF-*`, `M1-PROP-*`, and `M1-FZ-*` IDs. Corpus
entries may be removed only when redundant coverage is demonstrated; every
bug-derived minimized entry is permanent.

`python3 fuzz/scripts/validate_artifacts.py` validates every manifest pattern,
corpus SHA-256, target/case binding, and any retained sidecar/artifact pair.
The sidecar must conform to `fuzz/failure-sidecar.schema.json`; mutation tests
for fail-closed hash handling run in CI.

This campaign does not execute the LCOV Oracle, close `M1-MD-020`,
`M1-TF-063`, or `M1-TF-064`, or provide product compatibility evidence.

The stable parent watchdog uses an authoritative Unix `prlimit` address-space
limit, a two-second wall deadline with kill and reap, and `/proc` peak-RSS
sampling. Windows stable qualification records the absence of an address-space
limit; Windows Job Object enforcement is deferred to the release-platform
qualification matrix and is not claimed by CORE-009.
