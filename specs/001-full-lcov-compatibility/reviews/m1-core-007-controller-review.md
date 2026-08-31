# M1-CORE-007 Controller Critical Review

Status: **ACCEPTED**
Accepted implementation: `6f04f44`
Risk: **Critical**

## Semantic Oracle

Identical model/context/provider results produce identical bytes. Projected
source bytes and testcase bytes determine section order. Only line-testcase
membership creates sections. U-WRITE family/field order is exact, summaries are
recomputed, legacy/permissive syntax is omitted, and the model is unchanged.

## Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Goal and architecture | pass | pure tracefile projection, no filesystem/CLI |
| Projected source/test ordering | pass | inverse-order regression |
| Family and numeric ordering | pass | exact mixed and large-number tests |
| Branch/MC/DC ordering | pass | multi-block and lexical-group regressions |
| Checksums/comments | pass | stored precedence, provider fill, disabled mode |
| Round-trip/nonmutation | pass | fixed point plus deep equality |
| Focused Rust gates | pass | tracefile 47, model 48, workspace check |
| Workspace fmt/clippy | nonblocking host residual | pre-existing unrelated failures |
| Python contracts | nonblocking host residual | missing `jsonschema`; Windows CRLF drift |
| Docker Oracle | nonblocking host residual | Docker unavailable; retained Oracle contract used |
| Product evidence | pass | remains false |

## Reverse Review

Exact-byte assertions catch family/order/index/summary drift. Inverse projection
catches lookup-key ordering. Stored/provider tests catch precedence and path/line
arguments. Deep equality catches mutation. Fixed-point output catches numeric
branch-expression invention and other canonical semantic drift.

## Residual Risk

Filesystem-backed provider implementations still need runtime Oracle tests.
Broader parser CORE-006 malformed/ignore residuals constrain corpus-wide parity,
but are not hidden by this writer review.

Typed serialization failure for absent branch expressions is intentional: the numeric fallback would collapse a genuine numeric expression. CORE-008 owns classification of accepted but nonserializable states.

## Reviewer Outcome

The independent Critical reviewer accepted M1-CORE-007 at 6f04f44. The typed failure for absent branch expressions preserves semantic identity and correctly leaves classification to M1-CORE-008. No finding remains open against this slice; host-only fmt/clippy/Python/Docker limitations are recorded as nonblocking residual verification gaps and do not create product evidence.
