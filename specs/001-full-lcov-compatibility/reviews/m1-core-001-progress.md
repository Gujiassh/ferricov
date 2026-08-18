# M1-CORE-001 Progress — Model Primitives

Status: **IMPLEMENTED (controller-reviewed)**  
Date: 2026-08-18  
Package: `ferricov-model`  
Branch tip base: `4268d84` + this work

## Delivered types

| Type | Module | Role |
| --- | --- | --- |
| `ByteString` | `bytes.rs` | Opaque byte identity; no UTF-8 requirement; explicit display |
| `SourceLookupKey` | `identity.rs` | Case-sensitive or ASCII-folded lookup key |
| `SourceIdentity` | `identity.rs` | Lookup vs display path (+ optional diagnostic path) |
| `TestName` | `identity.rs` | Byte testcase identity; unsanitized provenance optional/non-semantic |
| `NumericAtom` | `numeric.rs` | Raw lexeme + class/kind/signed-zero tags; no f64-first coerce |
| `CoverageCount` | `numeric.rs` | validate / add / is_zero / is_positive / compare_threshold |
| `BranchTaken` | `branch.rs` | `NeverEvaluated` (`-`) vs `Evaluated(CoverageCount)` + merge rules |

## Tests

Command: `cargo test -p ferricov-model`  
Result: **21 passed**

Coverage includes: arbitrary/invalid UTF-8 bytes, lookup≠display, empty/` ,diff` test names, NaN/Inf/non-numeric classification, signed zero, excessive/invalid validate, large-integer add without precision loss, NeverEvaluated≠0 and merge identity/replace.

## Explicit deferrals (not CORE-001 scope)

- Full Perl SV promotion / scientific-form arithmetic beyond simple decimal add
- Store/algebra/parser/writer (CORE-002+)
- Fuzz / product limits / product evidence (still matrix-excluded)

## Residual risks

1. `numeric.rs` decimal add/compare is a minimal ASCII decimal engine — enough for CORE-001 invariants, not a claim of full Perl numeric parity.
2. Case-insensitive source folding is ASCII-only by design (Unicode folding banned until Oracle proof).
3. `ByteString: Display` is lossy by design; callers must not use it as identity.

## Non-claims

- Does not close signed N/A / FERRICOV / MD-020·TF-063·064
- Does not set `product_compatibility_evidence=true`
- Does not authorize CORE-009/011
