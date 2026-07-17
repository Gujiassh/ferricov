# Ferricov Development Rules

- Read `docs/ssot/project.md`, `docs/ssot/compatibility-contract.md`, and
  `docs/ssot/performance-contract.md` before changing behavior.
- Treat upstream LCOV `v2.5` at commit
  `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` as the behavioral Oracle.
- Do not mark a public surface compatible without differential evidence.
- Correctness is a prerequisite for performance comparison. Never trade
  coverage meaning, exit behavior, or report integrity for speed.
- Every behavior change requires focused tests and an updated compatibility
  matrix entry.
- Keep the coverage model independent of CLI, filesystem, subprocess, and
  report-rendering concerns.
- Do not copy Perl implementation structure into Rust. Reproduce observable
  behavior behind Rust-native module boundaries.
- Write every commit message in English.
- Write all repository documentation in English, including README files,
  specifications, ADRs, SSoT documents, compatibility reports, benchmark
  reports, issue templates, and pull request text.
