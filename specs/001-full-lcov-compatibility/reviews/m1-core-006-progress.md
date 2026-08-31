# M1-CORE-006 Progress — Record Semantics

Status: **IMPLEMENTED (shippable happy-path + key-edge slice; full Oracle ignore/stop matrix residual)**  
Date: 2026-08-18  
Package: `ferricov-tracefile` (depends on `ferricov-model`)  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `de5d25b` with CORE-005 landed)  
Scope: `crates/tracefile` + this progress review doc  
Commit/push: **not performed** (per task)

## Acceptance

Agent-spec CORE-006: *All 20 record tags, legacy/current function forms, summaries,
checksums, version rules, branch state, MC/DC close behavior, terminators, ignored
errors, and hard failures.*

Honest shippable slice delivered (not full Oracle parity for every malformed path):

| Requirement | Status |
| --- | --- |
| Apply path for TN / SF / KF into model DB | Done (bind + ensure source) |
| VER (source-scoped; identical repeat OK; conflicting second → hard-fail) | Done |
| DA (count accumulate + optional checksum into `checksums`) | Done |
| FN / FNDA / FNL / FNA (legacy + current → `FunctionTable`) | Done (happy + key hard-fails) |
| BRDA (kind / U / block cursor / `-` → `NeverEvaluated`) | Done |
| MCDC (both senses; index gap/format; already-defined hard-fail) | Done (key paths) |
| Summary tags FNF/FNH/BRF/BRH/LF/LH/MCF/MCH ignored as model totals | Done |
| `end_of_record` section commit (L/F/B union; MC/DC late-TN close) | Done |
| Unknown nonblank → `ERROR_FORMAT` + `IgnorePolicy::{Continue,Stop}` | Done (simple enum) |
| `StreamingParser::database()` / `into_database()` / `parse_database` | Done |
| Focused tests; `cargo test -p ferricov-tracefile -p ferricov-model` green | Done (40 + 48) |
| No writer / no product evidence flip / no CLI / no commit | Done |

## Delivered modules

| Module | Role |
| --- | --- |
| `crates/tracefile/src/policy.rs` | `IgnorePolicy::{Continue,Stop}` |
| `crates/tracefile/src/section.rs` | `OpenSection` working buffers + FNL index + branch/MC/DC cursors |
| `crates/tracefile/src/commit.rs` | Section commit + `close_mcdc_block` (`U-MCDC-LATE-TN`) |
| `crates/tracefile/src/record_parse.rs` | Shared field splitters |
| `crates/tracefile/src/records.rs` | Per-tag apply dispatch onto open section / DB |
| `crates/tracefile/src/parser.rs` | Streaming API wired to apply + `database()` / `into_database()` |
| `crates/tracefile/src/diag.rs` | Extended `DiagKind` (version/FNL/MCDC/mismatch/…) |
| `crates/tracefile/src/tests_core006.rs` | Focused CORE-006 acceptance tests |

`records.rs` is ~840 lines (slightly over the soft ~800 guideline). Further tag-split
is deferred unless the next slice grows it further.

## Design choices

### Section commit

On `end_of_record`:

1. Ensure `SourceCoverage` exists under the SF/KF lookup key.
2. Merge source-scoped `VER` (conflict → hard-fail) and first-wins checksums.
3. Union this section's line / function / branch contribution into the
   **SF-bound** testcase family maps, then into aggregate (via model algebra
   `AlgebraOp::Union`).
4. Close MC/DC: union open block into **aggregate first**, then clone/union into
   the **current** test name (`U-MCDC-LATE-TN`), not the SF-bound name.
5. Clear working `OpenSection` buffers. Parser binding (`ParserState::source`)
   is intentionally not fully cleared (grammar: terminator does not fully clear
   source binding; residual Oracle cases define post-terminator records).

Unterminated sections are not auto-committed when a new `SF` opens (matches the
Oracle filter behavior used by `M0-TF-MCDC-SF-001`).

### Late-TN MC/DC

- Line / function / branch always write into the SF-bound test name buffers.
- MC/DC accumulates in `OpenSection::mcdc_open`.
- Close (terminator) looks up `ParserState::test_name()` at close time.
- Minimal fixture in `tests_core006::late_tn_assigns_mcdc_to_current_name`
  mirrors the M0-TF-TN-MCDC ownership idea: A owns L/F/B; B owns MC/DC; aggregate
  holds both senses.

### Ignore policy

`IgnorePolicy::Continue` (default) records ignorable diags and keeps applying.
`IgnorePolicy::Stop` sets `stopped` after the first ignorable diagnostic and
skips further apply. Hard-fails (`VersionConflict`, duplicate `FNL`, unknown
`FNA` index, `MCDC already defined`) always stop. Full per-category Oracle
ignore matrices / stop-on-error / exit-code wiring remain residual.

### Summaries

All eight summary tags classify and emit `RecordApplied` but never mutate
`observable_totals` or aggregate found/hit fields. Writer recomputation is
CORE-007.

## Tests

Commands:

```text
cargo test -p ferricov-tracefile   # 40 passed
cargo test -p ferricov-model       # 48 passed
```

Focused CORE-006 coverage:

1. Multi-record section → lines / functions / branches / MC/DC under correct
   testcase + aggregate after EOR; checksum + VER stored; summaries ignored
2. VER conflict hard-fail; identical VER repeat accepted
3. Summary records do not become trusted totals
4. Late TN before MCDC close → MC/DC under current name; L/F/B under SF-bound
5. BRDA `-` → `NeverEvaluated`
6. Non-UTF-8 SF path with DA
7. Unknown record → `ERROR_FORMAT` continue; Stop policy halts
8. `into_database()` consumes parser

## Implemented vs residual Oracle matrix gaps

### Implemented in this slice

- Happy-path apply for all data tags listed above
- Key hard-fails: VER conflict, duplicate FNL, unknown FNL index for FNA,
  MCDC already defined on line revisit
- Key ignorables: unknown record, FNDA unknown name (`ERROR_MISMATCH`),
  DA/BRDA/MCDC line ≤ 0 (retained under Continue), MC/DC index gap (appended +
  format diag), MC/DC expression mismatch (count still updates)
- Section commit + late-TN MC/DC ownership
- Simple continue/stop policy

### Residual (not claimed Oracle-complete)

1. Full ignore-category / stop-on-error / exit-status matrix vs pinned Perl
2. Checksum verification against source MD5 (`ERROR_VERSION`) — store only
3. Path resolve / exclude / language filters; skip-until-next-SF data gating
4. Exact BRDA no-final-comma / `rindex` edge; unreachable-flag modes beyond
   sticky `U` retention
5. Exact MC/DC aggregate cache found/hit cloning quirks (`M0-TF-MCDC-SF-001`
   unterminated first-source filter + cache counters)
6. Writer enumeration from line-test keys omitting B-only MC/DC (CORE-007)
7. EOF empty-source removal / `ERROR_EMPTY`
8. Function suppression patterns; mixed legacy/current conflict Oracle cases
9. Excessive-count thresholds / full TF-030 numeric coercion matrix on apply
10. Post-terminator records without new SF; repeated terminator Oracle cases
11. `forget_testcase_names` / TN replace-with-empty policy
12. Product evidence / differential manifests (explicitly out of scope)

## Residual risks

1. `records.rs` soft size (~840 lines) — split further if the next slice grows.
2. Commit unions the *section contribution* into both testcase and aggregate;
   repeated SF/test sections that should reuse-and-re-union existing testcase
   maps need Oracle confirmation (`M1-MD-003` / terminator clone interactions).
3. MC/DC line-contiguity hard-fail is section-local via `mcdc_closed_lines`;
   cross-section / append reuse paths (`U-MCDC-APPEND`) need more fixtures.
4. DA nonnumeric count currently coerces then reports ignorable format; exact
   Oracle retention/order of diag vs mutation may differ on edge spellings.

## Explicitly out of scope

- CORE-007 canonical writer
- Product evidence flip / differential closure
- CLI surfaces
- Commit / push
