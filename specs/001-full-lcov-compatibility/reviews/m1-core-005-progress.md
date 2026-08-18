# M1-CORE-005 Progress — Logical-Line Parser

Status: **IMPLEMENTED (logical-line pipeline + binding state; full record apply deferred)**  
Date: 2026-08-18  
Package: `ferricov-tracefile` (depends on `ferricov-model`)  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `a787184` with CORE-004 landed)  
Scope: `crates/tracefile` + this progress review doc only  
Commit/push: **not performed** (per task)

## Acceptance

Agent-spec CORE-005: *Perl-compatible chomp/trailing whitespace/comment handling,
prefix-vs-full record matching, raw bytes, source/testcase binding, and
malformed-state classification.*

| Requirement | Status |
| --- | --- |
| Logical-line normalization from raw bytes (`\n` / `\r\n` / lone `\r`) | Done |
| Perl-compatible chomp + trailing `\s` (documented Linux Oracle rule) | Done |
| Comment: `#` only at start of normalized line; leading-space `#` is not comment | Done |
| Preserve raw bytes for identity fields (paths, TN) | Done |
| Prefix vs full classification framework; Comment/Empty/Terminator/Record/Unclassified | Done |
| Recognize `TN`, `SF`/`KF` binding; other known tags as stubs | Done |
| No panic on arbitrary bytes | Done |
| Parser binding: current TN, SF/KF source open, late-TN does not rebind maps | Done |
| Streaming API: feed bytes / lines → events + state mutations | Done |
| Explicit malformed/diagnostic enum (ignored vs hard-fail classes) | Done |
| Focused tests in `crates/tracefile`; model still green | Done (30 tracefile + 48 model) |
| No product evidence flip / no CORE-006 full apply / no writer / no commit | Done |

## Delivered modules

| Module | Role |
| --- | --- |
| `crates/tracefile/src/line.rs` | Byte splitter + chomp/trailing-`\s` normalization |
| `crates/tracefile/src/classify.rs` | `LineClass` / `RecordTag` / prefix matching |
| `crates/tracefile/src/diag.rs` | `DiagKind` / `DiagClass` / `ParseDiag` |
| `crates/tracefile/src/state.rs` | `ParserState`, TN/SF binding, late-TN rule, `ParseEvent` |
| `crates/tracefile/src/parser.rs` | `StreamingParser` feed/finish/parse_all API |
| `crates/tracefile/src/tests_core005.rs` | Focused CORE-005 acceptance tests |

## Design choices (chomp / CRLF)

Pinned Oracle `_read_info` on Linux:

1. Perl `readline` splits only on `\n`.
2. `chomp` removes one trailing `\n`.
3. `$line =~ s/\s+$//` strips trailing Perl ASCII `\s`
   `{0x09,0x0A,0x0B,0x0C,0x0D,0x20}` (verified on Perl 5.38.2; NEL/`0x85` and
   NBSP/`0xA0` are **not** whitespace under this runtime).

CRLF fixtures therefore normalize as: keep `\r\n` → chomp drops `\n` →
trailing-`\s` drops leftover `\r`. Ferricov matches that end state.

**Ferricov splitter choice:** the streaming API accepts raw byte chunks and
splits on `\r\n`, `\n`, **or** lone `\r` (universal newlines). After terminator
strip, trailing-`\s` matches Oracle. LF and CRLF fixtures yield Oracle-identical
normalized lines. CR-only files are split here but would be a single readline
record under Oracle on Linux; that difference is intentional for byte-stream
robustness and is a residual for differential cases that use CR-only separators.

## Binding / late-TN

- Initial test name is empty (`TN:` with no payload is valid).
- `TN` base stops at first comma; Perl ASCII `\W` → `_`; exact `,diff` retained;
  unconsumed suffix after `,diff` / other comma suffixes preserved on the event.
- `SF`/`KF` share bind semantics; path payload bytes build
  `SourceIdentity::from_display_path` (filesystem resolve remains outside M1).
- Empty/whitespace-only `SF`/`KF` payload → ignorable `EmptySourcePath`, section
  marked skipped (no open bind).
- **Late `TN` updates the current name only.** It does not clear or rebind the
  already-open source binding / `bound_test_name`. MC/DC exceptional close
  ownership (`U-MCDC-LATE-TN`) is CORE-006.

## Malformed classification (this slice)

| Class | When | Severity |
| --- | --- | --- |
| `IgnoredEmpty` / `IgnoredComment` | blank or `^#` | ignored |
| `DiagKind::ErrorFormat` | unclassified nonblank line | Ignorable |
| `DiagKind::EmptySourcePath` | empty `SF`/`KF` payload | Ignorable |
| `DiagKind::TestNameSanitized` | `\W` replaced in TN base | Note |
| `DiagClass::HardFail` | reserved; no CORE-005 hard-fail yet | — |

Policy application (ignore-errors / stop-on-error / exit) remains CORE-006+.

## Tests

Commands:

```text
cargo test -p ferricov-tracefile   # 30 passed
cargo test -p ferricov-model       # 48 passed
```

Focused CORE-005 coverage:

1. chomp/CRLF/LF byte preservation + interior NUL
2. `#comment` vs ` #not-comment`
3. `TN:` empty, `TN:name`, `TN:name,diff` (+ sanitization)
4. `SF:` / `KF:` bind with arbitrary / non-UTF-8 path bytes
5. `end_of_record` terminator (+ suffix permissiveness)
6. Non-UTF-8 path bytes survive streaming
7. Chunked multi-section feed updates TN/SF; late-TN keeps SF-bound name
8. Arbitrary 0..=255 bytes do not panic

## Residual risks for CORE-006

1. Full semantic apply for all 20 tags (DA/FN/FNDA/FNL/FNA/BRDA/MCDC/VER/summaries)
   including Full-anchor validation and numeric/`looks_like_number` paths.
2. Section commit on terminator (union into aggregates, MC/DC close, branch
   block close) and EOF empty-source filtering (`ERROR_EMPTY`).
3. MC/DC late-TN ownership at close (`testcase_mcdc($testname)` vs SF-bound map).
4. Skip-current-file exclusion until next `SF`/`KF`; path resolve / language
   filters stay outside or partially deferred.
5. Ignore / stop-on-error policy wiring for ignorable diags; hard `die` paths
   (duplicate `FNL` index, version conflict, `MCDC already defined`).
6. CR-only line-split divergence vs Oracle readline (document in TF-001 if a
   CR-only fixture is added).
7. Summary prefix matching is stub-level (`FNF`…); Oracle ignores payloads —
   CORE-006 must keep them non-mutating.

## Non-claims

- Does not flip `product_compatibility_evidence`
- Does not implement full CORE-006 record apply
- Does not implement writer (CORE-007)
- Does not change CLI / ops / report
- Does not commit or push
