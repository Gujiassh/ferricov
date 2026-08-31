# M1-CORE-009 Progress

Status: **implementation complete — Critical review pending**  
Branch: `feat/m1-core-009-properties-fuzzing`  
Product compatibility evidence: **false**

## Implemented

- Seven stable deterministic property identities execute on Rust stable,
  including fixed-point, accepted-input determinism, numeric lexeme sequences,
  ordered/safe algebra, index coherence, and fail-closed nonserializability.
- Nine named `cargo-fuzz`/libFuzzer entry points share one safe, bounded harness.
- Stable seed derivation is SHA-256 domain separation with the first eight
  bytes interpreted big-endian. Stable CI property generation uses 64 cases
  per target and is replayable.
- CI-smoke checks fail closed above 1 MiB input, 256 KiB logical fields, 65,536
  records/sections/family members, or two seconds per case. Hosted fuzzing also
  applies 512 MiB RSS and 60-second per-target process limits.
- The canonical authored seed is retained for all targets. The corpus README
  specifies same-cap `tmin`, uninstrumented replay, required sidecar evidence,
  and permanent retention for bug-derived minimized inputs.

## Boundary

This work does not execute Ferricov-vs-Oracle differential cases, select
product resource limits, or close `M1-MD-020`, `M1-TF-063`, or `M1-TF-064`.
CORE-010 and CORE-011 remain unauthorized.

## Verification

Final local fmt/check/test/clippy and hosted nightly fuzz smoke results are to
be recorded by the controller after review.
