# M0 Tracefile Contract Review

## Decision

The standalone LCOV 2.5 tracefile record and malformed-input inventory is
acceptable as an M0 contract. It is an Oracle-source and retained-evidence
contract only. It does not authorize M1 implementation, mark a planned M1 case
as passing, or provide Ferricov product compatibility evidence.

## Classification

- Review class: `Critical`
- Reason: tracefile syntax and malformed-input behavior define coverage data
  meaning, failure semantics, and the future parser/writer boundary.
- Product code changed: no
- Persisted or public data contract changed: no; the contract records the
  pinned upstream Oracle without changing Ferricov save or output semantics.

## Semantic Oracle

The review uses these verifiable invariants:

1. The pinned reader recognizes exactly 20 known record tags plus comment and
   blank lexical rules in the reviewed matcher scope.
2. Every one of the 15 reader matcher source lines is bound to exact text at
   LCOV commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.
3. Every one of the 18 canonical writer emission lines is bound: 17 record
   tags plus the explicit comment emission path.
4. `KF`, `FN`, and `FNDA` are accepted reader-only forms and are never promoted
   to canonical writer output.
5. Each known tag has one per-record malformed fixture; the unknown-record
   fallback supplies the twenty-first malformed fixture.
6. All 39 fixtures and all 59 Oracle observations retain their exact identities,
   exits, stdout hashes, stderr hashes, and optional output hashes.
7. All observations remain `oracle_reference`; root product compatibility is
   false and entry product-evidence arrays are empty.
8. The contract does not claim to resolve the 25 planned M1 tracefile IDs that
   still lack exact executable mappings.

## Evidence

The initial source audit found 15 reader matcher lines. The writer audit first
used an incorrect manual count of 19; direct source closure corrected this to
18 before the contract was accepted. The final total is 17 record emissions
plus one comment emission.

Commands executed:

```sh
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference --write
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/tracefile/test_contract.py
python3 compat/verify.py --skip-oracle
python3 -m py_compile \
  compat/tracefile/contract.py compat/tracefile/test_contract.py
python3 -m json.tool compat/schema/tracefile-contract.schema.json
python3 -m json.tool compat/tracefile/v2.5.json
```

Observed results:

- contract generation and committed-byte comparison: pass;
- record totals: 20;
- reader matcher source closure: 15 of 15;
- writer emission source closure: 18 of 18;
- fixture bindings: 39 of 39;
- per-record malformed fixture bindings: 21 of 21;
- Oracle case bindings: 59 of 59;
- Oracle exit distribution: 40 zero, 19 nonzero;
- mutation tests: 11 of 11 pass;
- retained tracefile corpus validation: 39 fixtures and pinned baseline pass;
- repository verifier without Docker: pass;
- full repository verifier: clean upstream checkout, source closure, and the first
  no-cache Oracle build passed; the second no-cache build was blocked by an
  external `snapshot.debian.org:443` timeout before the tracefile contract was
  rechecked;
- hosted CI remains the final unchanged two-build Oracle gate; no mirror
  fallback or verification weakening was introduced;
- product compatibility evidence: false.

## Reverse Review

The mutation suite proves rejection of:

- a missing record;
- an uncovered reader matcher;
- changed pinned source text;
- a writer/non-writer classification change;
- a missing malformed fixture;
- a record-to-malformed-fixture target swap;
- same-count Oracle stdout identity swaps;
- retained artifact hash drift;
- product-evidence injection; and
- promotion of an Oracle reference to a product status.

The contract also hard-binds the corpus manifest, case manifest, and Oracle
baseline SHA-256 values. A regenerated contract cannot silently absorb a
changed retained baseline without an explicit reviewed source change.

## Review Areas

| Area | Status | Judgment |
| --- | --- | --- |
| Goal alignment | pass | Closes only the M0 record/malformed inventory item. |
| User-visible timing | not applicable | No runtime product path exists. |
| Architecture boundaries | pass | Source inventory, schema, evidence, and future parser implementation remain separate. |
| Data contracts and types | pass | Existing public inventory and Suite schemas are unchanged. |
| Save or persistence semantics | not applicable | No Ferricov persistence path changed. |
| Failure behavior | pass | Default parse, canonical rewrite, and ignore-recovery identities remain bound to raw Oracle evidence. |
| Tests | pass | Eleven reverse mutations plus corpus and repository validation pass. |
| Documentation and SSoT | pass | README, changelog, compatibility SSoT, plan, tasks, and grammar status are synchronized. |
| M1 authorization | blocked | Twenty-five planned tracefile IDs and model-shaping decisions still lack executable mappings. |
| Product compatibility | blocked | No candidate parser exists and all product evidence remains empty. |

## Residual Risk

The retained corpus is representative, not the complete M1 executable
manifest. It does not yet capture all state/order, checksum, converter,
transport, resource, or semantic snapshot decisions listed in
`tracefile-grammar.md` and `coverage-model.md`. The next tracefile-related work
must add exact executable mappings rather than interpreting this inventory as
M1 readiness.
