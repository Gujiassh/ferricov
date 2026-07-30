# Execution Plan: Full LCOV 2.5 Compatibility

## 1. Objective

Deliver Ferricov 1.0 as a behavior-compatible replacement for the complete
installed public surface of LCOV 2.5 at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, while meeting every gate in the
performance contract.

Compatibility is the release gate. Rust implementation and higher performance
are not substitutes for compatible behavior.

## 2. Planning Baseline

The initial v1 extraction baseline found:

- 10 installed commands
- 156 distinct long-option candidates from the original document-oriented
  extraction
- 130 `lcovrc` key candidates in the initial extraction
- 23 installed support scripts
- 205 upstream test files
- approximately 30,600 lines across `lcov`, `genhtml`, `geninfo`, and
  `lcovutil.pm`

The current v2 executable-contract inventory supersedes the original 156-option
candidate count with:

- 353 exact parser-backed option definitions
- 41 additional documentation-derived candidates
- 9 positional forms
- 158 reviewed `lcovrc` entries: 153 public and 5 not applicable
- 23 installed support scripts
- all 205 upstream test files mapped and reviewed
- 531 public behavior plans, with 69 reviewed primary plans, all 4 required
  critical interaction domains reviewed, and 462 primary-review gaps

The option and configuration counts are omission-detection inputs, not progress
percentages. One option may require multiple positive, negative, configuration,
interaction, callback, and platform cases before it can pass.

## 3. Delivery Assumptions

The schedule assumes one full-time technical owner using AI for inventory,
fixture generation, implementation assistance, and review. It also assumes
reliable Linux build capacity and access to macOS runners before release
qualification.

Estimated duration is 28-36 full-time weeks. This is an engineering estimate,
not a release promise. Compiler availability, callback compatibility, and
upstream test portability are the largest sources of variance.

Adding engineers can shorten fixture, compiler-matrix, converter, and review
work. It will not linearly shorten the core model and compatibility decisions,
which require one architectural owner.

## 4. Execution Rules

1. Pin behavior to LCOV 2.5 until Ferricov 1.0 qualification is complete.
2. Inventory behavior before implementation.
3. Define a semantic Oracle for every work slice.
4. Preserve raw evidence before normalization.
5. Accept only reviewed normalizers from `compat/normalizers.md`.
6. Require unit tests and differential cases for every implemented behavior.
7. Require correctness parity before measuring or claiming performance.
8. Keep release claims narrower than the verified compatibility matrix.
9. Do not preserve the upstream internal Perl architecture.
10. Do not add Ferricov-only product features before 1.0 qualification.

## 5. Workstreams

### W1: Contract And Inventory

Owns command, option, configuration, tracefile, callback, installation,
platform, and compiler inventories. Every entry records its upstream source,
behavior class, dependencies, interaction groups, test cases, implementation
status, and evidence links.

### W2: Oracle And Evidence

Owns pinned upstream environments, differential execution, normalizers,
coverage-model comparison, tracefile comparison, DOM comparison, filesystem
comparison, result schemas, and evidence publication.

### W3: Coverage Core

Owns the byte-preserving coverage model, tracefile parser/writer, aggregation
invariants, path representation, counter arithmetic, source identity, test
names, checksums, branch data, condition data, and MC/DC data.

### W4: Public Commands

Owns CLI parsing, aliases, common options, `lcovrc`, environment expansion,
message classes, ignore behavior, exit status, filesystem orchestration, and
the installed command entry points.

### W5: Reports And Capture

Owns `genhtml`, report assets, normalized DOM parity, `geninfo`, GCC/LLVM
integration, package capture, kernel capture, and compiler-version behavior.

### W6: Performance And Release

Owns benchmark fixtures, time and RSS measurement, thread scaling, CI,
packaging, provenance, release artifacts, platform qualification, and external
project pilots.

W1 and W2 remain active through the entire project. They do not end when coding
starts.

## 6. Milestones

### M0: Executable Contract

**Target:** weeks 1-3

**Scope**

- Complete manual classification of all generated inventory candidates.
- Add missing short options, positional forms, environment variables, config
  discovery rules, tracefile records, message classes, callback protocols, and
  installation behavior.
- Map all upstream tests to inventory entries and interaction groups.
- Define the initial Linux compiler and filesystem matrix.
- Capture upstream correctness outputs and representative performance
  baselines.
- Decide and document how Perl-module callbacks and Perl coverage databases are
  supported. Exact compatibility may require invoking a user-provided Perl
  runtime only when those public features are used.

**Exit gate**

- Every public candidate is classified as public, internal, duplicate alias,
  generated token, or not applicable, with a source reference.
- Every public entry has at least one planned differential case.
- High-risk interactions have explicit case groups.
- The Oracle suite and baseline benchmark can run from a clean checkout.
- Callback/runtime and compiler/platform decisions are accepted for the scope
  needed by M1.
- The Oracle is retained as a content-addressed artifact or has a reproducible
  build definition, and the required execution-manifest format is recorded.
- No unresolved licensing or callback-compatibility decision blocks the core
  model.

**Current status:** in progress. The schema-aware v2 inventory, all command,
configuration, positional, and support-script reviews, the exhaustive 205-file
upstream test map, the callback/runtime and compiler/platform ADRs, and the
reproducible Oracle build and execution-manifest lane are established. M0 is
not complete: 462 behavior-planning gaps, compiler capture qualification, and
release platform evidence remain. The 148-case M0 CLI/configuration correctness baseline is
retained and passes independent semantic replay, without claiming Ferricov
product compatibility. Forty public CLI primary entries covered by that
contract now have reviewed planning bindings to 154 exact suite cases. Eight
configuration-semantic slices add 67 bindings and six reviewed primary targets;
all remain planning-only without candidate evidence. A separate fail-closed
environment contract now reviews 19 named variables, one dynamic input, five
configuration-discovery paths, all 36 direct `$ENV` source lines, and 22
reference-only Oracle-case bindings without changing the public inventory.
The separate tracefile contract reviews 20 record tags, two lexical rules, all
15 reader matcher lines, all 18 writer emission lines, 36 fixtures, 21
per-record malformed inputs, and 52 reference-only Oracle observations. It
closes the M0 record/malformed inventory but leaves 28 planned M1 tracefile IDs
without exact executable mappings.
The separate diagnostics contract reviews all 32 shared classes, 399 symbol
references, nine control rules, four unclassified failure surfaces, and ten
command exit policies. Its 51 retained observations remain reference-only,
including a `geninfo` startup case intercepted by read-only temporary storage;
all 71 diagnostic and parallel case identities remain planned.
The separate installation contract binds the 321-entry installed tree to nine
exhaustive payload groups and 15 source closures. Canonical paths, SHA-256
file identities, and the legacy man symlink fail closed. All 13 installation
cases remain planned. Four retained report samples bind output trees through
sample metadata and contain the same seven runtime assets without providing
product evidence; directory layout remains an explicit gap because the tree
recorder retains only files and symlinks.
The resource-observation lane retains 13 accepted controlled scale profiles
from the immutable Oracle. Exact input shapes, source-scoped family
cardinalities, branch/MC/DC summary semantics, raw metrics, clean outcomes,
cleanup, and host/runtime identity fail closed. Writable output storage retains
canonical post-generation diagnostics with explicit host-deadline provenance;
retention failure cannot bypass attempted container/temp cleanup. Successful
result validation rejects unreferenced tree entries and symlinks. The canonical
13/13 result remains bound to historical image `sha256:b02cc645...56eb80b7`.
CI separately resolves the closure-verified rebuilt alias to its immutable ID,
rechecks the canonical LCOV executable hash, and validates the 13 ordered
samples-only trees without emitting retained evidence. These are bounded
single-run
Oracle observations, not Ferricov product limits, compatibility evidence, or
performance gates; `M1-MD-020`, `M1-TF-063`, and `M1-TF-064` remain blocked.
M1 must not start until the M0 exit gate and the Week 2 parser gate are
satisfied.

### M1 / v0.1: Tracefile Core

**Target:** weeks 4-7

**Scope**

- Define byte-preserving path and text representations.
- Implement every inventoried LCOV 2.5 tracefile record.
- Implement streaming parse and deterministic serialization.
- Implement coverage invariants, exact counter behavior, and summary totals.
- Add malformed, legacy, current, large, and non-UTF-8 fixtures.
- Add parse/write round-trip properties and parser fuzzing.

**Exit gate**

- All tracefile record and malformed-input cases pass the Oracle.
- Parse-write-parse preserves the semantic model for the complete corpus.
- Deterministic writer cases match the approved canonical form.
- Fuzz targets have no unresolved crash, panic, path, or allocation finding.
- Large-file parsing is no slower than LCOV beyond the performance tolerance;
  target speedup is at least 2x.

**Release claim:** tracefile-core preview only. No drop-in CLI claim.

### M2 / v0.2: `lcov` Manipulation And Shared Runtime

**Target:** weeks 8-13

**Scope**

- Implement common CLI parsing, aliases, configuration precedence, message
  classes, ignore behavior, exit status, temporary directories, and callbacks.
- Implement all non-capture `lcov` operations, including merge, extract,
  remove, list, summary, intersect, subtract, pruning, function mapping,
  substitution, filtering, checksums, test-name handling, and thresholds.
- Implement relevant option/config interactions and failure paths.

**Exit gate**

- Every non-capture `lcov` inventory entry passes its differential cases.
- Coverage models, tracefiles, stdout, stderr, exit status, and file effects
  contain no unexplained differences.
- Large merge/filter operations are at least 2x faster; target is 3-5x.
- Peak RSS is no worse on representative cases and improves on large cases.

**Release claim:** preview compatibility for an explicitly published subset of
`lcov`; no full-suite claim.

### M3 / v0.3: Complete `genhtml`

**Target:** weeks 14-20

**Scope**

- Implement report aggregation, directory/file/source pages, assets, links,
  sorting, navigation, thresholds, precision, source resolution, and themes.
- Implement baseline/differential views, ownership and annotation data,
  callbacks, date bins, frames, gzip, flat/hierarchical modes, detail views,
  condition and MC/DC presentation, and all remaining output modes.
- Add normalized DOM, link graph, asset, source-line state, and screenshot
  comparisons where visuals encode coverage meaning.

**Exit gate**

- Every `genhtml` inventory entry and interaction group passes.
- Coverage totals, thresholds, page graph, anchors, and source annotations have
  no unexplained differences.
- All generated internal links resolve.
- Large default and feature-heavy reports are at least 2x faster; target is
  3-5x, with improved peak RSS.

**Release claim:** `lcov.info` to compatible HTML beta for the published
matrix. This is the first release suitable for external project pilots.

### M4 / v0.4: Complete Capture

**Target:** weeks 21-27

**Scope**

- Implement `geninfo` and `lcov --capture` behavior.
- Cover initial and runtime capture, lone compile-time data, external files,
  symlinks, build/base directories, source resolution, exclusion markers,
  checksums, function/branch/condition/MC/DC data, package workflows, kernel
  workflows, and all compiler-specific behavior in the declared matrix.
- Test GCC and LLVM/gcov-emulation behavior in isolated toolchain images.

**Exit gate**

- Every capture inventory entry passes on every applicable toolchain.
- Captured semantic coverage models match exactly.
- Compiler/version error and warning behavior matches.
- Capture throughput is no worse for any representative fixture and improves
  geometrically across the family.

**Release claim:** primary-command beta for the published Linux/toolchain
matrix.

### M5 / v0.5: Complete Installed Suite

**Target:** weeks 28-31

**Scope**

- Implement `genpng`, `gendesc`, `perl2lcov`, `py2lcov`, `xml2lcov`,
  `xml2lcovutil.py`, and `llvm2lcov`.
- Implement installed support scripts and documented callback protocols.
- Match installation layout, manpages, command names, assets, and config
  discovery.
- Produce Linux and macOS packages and checksums.

**Exit gate**

- Every installed public surface has passing evidence or a reviewed
  not-applicable classification for the declared platform.
- Fresh-machine installation and replacement tests pass.
- Runtime dependencies are documented per feature. Base `lcov`, `genhtml`,
  and `geninfo` workflows do not require Perl; Perl-specific public features
  may require a user-provided Perl runtime if M0 confirms that mechanism.

**Release claim:** full-suite release candidate, not yet stable.

### M6 / v1.0: Qualified Replacement

**Target:** weeks 32-36

**Scope**

- Run the complete upstream-derived, issue-derived, generated, malformed,
  fuzz, compiler, platform, installation, and benchmark matrices.
- Perform reverse review for incorrect totals, false CI success, broken report
  links, path corruption, and hidden performance regressions.
- Pilot real replacement in at least three external projects.
- Resolve every unexplained difference or narrow the declared support matrix.
- Publish compatibility inventory, raw evidence, benchmark report, known
  limitations, provenance, and signed release artifacts.

**Exit gate**

- Every applicable public inventory entry is `pass`.
- No unexplained semantic, output, exit, warning, callback, filesystem, or DOM
  difference remains.
- Every performance-contract gate passes.
- Three external CI replacements complete without a compatibility workaround.
- Documentation, packages, licenses, and evidence are independently reviewed.

**Release claim:** LCOV 2.5 drop-in compatible for the exact published
platform and toolchain matrix.

## 7. Dependency Order

```text
M0 executable contract
  -> M1 model and tracefiles
      -> M2 shared runtime and lcov operations
          -> M3 genhtml
          -> M4 geninfo and capture
              -> M5 auxiliary suite and packaging
                  -> M6 qualification and v1.0
```

`genhtml` and capture may overlap after M2 stabilizes, but they must not create
separate coverage models, configuration engines, error systems, or path
semantics.

## 8. Compatibility Case Design

Each public behavior receives cases from the applicable classes:

- acceptance: valid short, long, positional, config, and environment forms
- rejection: missing values, invalid values, conflicts, unsupported contexts
- equivalence: CLI form versus corresponding `lcovrc` form
- interaction: operation, filter, callback, parallel, and output combinations
- data: line, function, branch, condition, MC/DC, checksum, and test-name data
- filesystem: relative, absolute, symlinked, missing, non-UTF-8, and unusual
  path characters
- failure: exit status, signal, stdout/stderr channel, message class, ignore and
  keep-going behavior
- scale: small, medium, large, many-file, and high-cardinality coverage data

Passing a parser test does not complete an option. The linked case group must
pass end to end.

## 9. Performance Program

Performance work begins with M0 baselines and runs continuously. It is not a
final optimization phase.

- Record wall time, user/system CPU, peak RSS, output bytes/files, throughput,
  worker count, hardware, toolchain, and raw samples.
- Compare optimized builds in the same pinned environment.
- Use startup, tracefile, operation, report, capture, converter, callback, and
  failure-path benchmark families.
- Track per-case regression and family geometric mean.
- Profile only after a reproducible benchmark identifies a bottleneck.
- Reject speedups that alter output meaning, warning behavior, or CI decisions.

## 10. Quality Gates Per Work Slice

Every meaningful slice must include:

1. inventory and requirement references
2. semantic Oracle and fixtures
3. implementation within the declared module boundary
4. focused unit tests
5. differential correctness evidence
6. performance evidence when a hot path changes
7. fuzz/property coverage when parsing or algebra changes
8. SSoT/spec/task updates
9. independent review for Standard or Critical changes

The workspace gate is:

```bash
cargo fmt --all --check
cargo check --workspace --all-targets
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
```

The pinned MSRV must also pass in CI before the first published crate or
binary. Rust 1.85.0 is the current declared MSRV and passes the local workspace
gate; CI keeps it in the required toolchain matrix.

## 11. Risk Register

| Risk | Impact | Control | Decision point |
| --- | --- | --- | --- |
| Hidden option interactions | False compatibility claim | Test-to-inventory mapping and interaction groups | M0 |
| Perl-module callbacks and Devel::Cover data | Pure standalone binary cannot execute existing Perl protocols by itself | Verify subprocess protocol and document optional feature runtime | M0 |
| Historical compiler behavior | Matrix growth and unavailable toolchains | Containerized declared matrix and explicit applicability | M0/M4 |
| HTML nondeterminism | Over-normalization can hide semantic defects | Raw evidence, narrow normalizers, DOM/link/source-state checks | M3 |
| Non-UTF-8 and platform paths | Data corruption or crashes | Byte-preserving model and platform fixtures | M1 onward |
| Parallel performance regression | More workers may be slower or use excessive memory | Scaling benchmarks and RSS budgets | M2-M4 |
| Upstream changes during development | Endless target movement | Keep 2.5 pinned until 1.0; audit newer release separately | after M6 |
| AI-generated false parity | Tests reproduce implementation assumptions instead of upstream behavior | Oracle-first fixtures, reverse tests, independent review | every milestone |

## 12. Go/No-Go Reviews

- **After M0:** stop or re-scope if complete public behavior cannot be
  inventoried or callback compatibility has no defensible implementation.
- **After M1:** stop or redesign if the model cannot represent all tracefile
  semantics without lossy conversion.
- **After M2:** reconsider the product if representative core operations cannot
  meet parity and show meaningful performance improvement.
- **After M3:** begin external promotion only if the HTML workflow is compatible
  and at least 2x faster on large reports.
- **Before M6:** do not enter stable qualification with known primary-command
  gaps.

## 13. Immediate Two-Week Plan

### Week 1: Complete The Executable Contract

- Extend the inventory schema with classification, upstream references,
  behavior groups, dependencies, applicability, and evidence status.
- Review all 10 command inventories and remove generated-token false positives.
- Extract short options, positional forms, config discovery, environment
  variables, tracefile records, error classes, and installation paths.
- Map the 205 upstream test files to public behaviors.
- Draft the callback/runtime and compiler-matrix ADRs.

**Week 1 deliverable:** reviewed compatibility matrix with no unclassified
candidate and a list of unresolved contract decisions.

### Week 2: Baselines And Model Specification

- Generate formal differential suites for startup, help, version, invalid
  options, configuration precedence, and a representative tracefile corpus.
- Add CPU and peak-RSS collection to the evidence runner.
- Capture reproducible upstream correctness and performance baselines. The M0
  aggregate CLI/configuration correctness baseline is retained under
  `compat/correctness/` and remains
  distinct from Ferricov compatibility evidence.
- Retain a source-complete environment and configuration-discovery contract
  independently of the public inventory schema.
- Retain a source-complete tracefile record and malformed-input contract
  independently of the public inventory schema and M1 product evidence.
- Retain a source-complete diagnostic registry, error-control, and exit-policy
  contract independently of command implementation and product evidence.
- Retain a source-complete installation and report-asset contract independently
  of packaging implementation and product evidence.
- Specify the byte-preserving coverage model and tracefile grammar.
- Define M1 acceptance fixtures, property invariants, fuzz targets, and
  benchmarks.

**Week 2 deliverable:** approved model specification, executable M1 test corpus,
and upstream baseline report. Parser implementation starts only after this gate.

## 14. Progress Reporting

Progress is reported by verified behavior, not source lines or parsed options:

- inventory entries classified / total
- public behavior groups with planned cases / total
- behavior groups passing differential evidence / applicable total
- upstream-derived tests passing / applicable total
- benchmark families passing / total
- unresolved semantic differences
- open Critical and Standard review findings

Pre-release notes must state both completed and missing compatibility surfaces.
