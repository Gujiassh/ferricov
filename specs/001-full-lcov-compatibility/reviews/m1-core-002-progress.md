# M1-CORE-002 Progress — Coverage Stores

Status: **IMPLEMENTED (controller-reviewed)**  
Date: 2026-08-18  
Package: `ferricov-model`  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `37044b1`+)  
Scope: `crates/model` only

## Acceptance

Agent-spec CORE-002: *Independent aggregate plus line/function/branch/MC/DC
testcase-family maps, including explicit empty values and observable totals.*

| Requirement | Status |
| --- | --- |
| Aggregate and four testcase-family maps are independent first-class stores | Done |
| Explicit empty family values remain representable (map presence) | Done |
| Four family key sets independently representable | Done |
| `observable_totals` distinct `TotalState` (opaque/cache holder) | Done |
| `LineKey` retains zero / ignored-error states (not plain `u64`) | Done |
| Function/Branch/MC/DC CORE-003 invariants deferred and stubbed | Done |
| No filesystem / CLI / product evidence flip / Perl layout copy | Done |

## Delivered types

| Type | Module | Role |
| --- | --- | --- |
| `LineKey` | `keys.rs` | `NumericAtom` newtype; `from_lexeme` retains zero/ignored states; `try_canonical_positive` for canonical path |
| `LineCoverage` | `line.rs` | Empty-capable `LineKey → CoverageCount` map |
| `FunctionTable` | `function.rs` | Minimal empty-capable stub; TODO(CORE-003) alias indexes |
| `BranchCoverage` | `branch_store.rs` | Minimal empty-capable stub; TODO(CORE-003) ordered blocks |
| `McdcCoverage` | `mcdc.rs` | Minimal empty-capable stub; TODO(CORE-003) senses/groups |
| `CoverageStore` | `stores.rs` | Aggregate four-family container |
| `TestcaseStores` | `stores.rs` | Four independent `map<TestName, *>` family maps |
| `TotalState` | `stores.rs` | Opaque observable-totals holder; Oracle-exact semantics deferred |
| `SourceCoverage` | `stores.rs` | identity / version / checksums / aggregate / testcases / observable_totals |
| `CoverageDatabase` | `stores.rs` | `map<SourceLookupKey, SourceCoverage>` |

## Module layout

Kept `numeric.rs` untouched (already ~850 lines). New modules:

- `keys.rs`, `line.rs`, `function.rs`, `branch_store.rs`, `mcdc.rs`, `stores.rs`
- `lib.rs` re-exports CORE-001 + CORE-002 public types

## Tests

Command: `cargo test -p ferricov-model`  
Result: **31 passed** (`cargo test -p ferricov-model`, including CORE-001 + CORE-002).

Focused CORE-002 unit coverage added for:

1. Aggregate vs testcase independence (mutate one, other unchanged)
2. Explicit empty `LineCoverage` inserted for a `TestName` remains present
3. Four family maps with different key sets on the same source
4. `CoverageDatabase` keyed by `SourceLookupKey` (case-sensitive vs ASCII fold)
5. `observable_totals` set/get/clear without deriving from points
6. `LineKey` zero / retained / canonical-positive constructor paths
7. `CoverageStore` family independence smoke
8. Empty `LineCoverage` + zero `LineKey` insert smoke in `line.rs`

## Design choices

1. **`LineKey` wraps `NumericAtom`**, not `u64` / `CoverageCount`. Parser path
   retains any lexeme; canonical path rejects non-positive integer-like spellings.
2. **`BTreeMap`** for ordered, deterministic store iteration without HashMap
   seed dependence. `LineKey: Ord` orders by retained lexeme bytes (numeric
   writer sort remains later work).
3. **`TotalState` is opaque** (`Option<ByteString>` payload). Documented that
   Oracle-exact cache/lifecycle semantics are deferred; field exists so totals
   are not conflated with recomputed point views.
4. **Function / Branch / MC/DC are empty-capable stubs** with explicit
   `TODO(CORE-003)` — no alias indexes, block signatures, or sense pairs yet.
5. **No lazy derivation** between aggregate and testcase stores; both are owned
   fields on `SourceCoverage`.

## Explicit deferrals (not CORE-002 scope)

- CORE-003: function alias indexes, branch ordered blocks, MC/DC senses/groups
- CORE-004: union / intersection / difference algebra
- Found/hit derivation caches beyond opaque `TotalState`
- Parser / writer / filesystem / CLI
- Product compatibility evidence (`product_compatibility_evidence` remains false)

## Residual risks

1. Stub containers may need reshaping when CORE-003 invariants land (especially
   `FunctionTable` dual indexes and branch hierarchical identity).
2. `LineKey` map order is lexeme-byte order, not Oracle numeric sort — writer
   must not assume current `BTreeMap` iteration equals canonical output order.
3. `TotalState` opacity means no executable Oracle total semantics yet; later
   cases may require a richer typed cache or prove the field removable.
4. ~~Tests pending~~ — controller confirmed 31 passed.

## Non-claims

- Does not implement CORE-003+ invariants or algebra
- Does not close signed N/A / FERRICOV / MD-020·TF-063·064
- Does not set `product_compatibility_evidence=true`
- Does not authorize CORE-009/011
- Does not commit or push
