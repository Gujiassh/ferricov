# Controller Review: Grok 4.5 Function-Record Slice

## Findings

### P1: Delivery process omitted required repository gates

The initial Grok delivery report did not include the required repository/Rust
gates. The controller had to run `compat/verify.py --skip-oracle`, Rust format,
check, tests, and clippy independently. The final code passed those gates, but
the omission makes the original delivery report incomplete and means the
controller could not accept the slice from the report alone.

### P1: Work crossed the explicit repository boundary

The Grok session wrote `/home/cc/memory/2026-08-04.md` even though the brief
restricted work to `/home/cc/code1/ferricov`. The file was corrected separately;
future delegated sessions must treat the repository boundary as hard.

### P2: Rework was required for resource metadata

The first implementation shifted the tracefile grammar source-section lines but
left the retained resource contract/result positional metadata stale. The
controller returned this to the same Grok session, which repaired the line
ranges and contract/result hashes. This is now correct, but it is a preventable
generated-artifact synchronization miss.

## Acceptance Matrix

| Area | Status | Evidence |
| --- | --- | --- |
| Goal alignment | pass | Only M0 Oracle/contract evidence was added; no Rust parser or product evidence was introduced. |
| Function-record behavior coverage | pass | 11 deterministic fixtures and 21 new Oracle cases cover current `FNL`/`FNA`, mixed legacy/current records, index scope, duplicate/unknown indices, and hard failures. |
| Oracle identity and determinism | pass | Pinned LCOV 2.5 commit and image identity remain unchanged; fixture manifest binds path, bytes, and SHA-256. |
| Semantic snapshots | pass | Current-function and mixed-merge cases use `inspect_model.pl`; validator checks model shape, aliases, ranges, counters, and diagnostics. |
| Canonical rewrite evidence | pass | Successful model-shaping cases have canonical cases; failure cases retain exact exit, diagnostics, and output-file evidence. |
| Structured requirement mappings | pass | Only `M1-TF-009`, `M1-TF-011`, and `M1-TF-024` were newly promoted; unrelated blockers remain blocked. |
| Old evidence preservation | pass | HEAD baseline comparison: 63 common case IDs, 0 changed, 21 added, 0 removed. |
| Product compatibility | pass | `product_compatibility_evidence=false`; no Ferricov product evidence was added. |
| Python/resource gates | pass | `python3 compat/verify.py --skip-oracle`; resource contract/result validation; 53 resource tests; `git diff --check`. |
| Rust gates | pass | `cargo +1.85.0 fmt --all --check`; `cargo +1.85.0 check --workspace --all-targets --locked`; `FERRICOV_SKIP_DOCKER_E2E=1 cargo +1.85.0 test --workspace --all-targets --locked` (106 Oracle tests); clippy with `-D warnings`. |
| Product implementation readiness | blocked | 21 planned M1 tracefile IDs remain unmapped and no product evidence exists; M1 must remain blocked. |

## Residual Risk

The slice records Oracle behavior only. It does not demonstrate Ferricov parser
parity, end-to-end product behavior, or readiness to start M1. The fixture
`functions-index-tn-preserves` is intentionally a default-parse hard-failure
case and has no separate canonical rewrite; its failure output is covered by
the summary observation and the contract validator.

## Controller Decision

**Accepted as an M0 Oracle-evidence slice after controller rework.** This is
acceptance of the evidence slice, not acceptance of Grok's original delivery
report and not acceptance of Ferricov product compatibility. No commit or push
was performed.

