# M1-CORE-008 Controller Critical Review Draft

Status: **DRAFT — independent Critical re-review required**
Risk: **Critical**

## Semantic Oracle

Semantic equality compares only the complete semantic model. Evidence equality
separately compares parser/run facts. No diagnostic, raw provenance, policy,
transport buffer, output bytes, or serializability fact silently changes model
semantic equality.

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Semantic/evidence schema split | pass | distinct public snapshot types |
| Aggregate/testcase/empty identity | pass | structural database equality |
| Index/order/totals/numeric bytes | pass | database internals plus reverse tests |
| Diagnostic/provenance envelope | pass | parser state plus explicit source provenance |
| Streaming in-flight state | pass | splitter buffer and pending CR captured |
| Process ownership | pass | optional explicit process evidence; capture None |
| Output classification | pass | canonical bytes or typed error in evidence only |
| Product evidence | pass | unchanged and false |
| Focused gates | pass | tracefile 53, model 48, workspace check |
| Hosted gates | residual | unchanged Windows/Docker limitations |

## Reverse Review

The diagnosed/clean pair must be semantic-equal and evidence-unequal. Partial
`TN:x` feed must be semantic-equal to untouched, evidence-unequal through the
splitter buffer, then finish deterministically. Two SourceIdentity values with
different diagnostic paths remain semantically equal while SourceProvenance is
unequal. Signed-zero, family/index, and serializability mutations remain unequal
on the appropriate layer.

## Residual Risk

This is a stable Rust schema, not a persisted JSON/public wire contract. A future
artifact encoder must preserve the schema split and cannot substitute debug text.
