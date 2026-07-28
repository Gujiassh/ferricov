# Upstream Test Map

`upstream-test-map.json` maps every tracked file under the LCOV v2.5
`tests/` tree to a public behavior driver, internal test infrastructure, or a
supporting fixture. The source is pinned to upstream commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.

The map distinguishes direct public evidence from indirect internal-module
evidence. A mapping does not by itself establish Ferricov compatibility; it
only identifies the behavior family for future differential cases.
`review_status: reviewed` means the file's classification, owner, behavior
group, and concrete upstream consumer evidence were reviewed; it does not claim
that every fixture byte was manually inspected or that Ferricov already passes
the behavior. Every reviewed fixture records sorted `tests/...:line`
`consumer_evidence`, which the validator resolves against the pinned tracked
test tree and checks for an in-range line number.

Regenerate the map from the clean pinned checkout:

```sh
python3 compat/inventory/tests/generate.py \
  --upstream-root /path/to/lcov-v2.5
```

Validate the schema-specific invariants, commit and tree identity, exact
205-file set, per-file hashes, totals, references, source and key ordering,
and deterministic regeneration:

```sh
python3 compat/inventory/tests/validate.py \
  --upstream-root /path/to/lcov-v2.5
```

The validator uses the same `jsonschema` dependency as `compat/verify.py` and
rejects a substituted schema by content hash.

Do not infer an owner from a similar path. The pinned map requires all 205 files
to be reviewed; a future unresolved mapping must stay explicitly `unreviewed`
with no owner or consumer evidence until its concrete consumer is verified.
