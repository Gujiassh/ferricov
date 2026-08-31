# M1-CORE-008 Controller Critical Review Draft

Status: **DRAFT — independent Critical review required**
Risk: **Critical**

## Semantic Oracle

Two snapshots are equal only when committed and in-flight semantic state,
identity/provenance, diagnostics/policy, all aggregate/testcase family stores,
indexes/order/totals, and canonical bytes or typed nonserializability are equal.

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Model/tracefile boundary | pass | snapshot lives in tracefile, model stays pure |
| Aggregate/testcase independence | pass | full database structural equality |
| Empty/lazy family identity | pass | map presence retained |
| Index/order/totals | pass | internal structures included; reverse tests |
| Numeric/arbitrary bytes | pass | signed-zero, NaN/Inf, invalid UTF-8 |
| Provenance/diagnostics | pass | parser state, open section, policy, stopped |
| Output classification | pass | bytes or typed BranchExpressionAbsent |
| Product evidence | pass | unchanged and false |
| Focused Rust gates | pass | tracefile 51; model 48; workspace check |
| Hosted Oracle/Python/fmt/clippy | residual | pre-existing host limitations |

## Reverse Review

Assume two similar states were collapsed. The signed-zero, diagnostic-only,
family/index/order, arbitrary-byte, and absent-expression tests each mutate one
semantic axis and require inequality. Assume output classification drifted: the
numeric-expression/absent-expression pair requires distinct serializability.

## Residual Risk

The snapshot is a stable Rust representation, not a new persisted JSON/public
wire contract. A future differential artifact encoder must preserve every field
rather than replacing this equality with debug text or normalized JSON.

