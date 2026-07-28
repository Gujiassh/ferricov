# CLI Parser Policy Equivalence

This document summarizes machine-verified parser-policy partitions. The
canonical per-case links, exact policy objects, hashes, and environment
profiles are in `case-contract.json`. These partitions cover parser
mechanics only; they do not claim command-behavior or Ferricov parity.

## Shared Getopt Long

- ID: `parser-policy.shared-getopt-long`
- Commands: `lcov`, `genhtml`, `geninfo`, `perl2lcov`, `llvm2lcov`
- Canonical policy SHA-256: `26ac25c7dac0359084cb11f3a0a3dd10db46a2d49107c3edfb4f318c9ba627ee`

## Direct Getopt Long

- ID: `parser-policy.direct-getopt-long`
- Commands: `genpng`, `gendesc`
- Canonical policy SHA-256: `dd9e1edc2b323ec3b0d25c90f61f9622c8a582ea4dfdfb4bbd9dd28a9ecc47eb`

## Argparse

- ID: `parser-policy.argparse`
- Commands: `py2lcov`, `xml2lcov`
- Canonical policy SHA-256: `4ccaf6b0ed51445bbb2aeed9e43b04043c9ef14a360473d7036327b1222b5a2f`

## None

- ID: `parser-policy.none`
- Commands: `xml2lcovutil.py`
- Canonical policy SHA-256: `62760830e20084142626efd1584533a402d45c638332d093ced35f0248c3d712`

## Evidence Boundary

The suites and links are a static executable contract. The raw Oracle
correctness observations are retained under `compat/correctness/` and
validated separately. They describe the pinned reference only and do not
provide Ferricov product compatibility evidence.
