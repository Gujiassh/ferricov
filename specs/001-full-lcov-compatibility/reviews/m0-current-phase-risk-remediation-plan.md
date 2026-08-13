# M0 Current-Phase Risk Remediation Plan

## Status

Implemented on the active M0 branch after independent audit (Accept with fixes).
This plan does **not** authorize M1 product implementation, does **not** claim
Ferricov product compatibility, and does **not** close remaining public-entry
planning gaps by inventing behavior.

## Scope Boundary

In scope: structural, documentation, hygiene, and verification-integrity risks
that currently threaten M0 completion quality.

Out of scope:

- implementing `crates/{model,tracefile,ops,report,cli}` product logic;
- claiming compatibility for any public surface;
- closing the remaining 88 unreviewed primary public entries without real
  Oracle planning work;
- force-deleting remote branches or rewriting published history.

## Truth Source For Metrics

Live `compat/behavior/contract.json` totals on the active branch:

| Metric | Value |
| --- | ---: |
| public inventory entries | 531 |
| reviewed primary coverage | 443 |
| uncovered public entries / unreviewed case groups | 88 |
| interaction domains reviewed | 4 / 4 |
| product compatibility evidence | false |

Any document that still reports `440 / 91` or similar is stale.

## Risk Register

### R1 — SSoT metric drift (Severity: High)

**Symptom.** `docs/ssot/project.md` reports 443 reviewed / 88 gaps, while
`docs/ssot/compatibility-contract.md` still reports 440 / 91. Workbench
`next_step` text may lag either number.

**Why it matters.** M0 readiness is numeric. Drift makes agents and humans
re-plan the wrong residual surface and can hide or invent gaps.

**Fix.**

1. Treat `compat/behavior/contract.json` → `totals` as the only live metric
   source for reviewed/uncovered primary coverage.
2. Correct stale prose in `docs/ssot/compatibility-contract.md` and any other
   checked-in status prose that disagrees with those totals.
3. Add a small verifier that fails when selected status documents still contain
   obsolete hard-coded residual counts that disagree with `contract.json`
   totals, or prefer generating a machine-readable status snapshot and making
   docs cite it.
4. Keep definitional compatibility rules in SSoT; do not leave live counters as
   free-hand prose without a check.

**Acceptance.**

- Documented residual metrics match `contract.json` totals exactly.
- A local command fails if the known stale pair (`440` reviewed with `91` gaps)
  reappears, or if a generated status snapshot disagrees with totals.
- `product_compatibility_evidence` remains false.

### R2 — Operational status mixed into stable SSoT (Severity: Medium)

**Symptom.** `docs/ssot/project.md` and parts of
`docs/ssot/compatibility-contract.md` mix immutable project law with wave-by-wave
M0 progress journals.

**Why it matters.** Stable contracts become unreviewable changelogs. Agents
treat journal lines as architecture law.

**Fix.**

1. Add `docs/ssot/m0-status.snapshot.json` containing only operational metrics
   and blocker IDs derived from live contracts.
2. Slim the live-counter paragraphs in `project.md` / compatibility inventory
   table cells to short citations of that snapshot plus stable rules.
3. Leave historical wave detail in `specs/.../tasks.md`, `CHANGELOG.md`, and
   review files.

**Acceptance.**

- Stable SSoT still defines objective, baseline, architecture, and comparison
  law.
- Live residual counts appear once in the snapshot (or an equivalent single
  generated status surface) and are referenced, not triplicated with divergent
  numbers.

### R3 — Oracle harness concentration risk (Severity: Medium, pre-M1)

**Symptom.** `compat/oracle/src/differential.rs` (~1873 LOC) and
`differential/process.rs` (~1505 LOC) still concentrate suite loading, identity,
process isolation, comparison, and evidence persistence. SSoT already requires
a split before M1 domain differentials land.

**Why it matters.** M1 will add tracefile/model differentials. Leaving the
monolith forces more logic into the same files and raises regression risk.

**Fix.**

Mechanical, behavior-preserving module split under `compat/oracle/src/differential/`:

| Module | Responsibility |
| --- | --- |
| types / existing public types | suite/case/launcher enums and structs |
| suite | load/validate suite and launcher documents |
| compare | dimension comparison and normalizer application |
| evidence | already exists; keep persistence only |
| process | already exists; keep execution/identity/timeout only |
| runner | orchestration entrypoints currently on `DifferentialRunner` |

Rules:

- no behavior change;
- no public CLI flag change;
- keep `pub use` surface stable from `ferricov_oracle` if currently exported;
- run the existing Rust workspace tests and `python3 compat/verify.py --skip-oracle`
  smoke after the split.

**Acceptance.**

- No file under `compat/oracle/src/differential*.rs` remains above 1000 lines
  without an explicit documented exception.
- `cargo test --workspace --all-targets --locked` with
  `FERRICOV_SKIP_DOCKER_E2E=1` passes.
- No product crate gains implementation code.

### R4 — Inventory pin dual-source risk in `compat/verify.py` (Severity: Medium)

**Symptom.** `EXPECTED_COMMANDS`, policy families, positionals, and generated
token tables are hand-maintained constants. Inventory generation is separate.

**Why it matters.** A regenerated inventory can pass schema checks while verify
still asserts obsolete pins, or the reverse if constants are updated first.

**Fix options ranked:**

1. **Preferred for this phase:** keep fail-closed pins, but load them from a
   committed pin file generated by the inventory tool
   (`compat/inventory/expected-pins.v2.5.json` or similar) and make
   `compat/verify.py` consume that file only.
2. **Minimum:** document that pins are intentional and add a check that pin
   totals equal live inventory totals for command counts / token counts.

Do not weaken fail-closed behavior.

**Acceptance.**

- Changing inventory totals without updating the pin source fails verification.
- Pin source is single-file and referenced by verify, not duplicated in prose.

### R5 — Worktree and branch hygiene (Severity: Medium)

**Symptom.** Thirteen additional worktrees under `/tmp/ferricov-*` are marked
prunable. Multiple historical `repair/m0-*` branches remain checked out there.
Active work is on `test/m0-tf030-exact-numeric-matrix`.

**Why it matters.** Agents reopen stale trees, edit the wrong checkout, or
reintroduce already-merged repairs.

**Fix.**

1. Declare the canonical active worktree as `/home/cc/code1/ferricov` on the
   current M0 delivery branch.
2. Remove only **prunable** local worktrees after confirming they have no
   unique dirty files (`git status --porcelain` empty).
3. Do not delete remote branches in this slice unless the owner explicitly asks.
4. Record the canonical worktree rule in the workbench project notes / this
   review artifact.

**Acceptance.**

- `git worktree list` shows the canonical tree plus only intentionally retained
  extras.
- No in-flight unique dirty changes are discarded.

### R6 — TF-030 fail-open evidence risk (Severity: Closed on current branch)

**Symptom / history.** Independent Critical audit found self-hash refresh,
open semantic JSON shape, and missing direct upstream byte binding risks.

**Current state.** `m0-tf030-audit-rework-spec.md` records that the sixth
independent Critical audit accepted the rework; independent observation
registry and merge-integrity repairs are present in the fixture validators.

**Fix for this plan.** Re-verify, do not re-implement unless verification fails.

**Acceptance.**

- Targeted TF-030 validation commands pass on this branch.
- Spec remains explicit that product compatibility is false and M1 is blocked.

### R7 — M1 activation blockers not centralized (Severity: Low for code, High for process)

**Symptom.** Blockers such as `M1-MD-020`, `M1-TF-063`, `M1-TF-064`, residual
unbound diagnostics identities, and the 88 primary gaps are scattered across
SSoT paragraphs, tasks, and reviews.

**Why it matters.** An agent can mistake “many contracts exist” for “M1 is
unlocked.”

**Fix.**

Include an explicit `m1_activation_blockers` array in the M0 status snapshot:

- `behavior_primary_gaps` count from contract totals;
- named model/tracefile decision blockers still open;
- any unbound diagnostic/parallel planned IDs count if cheaply available;
- `product_compatibility_evidence=false`;
- `m1_authorized=false`.

**Acceptance.**

- One machine-readable place answers “may M1 start?” with `false` and reasons.

### R8 — Commit-message / identity hygiene (Severity: Low)

**Symptom.** Historical commits include non-English subjects; repo-local git
email may not match the intended GitHub identity policy for this remote.

**Fix.**

1. Keep all new commits English-only per `AGENTS.md`.
2. Before any commit on this GitHub remote, set/confirm repo-local
   `user.name` / `user.email` to the GitHub identity the owner uses for
   `Gujiassh/ferricov` (do not guess a private email; use the configured
   global GitHub-facing identity if already correct, otherwise ask).
3. Do not rewrite old history.

**Acceptance.**

- New commits from this remediation are English and use the intended identity.

## Implementation Order

1. **R6 verify** — confirm TF-030 validators still pass; stop if not.
2. **R1 + R2 + R7** — status snapshot + SSoT metric sync + blocker list.
3. **R4** — single pin source for verify inventory expectations.
4. **R3** — mechanical Oracle module split with tests.
5. **R5** — prune empty prunable worktrees only.
6. **R8** — enforce on the remediation commit(s).

## Explicit Non-Goals

- Closing the 88 remaining primary gaps in this slice.
- Authoring new genhtml/debug/history planning waves unless needed to fix a
  structural risk.
- Performance claims.
- Product binary scaffolding beyond empty crate comments already present.

## Verification Gate (whole slice)

```bash
python3 - <<'PY'
import json
from pathlib import Path
t=json.loads(Path('compat/behavior/contract.json').read_text())['totals']
assert t['reviewed_primary_coverage'] == 443
assert t['uncovered_public_entries'] == 88
print('ok', t['reviewed_primary_coverage'], t['uncovered_public_entries'])
PY
python3 compat/behavior/validate.py --mode current
python3 -m unittest compat.behavior.test_validate
python3 compat/verify.py --skip-oracle
python3 -m unittest compat.fixtures.m0-tracefiles.test_validate
FERRICOV_SKIP_DOCKER_E2E=1 cargo test --workspace --all-targets --locked
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
git worktree list
```

## Rollback

- Documentation/status snapshot: revert the docs commit.
- Verify pin extraction: restore previous constants if pin file proves wrong.
- Oracle split: revert the split commit; keep behavior identical so revert is
  safe.
- Worktree removal: only remove prunable clean trees; no content rollback
  needed if clean.

## Audit Questions For The Independent Reviewer

1. Is the scope correctly limited to current-phase structural risk, without
   sneaking M1 product work?
2. Are R1–R5 the right priority order for reducing M0 delivery risk?
3. Is R3 (Oracle split) safe enough to do now, or should it wait until after
   the active branch merges to `main`?
4. Does R4’s pin-file approach preserve fail-closed semantics?
5. Is worktree pruning specified safely enough?
6. What must be added or removed before implementation is allowed?

## Independent Audit Result

- Auditor: independent Critical review (2026-08-13)
- Verdict: **Accept with fixes**
- Plan risk class: Standard (Critical if R3/R4 executed without amendments)

### Mandatory amendments applied

1. **R3 deferred** from this slice (pre-M1 mechanical PR later).
2. **R1 verifier is totals-driven** from `compat/behavior/contract.json`, not a
   hard-coded residual pair ban.
3. **R2/R7 snapshot is generated or verified** against live contracts; includes
   `m1_authorized=false` and named blockers.
4. **R4 pin file is dual-control**: committed pin file, verify only reads it,
   regeneration is a separate explicit maintainer step.
5. **R5 names the 13 prunable worktrees** and uses prune for missing paths.
6. **R6 uses the full TF-030 rework verification set** with `LCOV_SOURCE_ROOT`.
7. Projection-count prose (445 vs 442) is reconciled or removed from live status.
8. No permanent hard-coded `443`/`88` as the long-term anti-drift law.

### Implementation order (post-audit)

1. R6 verify
2. R5 worktree prune
3. R1 + R2 + R7
4. R4 pin extraction
5. R8 on remediation commits
6. R3 deferred

### Audit report location

See chat session audit for full findings F1–F9. This section records the binding
implementation constraints.

## Delivery Record

- Date: 2026-08-13
- Branch: `test/m0-tf030-exact-numeric-matrix`
- Audit verdict: Accept with fixes; R3 deferred
- R6: TF-030 validate + 52 unit tests OK
- R5: pruned 13 missing `/tmp/ferricov-*` worktrees; canonical tree only
- R1/R2/R7: `docs/ssot/m0-status.snapshot.json` + live totals verifier
- R4: `compat/inventory/expected-pins.v2.5.json` dual-control pins
- R3: deferred (pre-M1 mechanical PR)
- Product compatibility evidence: false
- M1 authorized: false

