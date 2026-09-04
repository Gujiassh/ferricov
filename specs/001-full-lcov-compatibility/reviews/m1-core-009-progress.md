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

## Critical Rework

The first Critical audit rejected determinism-only assertions and silent budget
skips. Rework now adds exact accepted-input, numeric, round-trip, ordered
algebra, testcase-map, index-coherence, inverse-corruption, unequal MC/DC, and
writer-not-invoked assertions. Budget violations are typed failures; the stable
campaign is ignored in the ordinary suite and invoked by CI under a subprocess
deadline and RSS cap. Corpus and failure metadata now have fail-closed machine
validation, mutation tests, fixed seeds, and raw/minimized provenance hashes.

## Verification

- model tests: 48 passed;
- tracefile tests: 71 passed, one watchdog-only campaign ignored in the normal run;
- watchdog campaign replay: 1 passed;
- workspace Clippy with `-D warnings`: passed;
- all nine fuzz binaries: stable compile check passed;
- hosted nightly fuzz smoke remains required before controller acceptance.
