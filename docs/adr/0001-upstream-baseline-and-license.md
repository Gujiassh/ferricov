# ADR 0001: Upstream Baseline And License

## Status

Accepted on 2026-07-17.

## Decision

Ferricov targets LCOV `v2.5` at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` and uses
`GPL-2.0-or-later`, matching the licensing option stated in upstream source
headers.

The upstream executable is the behavioral Oracle. Upstream source and tests
may be studied and adapted under their license, with attribution retained
where material is reused. The Rust architecture will follow domain boundaries
rather than transliterating Perl modules.

## Consequences

- Compatibility claims refer to an immutable target.
- New upstream releases are handled as explicit compatibility deltas.
- Distributed binaries and source remain under GPL-2.0-or-later.
- Reused upstream fixtures or assets must preserve applicable notices.
