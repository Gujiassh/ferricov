# LCOV 2.5 environment contract

This directory owns the standalone, fail-closed inventory of environment
interactions and configuration discovery behavior in the pinned LCOV 2.5
Oracle. It does not change the public compatibility inventory schema and does
not claim Ferricov product compatibility.

The canonical [`v2.5.json`](v2.5.json) snapshot records:

- 19 named environment variables read or written by installed runtime and
  support code;
- one dynamic `$ENV{NAME}` configuration expansion input;
- five reviewed configuration discovery paths;
- all 36 source lines containing direct environment interaction syntax under
  `bin/`, `lib/`, and `scripts/`;
- 22 bindings to retained Oracle configuration cases where runtime evidence
  already exists.

Every source reference includes exact pinned source text. Validation rejects
source-line drift, incomplete environment-use coverage, renamed or reordered
entries, discovery precedence drift, unknown Oracle case bindings, and any
product-evidence claim.

Generate the canonical snapshot from the pinned upstream checkout:

```sh
python3 compat/environment/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference \
  --write
```

Verify committed bytes and run mutation guards:

```sh
python3 compat/environment/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
LCOV_SOURCE_ROOT=/home/cc/code1/lcov-upstream-reference \
  python3 -m unittest compat/environment/test_contract.py
```

The aggregate `product_compatibility_evidence` value and every entry-level
`product_evidence` array remain empty until Ferricov itself passes equivalent
differential cases.
