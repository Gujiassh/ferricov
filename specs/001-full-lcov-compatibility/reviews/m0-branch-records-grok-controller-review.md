# Historical snapshot: counts below describe the branch-records lane before the numeric/error expansion.

# Controller Review: Grok 4.5 Branch-Record Slice

## Findings

1. **P1 (resolved): the first expression-mismatch probe did not prove
   `M1-TF-025` expression independence.** The two `BRDA` lines used one input
   block token but were assigned different branch positions by the pinned
   reader, so no `BranchElement::merge` occurred. Sol's independent review
   caught this before acceptance. The controller retained the original case as
   a positional-expression parse probe and added two same-source, same-test,
   same-block inputs with distinct expressions. The new two-input canonical and
   semantic cases now prove positional merge, left-expression retention, and
   count addition.

2. **P1 (process, resolved): the initial delegated report omitted required
   repository and Rust gates.** The controller ran the gates independently;
   they pass. A delegated report is not an acceptance artifact unless it names
   the commands and results.

3. **P2 (process, resolved): the first implementation left retained resource
   source-position metadata stale after grammar growth.** The controller
   regenerated the resource contract and result binding. The final tracefile
   source section is `tracefile-grammar.md:806-834`, and the contract/result
   hashes now match.

4. **P2 (process, resolved): the delegated session wrote outside the repository
   boundary and left an unused `/home/cc/.pi-subagents` artifact directory.
   The external directory was moved to the system trash; the repository has no
   `.pi-subagents` directory. Future lanes must treat the repository boundary
   as hard and either use or discard orchestration artifacts immediately.

5. **P2 (verification, resolved): the first validator did not assert the
   aggregate/testcase line caches and testcase branch cache for the merge
   snapshot, and the new mutation test was initially outside CI.** Sol found
   the gap. The controller added eight single-field mutation checks, wired the
   focused test into `.github/workflows/ci.yml` and `compat/verify.py`, and
   reran the automatic gates.

## Scope And Ownership

The assignment was Oracle evidence only. No Rust parser, model, product crate,
product evidence, commit, or push was added. The final working tree contains
branch/function fixtures, capture and inspection plumbing, generated contracts
and baselines, focused validators/tests, and synchronized English SSoT/spec
material.

The requested Grok 4.5 lane produced the broad initial branch-record slice.
The Grok 4.5 runtime was unavailable for the expression-merge rework, so the
controller completed that bounded repair. Terra's supplementary review covered
most branch boundaries but did not detect the false expression-identity proof;
Sol's independent review found that P1 and then the validator-cache P2. The
controller returned both findings to the implementation/verification lane and
closed them with evidence. This sequence is recorded as a delegation quality
result, not hidden behind the final green tests.

## Acceptance Matrix

| Review area | Status | Evidence |
| --- | --- | --- |
| Goal alignment | pass | M0 LCOV 2.5 Oracle evidence only; no M1 implementation or product claim. |
| `M1-TF-013` BRDA forms | pass | Vanilla, exception, fallthrough, `U`/`fU`/`eU`, dash taken, numeric/comma expressions, no-final-comma, empty-taken, empty-expression, diagnostics, and both unreachable modes are retained. |
| `M1-TF-025` branch identity | pass | Two inputs merge through `TraceFile::merge_tracefile` and `TraceInfo::UNION`; left `left`/`left_else` expressions remain, counts become `3/3`, aggregate cache is `found=2/hit=1`, and writer totals are `BRF:2`/`BRH:2`. |
| Oracle identity | pass | LCOV v2.5 commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, immutable image and executable identities remain pinned. |
| Evidence closure | pass | 65 fixtures, 109 cases/observations, 63 default parses, 31 canonical rewrites, 8 recovery cases, and 7 semantic snapshots; manifest/cases/baseline/inspector hashes are bound. |
| Validator regression coverage | pass | Aggregate line, testcase line, and testcase branch cache assertions are covered by 8 single-field mutations; the focused test is run by CI and `compat/verify.py`. |
| Old observation preservation | pass | `prior-84`: common 84, changed 0, removed 0, added 25; `prior-101`: common 101, changed 0, removed 0, added 8; HEAD 63: common 63, changed 0, removed 0, added 46. Common case JSON plus stdout/stderr/output identities are byte-equal. |
| Resource synchronization | pass | Contract `eec94e282d93a6dcee237b34cf014d16a1301b6b839396c8f1a7d565e3e8e387`; retained result `9b8dde867e810cf56f8a5b2e338a3aa5998d7c0f7c34e116b7fca143b3a6484f`; 13/13 accepted samples unchanged. |
| Product compatibility | pass | `product_compatibility_evidence=false` across tracefile, diagnostics, resources, behavior, and correctness artifacts. |
| M1 readiness | blocked | 19 planned M1 tracefile IDs remain unmapped; Ferricov product evidence is empty. |

## Verification

The controller and Sol independently reproduced these checks:

- `python3 compat/fixtures/m0-tracefiles/validate.py` -> 65 fixtures and
  pinned baseline validated.
- `python3 -m unittest compat/fixtures/m0-tracefiles/test_validate.py` -> 2/2,
  including 8 single-field cache-drift mutations.
- `python3 compat/tracefile/contract.py` -> 20 records, 15 reader lines, 18
  writer lines, 65 fixtures, 21 malformed fixtures, 109 cases.
- `python3 -m unittest compat/tracefile/test_contract.py` -> 18/18.
- `python3 compat/diagnostics/contract.py` and `python3 -m unittest
  compat/diagnostics/test_contract.py` -> 68 observations and 13/13.
- `python3 compat/resources/contract.py`, static/result validation, and
  `python3 -m unittest compat/resources/test_contract.py
  compat/resources/test_exercise.py` -> 53/53, 13/13 accepted.
- `python3 -m unittest compat/behavior/test_validate.py` -> 44/44;
  current behavior validation -> 531 public, 531 plans, 107 reviewed,
  424 gaps.
- Correctness validation and tests -> 148 baseline cases, 16/16 tests.
- `python3 compat/verify.py --skip-oracle` -> exit 0, including the focused
  semantic mutation test; `python3 -m unittest compat/test_verify.py` -> 7/7.
- CI YAML parse and `git diff --check` -> pass.
- `cargo +1.85.0 fmt --all --check`, `check --workspace --all-targets
  --locked`, `test --workspace --all-targets --locked` -> 106 Rust tests,
  and `clippy ... -D warnings` -> pass.
- `PERL5LIB=/home/cc/code1/lcov-upstream-reference/lib perl -c
  compat/fixtures/m0-tracefiles/inspect_model.pl` -> syntax OK; Python
  `compileall` -> pass. The script emits a non-fatal missing `get_version.sh`
  shell warning during module loading.

## Residual Risks

- These are pinned Oracle observations, not Ferricov parser parity or a release
  claim. M1 remains explicitly blocked.
- `generate.py` is now 1,813 lines and has several fixture-family
  responsibilities. It remains readable enough for this bounded lane, but the
  next evidence expansion should split generator definitions by record family
  before the file crosses the repository's 2,000-line review threshold.
- Resource and behavior unittest modules must continue to run in separate
  Python processes because their top-level `generate` imports can collide when
  loaded into one process. This is a test invocation constraint, not a lane
  semantic defect.

## Controller Decision

**Accepted as an M0 Oracle-evidence slice after controller rework, Sol findings,
and automatic-gate repair.** This accepts the evidence artifact and its
contracts, not the first Grok report and not Ferricov product compatibility.
No commit or push was performed.
