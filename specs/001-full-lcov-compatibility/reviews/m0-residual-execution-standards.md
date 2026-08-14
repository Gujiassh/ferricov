# M0 Residual Closure — Execution Standards

Status: normative (fail-closed)  
Applies to: all residual lanes A–F  
Parent plan: `m0-residual-multi-agent-plan.md`  
Integration branch: `test/m0-tf030-exact-numeric-matrix`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`

This document is the **source of truth for how work is done**. Lane briefs list *what*; this file lists *how* and *pass/fail*.

---

## 0. Program gates (ordered)

No step may skip its audit.

| Step | Output | Gate agent | Pass criterion |
| ---: | --- | --- | --- |
| S0 | Spec package complete | independent Critical auditor | ACCEPT on this file + plan + 6 briefs + ledger alignment |
| S1 | Worktrees + branches created | controller self-check | one worktree/lane, same baseline SHA, no dirty cross-talk |
| S2 | Per-lane implementation | independent lane auditor | Critical ACCEPT on that lane PR/worktree |
| S3 | Controller serial merge | independent merge auditor | generate clean, validate green, metrics delta = closed targets only |
| S4 | Integration push | controller | remote tip matches accepted merge SHA |
| S5 | Program close | M0 exit review | gaps=0 or signed N/A; still m1_authorized=false |

If any audit is **Reject**, rework returns to the **same responsible agent**; do not open a replacement agent unless the original is unavailable.

---

## 1. Non-negotiable product rules

1. **Planning only.** `evidence_status=planned`, empty product evidence arrays, `product_compatibility_evidence=false`.
2. **No M1.** Do not set `m1_authorized=true`. Do not implement Ferricov product crates for residual closure.
3. **No hollow closes.** Forbidden: cmd_line-only, parse-only, description-only `reviewed` without `suite_cases` (or behavior_groups+upstream_tests).
4. **Honest Oracle.** Prefer real exit/filesystem differentials. Exit-only is allowed only when documented as unused/error surface and still seals stable exit codes.
5. **English commits** on all residual branches.
6. **GitHub identity** for this remote: inherit `gujishh` / do not use GitLab identity.

---

## 2. Oracle sealing standard

### 2.1 Environment (required)

```
HOME=/work LANG=C LC_ALL=C TZ=UTC
PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0
SOURCE_DATE_EPOCH=946684800 TMPDIR=/work
```

Container: pinned image digest above. Run as host uid:gid (avoid root-owned fixtures).

### 2.2 Tree hashing

- Hash the **case working tree after command**, excluding runner artifacts (`__run.sh`, `__stdout`, `__stderr`, `__exit`).
- Shared multi-config fixtures: **all** variant `.lcovrc` files present in every case so tree deltas come from outputs/exit, not missing config files alone.
- Record: `exit_code`, `file_count`, `file_tree_bytes`, `file_tree_sha256`, `paths`, stdout/stderr sha+bytes, `reverse_run.exit_code=23` (planning convention unless product reverse exists).

### 2.3 Stability

- Re-run each sealed case ≥2 times; require identical `file_tree_sha256` and `exit_code`.
- If stderr is compared: must be stable (no memory counters, no temp path churn). Else exclude stderr.

### 2.4 Control vs variant

Every closed target needs:

- at least one **control** case without the boundary (or with neutral threshold), and
- at least one **variant** case with the boundary,

such that `exit` differs **or** `file_tree_sha256` differs (or both).

---

## 3. Suite / fragment standard

### 3.1 Naming

| Kind | Pattern |
| --- | --- |
| Fixture dir | `compat/fixtures/m0-residual-{slug}-contract/` |
| Suite JSON | `compat/cases/m0-residual-{slug}-contract.json` |
| Validator module | `compat/cases/m0_residual_{slug_us}_contract.py` |
| Unit tests | `compat/cases/test_m0_residual_{slug_us}_contract.py` |
| Authored fragment | `compat/behavior/fragments/authored/m0-residual-{slug}-wave.json` |
| Review | `specs/.../reviews/m0-residual-lane-{X}-*-review.md` |

`{slug}` examples: `a-cli-hard`, `b-lang-ext`, `c-filters`, `d-geninfo-success`, `e-parallel`, `f-misc`.

### 3.2 Suite document

- `schema_version=1`, `evidence_scope=compatibility`, `surface` = `cli` or `config`
- `comparisons`: ordered list of `{dimension, normalizer:"exact-v1"}`
- Production validator rejects: wrong ids/order, wrong argv, adding stdout/stderr when excluded, fixture path drift

### 3.3 Case group (fragment)

- `origin=manually_curated`
- `review_status=reviewed`
- `evidence_status=planned`
- `suite_cases` non-empty, sorted by (suite_id, case_id)
- `source_references` inventory-aligned, sorted by validate `source_key`
- description contains `cli-option boundary` or `config-key boundary` and explicit non-claim of product evidence
- targets: exactly one primary id from the lane list

### 3.4 Unit tests (minimum)

1. production validator accepts committed suite  
2. mutations rejected  
3. oracle pins + control/variant relation asserts  
4. fixture content hashes locked  
5. plans reviewed/planned/suite_cases present  

---

## 4. Implementer worktree protocol

```bash
# example Lane A
git fetch origin
git worktree add ../ferricov-m0-lane-A -b m0-residual/lane-A-cli-hard origin/test/m0-tf030-exact-numeric-matrix
```

Record in PR:

- baseline integration SHA
- lane letter + exact target ids
- Oracle seal command summary (or script path if committed under fixture)

### Local validation path (implementer)

Because residual `case.acceptance.*` ids already live in other authored fragments, a full
`python3 compat/behavior/generate.py` **will fail** in the lane worktree if the new wave
is added without stripping those hosts. That strip is **controller-only**.

Therefore implementers **must** validate with:

1. `python3 -m unittest compat.cases.test_m0_residual_<slug_us>_contract -v`
2. `python3 compat/cases/m0_residual_<slug_us>_contract.py` (static suite gate)
3. Optional: JSON schema sanity on the authored fragment only

Implementers **must not** attempt full contract regenerate/pin update in the lane PR.

### Implementer must NOT

- run controller merge or commit final `contract.json` / `plan-bindings.json` / pin bump
- strip **any** pre-existing authored fragments (repair, blocked, capture, filter, …)
- edit other lanes
- force-push integration

### Implementer PR body template

```markdown
## Lane
- Letter:
- Baseline SHA:
- Targets: (bullet list)

## Oracle
- Image digest:
- Differential summary table (case | exit | tree delta)

## Non-claims
- product_compatibility_evidence=false
- remaining residuals still open

## Tests
- unittest module: ...
```

---

## 5. Lane auditor standard (Critical)

Auditor is **read-only**. Order:

1. **Goal** — still M0 planning for assigned targets only?  
2. **Oracle honesty** — real delta? stable? correct image?  
3. **Contracts** — suite/fragment/inventory refs aligned?  
4. **Boundaries** — no file ownership violations?  
5. **Tests** — pins + mutations prove invariants?  
6. **Regress** — no product evidence, no M1, no hollow close?

Verdict: `ACCEPT` | `REJECT` with ordered findings (severity first).  
Reject → same implementer reworks with evidence list.

---

## 6. Controller merge standard (serial)

For each accepted lane, **one at a time**:

1. Merge lane branch into integration (ff or merge commit; no force)
2. Ensure authored wave fragment present
3. **Strip closed case ids from every authored fragment that currently hosts them**
   (not only `wave1-repair`). Deterministic procedure:
   - for each closed `case.acceptance.*` id, search `compat/behavior/fragments/authored/**/*.json`
   - remove that case group from its current host fragment
   - rewrite host as canonical sorted JSON
   - known residual hosts at plan time (38 ids):
     - `m0-geninfo-wave1-repair-a.json` (2)
     - `m0-lcov-wave1-repair-a.json` (1)
     - `m0-perl2lcov-wave1-repair-a.json` (1)
     - `m0-lcovrc-wave1-repair-a.json` (10)
     - `m0-lcovrc-wave1-repair-b.json` (6)
     - `m0-lcovrc-wave1-repair-d.json` (6)
     - `m0-lcovrc-blocked-wave.json` (6)
     - `m0-lcovrc-capture-wave.json` (2)
     - `m0-lcovrc-filter-wave.json` (4)
4. `python3 compat/behavior/generate.py`
5. Confirm generated inventory dirty only as expected; fix stale skeletons
6. Update `EXPECTED_PLAN_BINDINGS_SHA256` in `compat/behavior/validate.py`
7. `python3 compat/status/generate_m0_status.py`
8. `python3 compat/behavior/validate.py` must pass on clean tree after regenerate
9. Run lane unit tests + any adjacent smoke
10. Independent merge audit (metrics delta == closed target count)
11. Update blocked ledger (remove closed ids)
12. Push integration
13. Only then start next merge

**Metrics oracle:**  
`new_reviewed - old_reviewed == number of newly substantive primary targets`  
`new_gaps - old_gaps == -that number` (unless unrelated fixes).

---

## 7. Done criteria per target

A target is **closed** only if all hold:

- [ ] In authored fragment as substantive plan  
- [ ] Bound suite case(s) with sealed oracle  
- [ ] Unit tests green  
- [ ] Lane auditor ACCEPT  
- [ ] Merged via controller protocol  
- [ ] Appears in `reviewed_primary` coverage (no longer uncovered)  
- [ ] Removed from blocked ledger  

---

## 8. Explicit non-goals

- Closing diagnostics unbound PAR-* in these lanes  
- Unblocking M1-MD-020 / TF-063 / TF-064  
- Product compatibility evidence  
- Parallel merges of two lanes  

---

## 9. Spec package inventory (S0)

| File | Role |
| --- | --- |
| `m0-residual-multi-agent-plan.md` | collaboration topology |
| `m0-residual-execution-standards.md` | **this file** — how to execute |
| `m0-residual-lane-A-cli-hard-brief.md` | targets A |
| `m0-residual-lane-B-lang-ext-brief.md` | targets B |
| `m0-residual-lane-C-filters-brief.md` | targets C |
| `m0-residual-lane-D-geninfo-success-brief.md` | targets D |
| `m0-residual-lane-E-parallel-brief.md` | targets E |
| `m0-residual-lane-F-misc-brief.md` | targets F |
| `m0-residual-blocked-ledger.md` | living residual list + lane map |
| `tasks.md` (residual section) | checklist |

S0 audit must verify: 4+34=38 targets partitioned without overlap/omission; standards fail-closed; serial merge of pins mandatory.
