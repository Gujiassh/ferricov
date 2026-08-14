# M0 Residual Lane C — S2 Critical Audit

Status: **ACCEPT** (controller Critical audit; independent explore auditor failed with host serialization error — re-verified in controller)

## Scope

| Field | Value |
| --- | --- |
| Worktree | `/home/cc/code1/ferricov-m0-lane-C` |
| Branch | `m0-residual/lane-C-filters` @ `ce0eb80` |
| Baseline | `346f86f` |
| Targets | `lcovrc.filter-bitwise-conditional`, `lcovrc.filter-blank-aggressive`, `lcovrc.filter-lookahead` |

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Goal (M0 planning only) | **pass** | `product_compatibility_evidence=false`; `evidence_status=planned` |
| Ownership | **pass** | diff only fixture/suite/authored wave/review; no pin/contract/repair |
| Target set exact | **pass** | fragment has exactly 3 primary ids |
| Substantive plans | **pass** | reviewed + planned + suite_cases non-empty |
| Oracle image | **pass** | `sha256:b02cc645…56eb80b7` |
| Control/variant delta | **pass** | all 3 variants `file_tree_sha256 != control`, exit 0 |
| Unit tests | **pass** | 5/5 unittest OK; static suite gate OK |
| Inventory source refs | **pass** | kind/path/line match inventory sets |
| Hollow close | **pass** | real out.info tree deltas under `lcov --filter branch,blank` |

## Residual risks (accepted)

1. **Hand-crafted `edges.info`** seals filter application heuristics, not gcov capture provenance. Acceptable for these lcovrc filter keys; document in merge review.
2. Absolute `SF:/work/src/edges.c` bake-in — re-seal must use `/work` mount.
3. Host case ids still in `m0-lcovrc-wave1-repair-a.json` until S3 strip.

## Merge queue

**GO for S3** (serial merge after other lanes as controller schedules).

Do not merge until controller runs full strip+generate+pin protocol.
