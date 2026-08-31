# M1-CORE-008 Controller Critical Review

Status: **ACCEPTED — independent Critical audit at `11d4d1d`**
Risk: **Critical**

## Semantic Oracle

Semantic equality compares only the complete semantic model. Evidence equality
separately compares parser/run facts. No diagnostic, raw provenance, policy,
transport buffer, output bytes, or serializability fact silently changes model
semantic equality.

Serializability is fail-closed in two stages. First, a declarative contract table
classifies model shape and retained close lifecycle before any writer call;
non-serializable and repeated-close/Oracle-unknown states skip the writer. Second,
provisional serializable states require clean full-parser acceptance, exact
semantic equality, and byte-identical second-write fixed point. The first output
bytes remain explicit evidence even when a post-write check fails.

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Semantic/evidence schema split | pass | distinct public snapshot types |
| Aggregate/testcase/empty identity | pass | structural database equality and inverse classification tests |
| Writer reachability | pass | empty sources, orphan checksums, and disabled empty-family keys pre-rejected |
| Index/order/totals/numeric bytes | pass | database internals plus reverse tests |
| Diagnostic/provenance envelope | pass | source plus current/active/open/testcase `TN` provenance |
| Streaming in-flight state | pass | splitter buffer and pending CR captured |
| Process ownership | pass | optional explicit process evidence; capture leaves it `None` |
| Output classification | pass | contract pre-gate → write → clean parse → semantic compare → fixed point |
| Product evidence | pass | unchanged and false |
| Focused gates | pass | tracefile 61, model 48, workspace check, diff check |
| Hosted gates | residual | unchanged Windows/Docker limitations |

## Reverse Review

The diagnosed/clean pair must be semantic-equal and evidence-unequal. Partial
`TN:x` feed must be semantic-equal to untouched, evidence-unequal through the
splitter buffer, then finish deterministically. Two `SourceIdentity` values with
different diagnostic paths remain semantically equal while source provenance is
unequal; active and open `SourceBinding` provenance is retained independently.

Classification tests reject before canonical writing:
aggregate/testcase divergence, populated function-family presence without line
membership, lazy empty family state, observable totals, and late-`TN` MC/DC.
Repeated close reaches `BlockedOracleUnknown` and has no attempted output.
Repeated empty sections do not set populated-close history and therefore do not
produce a false lifecycle blocker. Context-disabled function, branch, and MC/DC
families reject key presence even for explicit empty values; disabled checksum output rejects stored checksums; empty sources and
checksums without an emitted `DA` line are likewise rejected before writing.
Provisional post-write semantic rejection retains its exact attempted bytes;
absent branch expressions remain typed writer failures with no bytes.

## Residual Risk

This is a stable Rust schema, not a persisted JSON/public wire contract. A future
artifact encoder must preserve the schema split and cannot substitute debug text.
## Independent Audit Result

The independent Critical audit accepted M1-CORE-008 at `11d4d1d`. The final
focused gates are `cargo test -p ferricov-tracefile` with 61 passing tests and
`cargo test -p ferricov-model` with 48 passing tests. Workspace check and diff
check also pass; product compatibility evidence remains false.
