# M0 Residual Closure — Multi-Agent / Multi-Worktree Plan

Status: active collaboration plan  
Baseline: `test/m0-tf030-exact-numeric-matrix@90bc1f7`  
Metrics at plan freeze: `reviewed_primary=493`, `gaps=38`, `m1_authorized=false`

## 1. What is already listed vs what this plan adds

| Artifact | Role | Ready? |
| --- | --- | --- |
| `docs/ssot/m0-status.snapshot.json` | live residual metrics + M1 blockers | yes |
| `reviews/m0-residual-blocked-ledger.md` | 4 CLI + 34 lcovrc inventory | yes (list only) |
| `reviews/m0-cli-residual-blocked-ledger.md` | CLI subset | yes (subset) |
| `tasks.md` / `plan.md` | milestone narrative | partial (not lane-split) |
| **this plan** | lane ownership, worktree/PR rules, acceptance | **this file** |
| per-lane agent briefs | exact target lists + edit boundaries | `m0-residual-lane-*-brief.md` |

**Answer:** residual *inventory* is listed; *multi-agent execution package* was incomplete — this plan + lane briefs close that gap.

## 2. Collaboration model (yes, multi-worktree / multi-agent / PR)

**Supported.** Pattern:

```
Main controller (this session / human)
  ├── assigns lanes + baselines
  ├── accepts Critical audits
  └── merges/pushes (or approves PR merge)
Lane agents (parallel)
  ├── one git worktree each (preferred)
  ├── one PR each into the integration branch
  └── no cross-lane file ownership
```

### 2.1 Branch topology

| Branch | Purpose |
| --- | --- |
| `test/m0-tf030-exact-numeric-matrix` | **integration branch** (current M0 tip) |
| `m0-residual/lane-A-cli-hard` | Lane A PR source |
| `m0-residual/lane-B-lang-ext` | Lane B |
| `m0-residual/lane-C-filters` | Lane C |
| `m0-residual/lane-D-geninfo-success` | Lane D |
| `m0-residual/lane-E-parallel` | Lane E |
| `m0-residual/lane-F-misc` | Lane F |

Rules:

1. Branch each lane from the **same integration SHA** at assignment time (record SHA in the PR).
2. **One active worktree per lane**; do not open a second worktree for the same lane family.
3. PR target: `test/m0-tf030-exact-numeric-matrix` (not `main`, not `k3s`).
4. Rebase/merge integration into the lane only when the controller says so (avoid thrash).
5. After merge, controller runs full `validate.py` + regenerate cleanliness check before next wave.

### 2.2 Agent roles

| Role | May do | Must not do |
| --- | --- | --- |
| **Lane implementer** | seal Oracle, suite/tests, authored fragment, regenerate contract in-lane, open PR | push to integration, claim product evidence, edit other lanes' files |
| **Lane auditor** (separate agent) | Critical read-only audit of the PR diff | implement fixes (return findings to implementer) |
| **Controller** | architecture, lane assignment, final acceptance, merge/push, ledger/status updates | leave unreviewed multi-lane merges unvalidated |

Default model for subagents when spawning: follow workspace rule (`gpt-5.4` unless user overrides).

### 2.3 Non-overlapping ownership (hard)

| Path pattern | Owner |
| --- | --- |
| `compat/fixtures/m0-residual-<lane>-*/` | that lane only |
| `compat/cases/m0-residual-<lane>-*` / `test_m0_residual_<lane>_*` | that lane only |
| `compat/behavior/fragments/authored/m0-residual-<lane>-*.json` | that lane only |
| `compat/behavior/fragments/authored/m0-*-wave1-repair-*.json` | **serialize** strip of case groups (controller or single merge agent) |
| `compat/behavior/contract.json` / `plan-bindings.json` / `validate.py` pin | **controller merge step** (or last-merge lane with exclusive lock) |
| `docs/ssot/m0-status.snapshot.json` | controller after each merge |
| `specs/.../reviews/m0-residual-lane-*-review.md` | that lane |

**Collision hotspot:** repair fragments + plan-bindings hash.  
**Mitigation:** implementers **do not** strip repair fragments or bump `EXPECTED_PLAN_BINDINGS_SHA256` in parallel. They deliver:

- new fixture + suite + tests + **authored wave fragment only**
- PR description lists target ids

Controller (or a dedicated **merge agent**) then:

1. checks out integration
2. applies wave fragment
3. strips repair skeletons for those ids
4. runs `generate.py` + pin update + status snapshot
5. Critical audit + push/merge

Optional fast path: only **one** lane merges at a time (serial merge, parallel implement).

### 2.4 PR checklist (every lane PR)

- [ ] Target ids ⊆ assigned lane list (no extras)
- [ ] Oracle image `sha256:b02cc645…56eb80b7`
- [ ] `product_compatibility_evidence=false` everywhere
- [ ] Substantive plan: `reviewed` + `planned` + non-empty `suite_cases` + real exit/fs (or documented stderr) delta
- [ ] No cmd_line-only / hollow parse-only closure
- [ ] Unit tests for suite pins + mutation reject
- [ ] English commit messages
- [ ] Review artifact under `specs/.../reviews/`
- [ ] Does **not** touch other lanes' fixtures/cases/fragments

### 2.5 Acceptance (controller)

1. `python3 compat/behavior/generate.py` then dirty tree empty for generated inventory
2. `python3 compat/behavior/validate.py` green
3. plan-bindings pin matches
4. wave tests green
5. metrics move only by assigned target count
6. ledger updated (closed ids removed or marked done)

---

## 3. Lane partition (38 targets)

### Lane A — CLI hard (4)

Brief: `m0-residual-lane-A-cli-hard-brief.md`

- `command.geninfo.option.compat-libtool`
- `command.lcov.option.compat-libtool`
- `command.geninfo.option.history-script`
- `command.perl2lcov.option.preserve`

Fixture theme: real `.libs` compile; multi-gcda history profile; Devel::Cover DB.

### Lane B — language extensions (5)

Brief: `m0-residual-lane-B-lang-ext-brief.md`

- `lcovrc.c-file-extensions`
- `lcovrc.java-file-extensions`
- `lcovrc.python-file-extensions`
- `lcovrc.perl-file-extensions`
- `lcovrc.rtl-file-extensions`

Fixture theme: multi-extension sources; only matching extension appears in SF set.

### Lane C — filters (3)

Brief: `m0-residual-lane-C-filters-brief.md`

- `lcovrc.filter-bitwise-conditional`
- `lcovrc.filter-blank-aggressive`
- `lcovrc.filter-lookahead`

Fixture theme: crafted C with blank/bitwise/lookahead edge lines.

### Lane D — geninfo success semantics (9)

Brief: `m0-residual-lane-D-geninfo-success-brief.md`

- `lcovrc.geninfo-auto-base`
- `lcovrc.geninfo-capture-all`
- `lcovrc.geninfo-compat`
- `lcovrc.geninfo-compat-libtool`
- `lcovrc.geninfo-follow-symlinks`
- `lcovrc.geninfo-gcov-all-blocks`
- `lcovrc.geninfo-interval-update`
- `lcovrc.geninfo-unexecuted-blocks`
- `lcovrc.no-exception-branch`

Fixture theme: multi-dir capture, symlinks, unexecuted blocks, exception edges, compat modes with real path effects.

### Lane E — parallel / fork (6)

Brief: `m0-residual-lane-E-parallel-brief.md`

- `lcovrc.parallel`
- `lcovrc.max-tasks-per-core`
- `lcovrc.lcov-filter-chunk-size`
- `lcovrc.lcov-filter-parallel`
- `lcovrc.fork-fail-timeout`
- `lcovrc.max-fork-fails`

Fixture theme: multi-file workloads; prefer exit/filesystem effects over pure timing.

### Lane F — misc (11)

Brief: `m0-residual-lane-F-misc-brief.md`

- `lcovrc.check-data-consistency`
- `lcovrc.demangle-cpp`
- `lcovrc.derive-function-end-line-all-files`
- `lcovrc.expected-message-count`
- `lcovrc.forget-testcase-names`
- `lcovrc.info-file-pattern`
- `lcovrc.lcov-json-module`
- `lcovrc.select-script`
- `lcovrc.split-char`
- `lcovrc.suppress-function-aliases`
- `lcovrc.trivial-function-threshold`

Fixture theme: demangle needs `c++filt` in Oracle; expected-message-count needs legal `type:count` forms; split-char must not break ignore-errors parsing by accident.

## 4. Parallelism recommendation

| Mode | When |
| --- | --- |
| **Parallel implement, serial merge** (recommended default) | Always safe with current generate/pin tooling |
| Parallel implement + parallel PR open | Yes |
| Parallel merge to integration | **No** unless merge agent owns generate/pin exclusively |

Max useful parallel implementers: **6** (one per lane).  
Max concurrent merges: **1**.

## 5. Out of scope for residual lanes

- M1 product crates / `m1_authorized`
- diagnostics unbound PAR-* (separate track: `diagnostics-parallel-contract.md`)
- model decisions M1-MD-020 / TF-063 / TF-064
- CB-* / INST-* audit non-substantive debt (unless controller opens a lane)

## 6. Definition of done for residual program

1. `uncovered_public_entries == 0` for public primary plans (or explicit N/A with controller sign-off)
2. `validate.py` green on clean tree after regenerate
3. blocked ledger empty or only intentional N/A
4. M0 exit review artifact written
5. Still `m1_authorized=false` until product evidence program starts
