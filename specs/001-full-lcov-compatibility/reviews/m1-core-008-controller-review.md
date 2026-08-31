# M1-CORE-008 Controller Critical Review Draft

Status: **DRAFT — independent Critical re-review required**
Risk: **Critical**

## Semantic Oracle

Semantic equality compares only the complete semantic model. Evidence equality
separately compares parser/run facts. No diagnostic, raw provenance, policy,
transport buffer, output bytes, or serializability fact silently changes model
semantic equality.

Serializability is fail-closed: canonical writer success is followed by parsing
the canonical bytes into a fresh database and comparing the reconstructed model
with the original semantic snapshot. Only an equal reconstruction is
`Serializable`; writer errors and round-trip semantic mismatch are distinct typed
non-serializable reasons. `BlockedOracleUnknown` is a separate representable
contract-corpus outcome and is never guessed from a decided round trip.

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Semantic/evidence schema split | pass | distinct public snapshot types |
| Aggregate/testcase/empty identity | pass | structural database equality and inverse classification tests |
| Index/order/totals/numeric bytes | pass | database internals plus reverse tests |
| Diagnostic/provenance envelope | pass | parser state plus database, active-binding, and open-binding provenance |
| Streaming in-flight state | pass | splitter buffer and pending CR captured |
| Process ownership | pass | optional explicit process evidence; capture leaves it `None` |
| Output classification | pass | write → parse → semantic compare; typed writer/mismatch outcomes |
| Product evidence | pass | unchanged and false |
| Focused gates | pass | tracefile 55, model 48, workspace check, diff check |
| Hosted gates | residual | unchanged Windows/Docker limitations |

## Reverse Review

The diagnosed/clean pair must be semantic-equal and evidence-unequal. Partial
`TN:x` feed must be semantic-equal to untouched, evidence-unequal through the
splitter buffer, then finish deterministically. Two `SourceIdentity` values with
different diagnostic paths remain semantically equal while source provenance is
unequal; active and open `SourceBinding` provenance is retained independently.

Classification tests force semantic losses after successful canonical writing:
aggregate/testcase divergence, populated function-family presence without line
membership, lazy empty family state, observable totals, and late-`TN` MC/DC must report
`RoundTripSemanticMismatch`. The repeated-close lifecycle fixture must be decided
by the same round-trip comparison and is serializable only when reconstruction is
actually equal. Absent branch expressions remain typed writer failures.

## Residual Risk

This is a stable Rust schema, not a persisted JSON/public wire contract. A future
artifact encoder must preserve the schema split and cannot substitute debug text.
Independent Critical re-review remains required before task acceptance or push.
