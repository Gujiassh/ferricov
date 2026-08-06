# LCOV 2.5 Coverage-Model Algebra Contract

This directory contains the standalone, fail-closed M0 Oracle coverage-model
algebra and property evidence contract for pinned LCOV v2.5. It does not
implement a Ferricov coverage model or provide product-compatibility evidence.

The generated contract freezes:

- seven Oracle-bound model rows: `M1-MD-010`..`M1-MD-014`, `M1-MD-017`, and
  `M1-MD-019`;
- blocked adversarial-fuzz identities `M1-MD-020`, `M1-TF-063`, and
  `M1-TF-064` with `fuzz_execution_phase=M1-only`;
- 27 committed algebra fixtures under
  `compat/fixtures/m0-algebra/fixtures/`;
- 157 executable Oracle cases and matching raw baseline observations;
- independent expected facts that bind image, program, argv, fixture, stream,
  output, and exit identities without self-hash-only acceptance; and
- intentional hard-error semantics for asymmetric MC/DC vector algebra
  (`md013-mcdc-vector` long-then-short union/intersect).

Corpus ownership lives in `compat/fixtures/m0-algebra/`. The executable catalog
is retained at `compat/model/m1-model.json` and is intentionally not a
differential suite document.

Validate the committed contract:

```sh
python3 compat/model/contract.py
python3 -m unittest compat/model/test_contract.py
python3 compat/fixtures/m0-algebra/validate.py
python3 -m unittest compat/fixtures/m0-algebra/test_validate.py
```

Regenerate after an intentional reviewed contract change:

```sh
python3 compat/fixtures/m0-algebra/generate.py --write-repo
# recapture Oracle baseline only against the pinned image when needed
python3 compat/fixtures/m0-algebra/capture_oracle.py
python3 compat/model/contract.py --write
```

`product_compatibility_evidence` remains false. Rust parser/model work remains
blocked for this lane.
