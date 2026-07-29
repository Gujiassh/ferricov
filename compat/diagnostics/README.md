# LCOV 2.5 Diagnostics Contract

This directory contains the standalone, fail-closed M0 inventory of LCOV 2.5
diagnostic classes, error-control rules, unclassified failure surfaces, and
command exit policies. It does not implement Ferricov runtime behavior or
provide product-compatibility evidence.

The generated contract freezes:

- all 32 ordered, case-insensitive shared message classes;
- the complete symbol-reference closure under `bin/`, `lib/`, and `scripts/`;
- the reserved `branch` class, which has no production emitter at the pinned
  commit;
- ignore-list precedence, repeated-name counts, keep-going, warning promotion,
  suppression, summary, and command exit-folding controls;
- parser, raw Perl, native Python, and early dependency failure surfaces;
- all 71 planned diagnostic and parallel case identities; and
- 51 bindings to retained raw Oracle observations.

The retained observations are references only. In particular, the retained
`geninfo` startup case is classified as an environment intercept because its
read-only execution environment prevents temporary-file creation before the
true no-argument path. Missing ignore-two, promotion, converter, and parallel
evidence remains explicit in the generated contract.

Validate against a clean pinned upstream checkout:

```sh
python3 compat/diagnostics/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/diagnostics/test_contract.py
```

Regenerate only after an intentional reviewed contract change:

```sh
python3 compat/diagnostics/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference \
  --write
```
