# M0 Installation Wave-1 Review Note

## Scope

Lane-local wave-1 implementation for installation layout and report-asset Oracle
evidence. This note covers only:

- `compat/installation/**`
- `compat/schema/installation-contract.schema.json`
- this review note

Shared `tasks.md`, root README, SSoT docs, crates, tracefile, diagnostics, and
behavior surfaces were intentionally not edited in this lane.

## Decision

Accept as a bounded M0 Oracle-reference batch:

- all 13 planned `INST-*` identities now have exact independent-fact case
  records in `compat/installation/oracle-case-records.json`;
- records remain `evidence_status=oracle_reference` and
  `execution_status=planned`;
- four retained report samples continue to bind the same seven runtime assets;
- root `product_compatibility_evidence` remains false;
- no Ferricov installer, packaging, uninstall, or report renderer was
  implemented.

This is not product compatibility and does not authorize M1 or M5 installation
claims.

## Classification

- Review class: `Critical`
- Product code changed: no
- Public Suite/Result/tracefile contracts changed: no
- Installation contract shape extended with closed Oracle case-record bindings

## Semantic Oracle

1. Installed-tree lock remains 321 ordered `/usr/local` entries with SHA-256
   `75edeea2799a5f13715df5dd119bc10614ee347aa5fc33e37fbeb21cafd8fd24`.
2. Nine exhaustive groups, 15 source closures, and mode counts remain fixed.
3. All 13 case IDs remain ordered and present:
   `INST-LAYOUT-001` through `INST-LICENSE-001`.
4. Case-record artifact SHA-256 is
   `e2c3de1c85574c5b524fa2ccf9b36cd94b4e19f73f6cab67d593654fa9699932`.
5. Each case binds independent facts through a type-sensitive facts hash; hash
   refresh alone without matching trusted bytes is rejected.
6. Case independent facts are regenerated from pinned upstream source closures
   and installed-tree partition evidence, then compared field-by-field with
   type-sensitive equality. Nested source digests, layout names, report
   artifact paths/hashes, sample metadata, and observation IDs cannot drift
   under refreshed self-hashes.
7. `INST-REPORT-ASSET-001` binds four sample observations and seven asset
   identities with exact bytes and SHA-256 digests.
8. Case records cannot claim product evidence or captured execution.
9. Known evidence gaps now explicitly include executable install/uninstall
   lifecycle capture for the 13 INST cases.

## Evidence

Commands:

```sh
export LCOV_SOURCE_ROOT=/home/cc/code1/lcov-upstream-reference
python3 compat/installation/contract.py --upstream-root "$LCOV_SOURCE_ROOT" --write
python3 compat/installation/contract.py --upstream-root "$LCOV_SOURCE_ROOT"
python3 -m unittest compat.installation.test_contract -v
python3 compat/verify.py --skip-oracle
git diff --check
```

Observed:

- installation contract generation/validation: pass;
- unittest: 38 pass, including reverse mutations for case-record binding,
  facts-hash drift, order drift, execution promotion, product evidence,
  type-sensitive JSON equality, and fail-closed independent-facts rebinding
  after self-hash refresh;
- product compatibility evidence: false.

## Fail-Closed Semantic Binding Repair

Independent review rejected self-hash-only case-record acceptance. This lane
now regenerates expected case records from pinned upstream closures and the
installed-tree lock, then compares every retained case against that independent
oracle:

1. `oracle-case-records.schema.json` closes `independent_facts` per family with
   `additionalProperties: false` and exact nested shapes for source bindings and
   report observations.
2. `contract.py` rebuilds expected source bindings, layout partition facts,
   failure claims, report artifact paths/hashes/sample metadata, and
   observation IDs from pinned inputs before accepting retained records.
3. Reverse mutations that refresh `facts_sha256` / case-records SHA-256 after
   changing nested source digests, report `artifact_path`, layout
   `support_script_names`, or report observation mapping all reject.

Statuses remain `execution_status=planned`, `evidence_status=oracle_reference`,
and root `product_compatibility_evidence=false`.

## Residual Risk

- No executable install/uninstall/config-discovery lifecycle capture yet.
- Directory entries/modes remain unobserved by the tree recorder.
- Report samples cover one default genhtml shape; optional updown, external CSS,
  hierarchical/flat reports, and HTML-reference checks remain open.
- Packaging, license distribution policy, and platform path variants still need
  exact runtime Oracle and future product evidence before any compatibility
  claim.
