# M1-CORE-003 Progress — Function / Branch / MC/DC Invariants

Status: **IMPLEMENTED**  
Date: 2026-08-18  
Package: `ferricov-model`  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `ea23e4e`)  
Scope: `crates/model` + this progress review doc only

## Acceptance

Agent-spec CORE-003: *Alias indexes, ranges, representative selection, ordered
branch blocks, exclusions, MC/DC senses, group identity, and reverse-index
coherence.*

| Requirement | Status |
| --- | --- |
| `FunctionTable` dual indexes (start → group, alias → group) kept coherent | Done |
| `FunctionGroup` start / optional end / aliases / representative / totals | Done |
| Representative = shortest after lambda penalty; equal length → lexical | Done |
| Group found/hit + alias found/hit views | Done |
| Repeated alias counts add; zero start / end-before-start representable | Done |
| `assert_indexes_coherent()` for tests / debug | Done |
| Hierarchical `BranchCoverage` with model-order blocks, kind-only signature | Done |
| `derived_index == position`; excluded edges retained; `-` ≠ evaluated `0` | Done |
| Hierarchical `McdcCoverage` with `GroupSizeKey`, dual senses, sticky exclusion | Done |
| At most one group per size key; stored_position order retained | Done |
| Empty-capable API preserved for CORE-002 store tests | Done |
| No algebra (CORE-004), no writer renumbering, no product evidence flip | Done |

## Delivered types

| Type | Module | Role |
| --- | --- | --- |
| `FunctionGroup` | `function.rs` | Start, optional end, alias→count, representative, hit/total helpers |
| `FunctionTable` | `function.rs` | Coherent `by_start` + `by_alias` indexes; found/hit views |
| `FunctionError` | `function.rs` | Alias start conflict / orphan / incoherent / count-add errors |
| `BranchKind` | `branch_store.rs` | Vanilla / Exception / Fallthrough (`b`/`e`/`f`) |
| `BranchEdge` | `branch_store.rs` | derived_index, taken, expression, kind, excluded |
| `BranchBlock` | `branch_store.rs` | model_position, signature, edges; append rebuilds signature |
| `BranchLine` | `branch_store.rs` | `blocks_in_model_order` sequence |
| `BranchCoverage` | `branch_store.rs` | `LineKey → BranchLine`; invariant assert |
| `GroupSizeKey` | `mcdc.rs` | `NumericAtom` newtype (not plain `u64`) |
| `SenseCoverage` | `mcdc.rs` | count + sticky excluded |
| `McdcExpression` | `mcdc.rs` | stored_position, declared_index, expression, both senses |
| `McdcLine` | `mcdc.rs` | at most one vector per `GroupSizeKey` |
| `McdcCoverage` | `mcdc.rs` | `LineKey → McdcLine` |

## Module layout

Replaced CORE-002 stubs in place:

- `crates/model/src/function.rs`
- `crates/model/src/branch_store.rs`
- `crates/model/src/mcdc.rs`
- `crates/model/src/lib.rs` (re-exports)
- `crates/model/src/stores.rs` (minimal smoke-test API adaptation)

`numeric.rs` was not grown.

## Tests

Command: `cargo test -p ferricov-model`  
Result: **39 passed** (prior 31 + 8 CORE-003 focused tests).

Focused CORE-003 coverage:

1. Function: aliases at same start → one group; reverse alias index coherent
2. Function: representative shortest + lexical + lambda penalty; found/hit views
3. Function: repeated alias counts add; zero start / end-before-start representable
4. Branch: append edges builds signature from kinds; `derived_index == position`
5. Branch: excluded edge retained; `NeverEvaluated` distinct from evaluated `0`
6. MC/DC: both senses present; sticky exclusion; one group per size key
7. MC/DC: expression `stored_position` order retained (declared-index gaps ok)
8. Function: mutations keep alias→group and start→group consistent (conflict path)

CORE-002 store independence tests still pass against the empty-capable API.

## Design choices

1. **Lambda penalty implemented from Oracle** (`FunctionEntry::addAlias`):
   names matching `{lambda(` or `.lambda$` get `+1000` effective length during
   representative selection on insert. Documented via `is_lambda_alias` /
   `effective_alias_length`. Removal recomputation without lexical tie-break
   remains deferred to `M1-ALG-FUNCTION-REP-001` / CORE-004.
2. **`FunctionTable::insert_alias` compatibility**: still empty-capable for
   CORE-002 smoke tests; places the alias at start `"0"` (explicitly
   representable). Real callers should use `insert_alias_at`.
3. **Branch signature is kinds only**; expressions live on edges and do not
   participate in compatibility identity. Input block token is not stored —
   only contiguous `model_position`.
4. **`GroupSizeKey` wraps `NumericAtom`**, matching `LineKey` style so group
   size is never a plain `u64`.
5. **Sticky exclusion** on `SenseCoverage::set` / `BranchEdge::set_excluded`:
   set-only, never clears — matching `MCDC_Expression::set`.
6. **No algebra yet**: structures are merge-ready (ordered maps / vectors /
   signatures) but union/intersect/diff are CORE-004.

## Explicit deferrals

- CORE-004: ordered union / intersection / difference
- Function representative recomputation after removal (hash-seed / no lexical
  tie-break path in Oracle `removeAliases`)
- Alias move to smallest start on ignored inconsistent-data continuation
- Branch writer renumbering / canonical signature sort (CORE-007)
- MC/DC asymmetric vector merge / difference (`M1-ALG-MCDC-*`)
- Purpose-specific totals caches beyond the views already exposed
- Parser / writer / CLI / product evidence

## Residual risks

1. `insert_alias` at start `"0"` is a CORE-002 compatibility shim — parsers must
   use `insert_alias_at` with real locations.
2. End-line “greatest accepted end” compare is a best-effort decimal/lexical
   helper, not full Oracle ignored-error diagnostics (writer owns those).
3. Branch `push_taken_on_line` always appends to the last block; real parser
   transition state (new block on line/input-block change) is CORE-005/006.
4. MC/DC `declared_index` gaps are retained but not validated against Oracle
   contiguous-index warnings yet.

## Non-claims

- Does not implement CORE-004 algebra
- Does not flip `product_compatibility_evidence`
- Does not commit or push
- Does not grow `numeric.rs`
- Does not copy Perl object layout
