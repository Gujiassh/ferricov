# LCOV 2.5 Installation And Asset Contract

This directory contains the standalone, fail-closed M0 contract for the
installed LCOV 2.5 layout and report assets. It records the pinned Oracle tree,
the Makefile/source closure, the planned installation case identities, and
retained report-asset observations. It does not implement installation,
packaging, report rendering, or Ferricov product compatibility.

The retained tree contains 321 file or symlink entries from the pinned Oracle:
320 SHA-256-identified files and one legacy `/usr/local/man -> share/man`
symlink. Paths must be canonical, lexicographically ordered, absolute, and under
`/usr/local`. Directory entries are not retained by the upstream manifest
script and remain an explicit evidence gap. The four report samples retain the
same seven generated assets; each output tree is bound through its sample
metadata and duplicate asset paths are rejected. This is Oracle evidence only;
no product evidence is present.

Validate against a clean pinned checkout:

```sh
python3 compat/installation/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/installation/test_contract.py
```

Regenerate only after an intentional reviewed contract change:

```sh
python3 compat/installation/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference \
  --write
```
