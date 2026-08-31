# M1-CORE-004 Progress — Ordered Algebra

Status: **IMPLEMENTED (structural APIs + unit tests; ALG Oracle binding deferred)**  
Date: 2026-08-18  
Package: `ferricov-model`  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `41a6146`)  
Scope: `crates/model` + this progress review doc only  
Commit/push: **not performed** (per task)

## Acceptance

Agent-spec CORE-004: *Union, intersection, difference, and operand-order
behavior for line, function, branch, MC/DC, and testcase stores using the exact
algebra fixtures.*

This slice delivers **structural ordered algebra APIs** with unit tests that
encode coverage-model rules. Exact ALG Oracle fixture binding (CLI/semantic
runners against `compat/fixtures/m0-algebra/`) remains for later differential
lanes; residuals below name which rows still need binding.

| Requirement | Status |
| --- | --- |
| Prefer new `algebra.rs` (do not dump into `numeric.rs`) | Done |
| `LineCoverage` union / intersect (add, not min) / difference (remove keys) | Done |
| `FunctionTable` union (left-biased range) / intersect / difference; indexes coherent | Done |
| Defined post-removal representative; document `M1-ALG-FUNCTION-REP-001` residual | Done |
| `BranchCoverage` structural nth-signature union / intersect / difference | Done |
| Do **not** fake `U-BRANCH-INTERSECT` / `M1-ALG-BRANCH-CACHE-001` as done | Done (deferred) |
| `McdcCoverage` sense add + sticky exclusion; right-only group copy; whole-line diff | Done |
| Asymmetric longer-left vector → fail-closed `Result` (not panic); document vs Oracle die | Done |
| Thin `CoverageStore` / `TestcaseStores` wrappers with documented testcase semantics | Done |
| Focused unit tests (required 1–8) + prior 39 still pass | Done (48 total) |
| No product evidence flip / no CLI / no commit / no push | Done |

## Delivered APIs

| Surface | Module | Ops |
| --- | --- | --- |
| `LineCoverage::{union,intersect,difference,apply_op}` | `algebra.rs` | Ordered map algebra |
| `FunctionTable::{union,intersect,difference,apply_op}` | `algebra.rs` | Start-keyed merge; coherent indexes |
| `FunctionGroup::{remove_alias,recompute_representative_after_removal}` | `function.rs` | Defined survivor selection |
| `FunctionTable::{remove_alias,remove_group,insert_group,...}` | `function.rs` | Algebra support |
| `BranchCoverage::{union,intersect,difference,apply_op}` | `algebra.rs` | Signature + nth occurrence |
| `McdcCoverage::{union,intersect,difference,apply_op}` | `algebra.rs` | Group/sense merge; whole-line diff |
| `CoverageStore::{union,intersect,difference,apply_op}` | `algebra.rs` | Per-family wrapper |
| `TestcaseStores::{union,intersect,difference,apply_op}` | `algebra.rs` | Per-`TestName` family maps |
| `AlgebraOp` / `AlgebraError` | `algebra.rs` | Op enum + fail-closed errors |

## What matches coverage-model / Oracle fixtures (unit-encoded)

Verified against model text and md010–md013 CLI snapshots as **behavioral
oracles for unit assertions** (not yet wired as differential product evidence):

1. **Line (md010 small-int subset):** union copies right-only + adds common;
   intersection keeps common and **adds** (not min); difference removes common
   keys; `A ∖ B ≠ B ∖ A`.
2. **Function (md011):** union merges aliases at start 10 with left end retained
   (`20` not `99`); intersect keeps common aliases with summed counts;
   difference removes common aliases and drops empty groups.
3. **Branch (md012 structural):** nth repeated-signature matching on union;
   left expression retained; `-` + evaluated merge; sticky exclusion from right;
   difference removes only the leading matched occurrence.
4. **MC/DC (md013 structural):** both-sense count add; sticky exclusion OR;
   right-only group copied on union; difference removes entire left line when
   right has that line.
5. **Operand order:** function union range bias `A∪B` vs `B∪A` differs; line
   difference non-commutative.

## Intentionally deferred ALG / MD rows

| Row | Residual | CORE-004 stance |
| --- | --- | --- |
| `M1-ALG-FUNCTION-REP-001` | Oracle `removeAliases` equal-length survivor can follow hash seed / non-lexical order | Ferricov uses **defined** shortest-then-lexical recompute after removal; document quirk, do not claim Oracle parity |
| `M1-ALG-BRANCH-CACHE-001` | Intersection may retain unmatched left block when no matched merge reports `changed` | Conventional intersect **drops** unmatched left occurrences; residual marked — **not** faked as done |
| `M1-ALG-MCDC-VECTOR-001` | Longer-left vector can Oracle-`die`; reverse can succeed | Ferricov returns `AlgebraError::McdcAsymmetricVector` (fail-closed `Result`); shorter-left ignores extra right exprs during merge |
| `M1-ALG-MCDC-EXPR-001` | Expression mismatch reports inconsistent data; continuation may suppress right-only group copy | Unit path leaves left vector unchanged and skips right-only copy on mismatch; full diagnostic/continuation policy unbound |
| `M1-MD-014` / testcase ALG rows | Exact left-only retention vs lazy empty right-only maps | Documented choice: union inserts right-only; intersect/diff mutate common names only and **retain left-only**; do **not** invent empty right-only maps until MD-014 pins |
| Exact fixture differential | `compat/fixtures/m0-algebra/` CLI/semantic runners | Structural APIs ready; product evidence must stay false until CORE-010-style binding |

## Tests

Command: `cargo test -p ferricov-model`  
Result: **48 passed** (prior 39 + 9 CORE-004 focused tests).

Focused CORE-004 coverage:

1. Line union / intersect (non-min) / diff + operand-order difference
2. Function union merges aliases; left-biased range; indexes coherent
3. Function difference removes aliases / drops empty groups; defined rep
4. Branch signature nth-occurrence matching on union (+ difference leading match)
5. MC/DC both-sense add + sticky exclusion on merge (+ right-only group copy)
6. MC/DC difference removes whole line
7. Operand order: function union range bias `A op B` vs `B op A`
8. Prior 39 tests still pass (extra: asymmetric MC/DC Result + CoverageStore smoke)

## Design choices

1. **`algebra.rs` is the sole home** for family ops; `numeric.rs` untouched.
2. **Mutating-left / ordered** APIs: `&mut self` + `&right`, matching model
   “ordered, mutating-left” description.
3. **Function post-removal representative** is shortest-effective-length then
   lexical — stable and tested; Oracle hash-seed path deferred.
4. **Branch intersection** is conventional pairable-prefix retention; cache
   quirk explicitly residual.
5. **MC/DC asymmetric length** is fail-closed `Result` rather than panic or
   inventing padding; documents Oracle-die vs Ferricov-Result choice.
6. **TestcaseStores** semantics are documented above pending `M1-MD-014`.

## Residual risks

1. Exact ALG fixture differential not yet executed in-process against sealed
   Oracle baselines — unit tests encode model rules, not byte-identical CLI
   output (totals/FNF/BRF/writer renumbering belong to later CORE tasks).
2. Function intersect rebuilds groups and recomputes representative among
   survivors; if Oracle retains a pre-intersect representative when it still
   survives, behavior should match; if not, bind via `M1-ALG-FUNCTION-REP-001`.
3. Branch edge length mismatch on equal signatures is not expected (signature
   is kinds-only); extra right edges are ignored.
4. Expression-mismatch MC/DC continuation is minimal (keep left, skip
   right-only copy) without emitting Oracle diagnostics.
5. `CoverageStore`/`TestcaseStores` wrappers do not yet touch version/checksum
   overlay or source-level algebra (`U-FILE-ALGEBRA`).

## Non-claims

- Does not flip `product_compatibility_evidence`
- Does not implement CLI / parser / writer / CORE-005+
- Does not claim `M1-ALG-BRANCH-CACHE-001` or `M1-ALG-FUNCTION-REP-001` Oracle parity
- Does not commit or push
- Does not grow `numeric.rs`
