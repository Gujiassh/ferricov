# M0 Installation Contract Review

## Decision

The standalone LCOV 2.5 installation-layout and report-asset inventory is
acceptable as an M0 planning contract. It binds pinned source and retained
Oracle artifacts only. It does not make any of the 13 installation cases
executable, authorize packaging or uninstall behavior, qualify report assets,
or provide Ferricov product compatibility evidence.

## Classification

- Review class: `Critical`
- Reason: installation paths, modes, fixups, partial failure, uninstall, and
  licensing affect executable identity, runtime discovery, host filesystem
  safety, and distribution obligations. Report assets encode user-visible
  output and links.
- Product code changed: no
- Persisted or public data contract changed: no; the contract records the
  pinned Oracle without changing Ferricov output, package, Suite, or Result
  schemas.

## Semantic Oracle

The review uses these verifiable invariants:

1. The retained installed-tree lock contains exactly 321 unique entries with
   SHA-256 `75edeea2799a5f13715df5dd119bc10614ee347aa5fc33e37fbeb21cafd8fd24`.
   Paths are canonical, lexicographically ordered, absolute, rooted under
   `/usr/local`, and contain no parent traversal; every file identity is a
   lowercase 64-character SHA-256.
2. The tree contains 320 files and one exact `/usr/local/man -> share/man`
   symlink; mode counts remain 210 at `0644`, 110 at `0755`, and one at `0777`.
3. Every entry belongs to exactly one of nine ordered groups: 10 commands, 1
   config, 1 library, 10 manpages, 23 support scripts, 60 HTML files, 10
   examples, 205 tests, and 1 legacy symlink.
4. The tree recorder retains only files and symlinks. The contract keeps
   `directory_entries_retained=false` rather than inventing directory evidence.
5. Fifteen pinned source closures retain 600 exact source lines covering install
   variables, documentation prerequisites, payload loops, uninstall, fixups,
   config discovery, installed tests, documented paths, and report-asset
   writers.
6. All nine layout identities and ten failure/divergence identities remain in
   exact reviewed order.
7. All 13 `INST-*` acceptance identities remain `planned` with no product
   evidence.
8. The four retained `genhtml` report samples contain the same seven assets:
   `gcov.css`, `ruby.png`, `amber.png`, `emerald.png`, `snow.png`, `glass.png`,
   and `updown.png`, with exact byte counts and hashes. Every output tree is
   bound to its retained `sample.json` path, byte count, and SHA-256; duplicate
   runtime asset paths are rejected.
9. The Oracle manifest remains `observed` with evidence scope
   `environment_smoke`; the benchmark result remains `baseline_only` with both
   correctness and performance gates `not_evaluated`.
10. Root product compatibility remains false and all retained asset
    observations remain `oracle_reference` only.

## Evidence

Commands executed:

```sh
python3 compat/installation/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference --write
python3 compat/installation/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/installation/test_contract.py
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current
python3 compat/verify.py --skip-oracle
python3 -m py_compile \
  compat/installation/contract.py compat/installation/test_contract.py
python3 -m json.tool compat/schema/installation-contract.schema.json
python3 -m json.tool compat/installation/v2.5.json
```

Observed results:

- contract generation and committed-byte comparison: pass;
- generated contract SHA-256:
  `7fe1f263301abe0328964cb20bd026746d4491b1db7f31011efa3896b5c3e4e2`;
- installed tree: 321 canonical ordered entries in 9 exhaustive groups;
- installed kinds: 320 SHA-256-identified files and 1 exact symlink;
- retained artifact bindings: 11, including four output trees and their four
  sample metadata records;
- source closure: 15 ranges and 600 lines;
- layout and failure identities: 9 and 10 respectively;
- planned installation identities: 13 of 13, all `planned`;
- runtime report assets: 7 exact identities across 4 retained samples;
- test suite: 22 of 22 pass, including 21 reverse mutations;
- behavior generation and current validation: pass with 462 explicit primary
  planning gaps unchanged;
- repository verifier without Docker: pass;
- product compatibility evidence: false.

## Reverse Review

The mutation suite proves rejection of:

- an unsorted installed-tree path sequence;
- a path outside `/usr/local`;
- parent traversal in an installed path;
- a non-SHA-256 file identity;
- legacy man symlink target drift;
- a missing installed-tree group;
- a tree-group count change;
- source-closure hash drift;
- installed-tree manifest hash drift;
- a false claim that directory entries were retained;
- a missing planned installation case;
- a duplicate runtime asset path;
- a mismatched sample-to-output-tree binding;
- a missing runtime asset;
- a runtime-asset identity change;
- retained sample-metadata binding drift;
- retained asset-observation artifact drift;
- removal of a known evidence gap;
- product-evidence injection;
- promotion of the baseline-only benchmark to an evaluated correctness gate; and
- promotion of an Oracle reference to product status.

The generator also hard-binds eleven retained artifacts, the pinned upstream
commit, every group closure, the Oracle manifest scope, and committed generated
bytes. Reverse review assumes a package or report regression occurred: source,
tree, mode, asset, or status drift would be rejected, while unobserved directory
and lifecycle behavior remains visibly blocked instead of passing by omission.

## Review Areas

| Area | Status | Judgment |
| --- | --- | --- |
| Goal alignment | pass | Closes the M0 installation-layout and asset-planning inventory only. |
| User-visible flow and timing | not applicable | No Ferricov install or report runtime exists in this slice. |
| Architecture boundaries | pass | Oracle installation evidence, future packaging, report rendering, and product evidence remain separate. |
| Data contracts and types | pass | The schema is standalone; public inventory, Suite, Result, and tracefile contracts are unchanged. |
| Save or persistence semantics | not applicable | No product persistence or output behavior changed. |
| Filesystem safety | blocked | Destructive uninstall, partial install, foreign sentinels, and path variants have planned identities but no executable evidence. |
| Distribution and licensing | blocked | The install payload omits `COPYING`; Ferricov package licensing remains a future release gate. |
| Report assets | pass | Seven retained Oracle identities are exact, while variant and HTML-reference qualification remains explicitly open. |
| Tests | pass | Twenty-one reverse mutations, schema validation, source closure, artifact binding, and byte stability pass. |
| Documentation and SSoT | pass | README, changelog, compatibility SSoT, plan, tasks, and normative installation specification are synchronized. |
| M1 authorization | blocked | Other M0 model, tracefile, fuzz, resource, benchmark, and go/no-go gates remain open. |
| Product compatibility | blocked | No Ferricov installer, package, report renderer, or differential product evidence exists. |

## Residual Risk

The lock excludes directory paths, directory modes, ownership, timestamps, and
install-time failure state. The four report samples cover one default benchmark
shape and do not qualify optional `updown` behavior, external CSS, hierarchical
or flat reports, HTML references, or platform differences. Staging, fixups,
configuration discovery, installed tests, uninstall safety, dirty input,
partial failure, documentation failure, and licensing all still require exact
Oracle and Ferricov execution before any compatibility claim.
