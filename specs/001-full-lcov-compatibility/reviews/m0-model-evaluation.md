# M0 Implementation Model Evaluation

## Status And Scope

This is an interim engineering evaluation of model-produced implementation
slices for Ferricov M0. It records the DeepSeek first-pass lanes, one controlled
DeepSeek inventory rework, and the controller-selected Codex replacement route.
The Codex replacement route remains separately tracked; this document records the accepted DeepSeek bounded lane and does not attribute controller work to the model.

This evaluation answers one question: did a model-produced implementation slice
meet its assigned ownership boundary, semantic requirements, review findings,
and required gates? It is not LCOV compatibility evidence. Mechanical counts,
unit-test success, model acceptance rate, cost, and elapsed time do not increase
Ferricov's compatibility status. Compatibility remains governed by
[the compatibility contract](../../../docs/ssot/compatibility-contract.md) and
[the execution plan](../plan.md).

## Acceptance Method

A slice is accepted only when all of these conditions hold:

1. The implementation stays inside its assigned ownership and file boundary.
2. The observable contract is derived from pinned LCOV 2.5 evidence rather
   than inferred from documentation names or generated structure.
3. Schemas, generated artifacts, source references, and runtime semantics agree
   end to end.
4. Required focused, workspace, negative, and integration gates pass.
5. Independent review has no unresolved Critical finding.
6. The controller can identify a coherent commit boundary without unrelated or
   rejected changes.

A slice that produces useful code or passing local tests but fails any of these
conditions is still rejected.

## Evaluation Summary

| Attempt | Lane | Decision | Approximate wall time | Cost |
| --- | --- | --- | ---: | ---: |
| DeepSeek first pass | inventory | reject | 12 min | included in first-pass total |
| DeepSeek first pass | differential runner | reject | 16 min | included in first-pass total |
| DeepSeek first pass | reproducible Oracle | reject | 20 min | included in first-pass total |
| DeepSeek controlled rework | inventory only | reject | 13 min 25 s | $17.841925 |
| DeepSeek v4-pro bounded VER lane | M1-TF-007 implementation draft | aborted/reject | ~17 min | not recorded |

The three first-pass lanes cost approximately $44.92 in total. The controlled
inventory rework recorded `duration_api_ms=781635` and result
`duration_ms=804657` in Claude session
`7af1bc77-ca3f-45c9-83c4-6e7cf688b259`.

Aggregate DeepSeek results for this evaluation:

- first-pass acceptance: 0 of 3, or 0%;
- controlled-rework acceptance: 0 of 1, or 0%;
- bounded configuration acceptance: 1 of 1 after controller rework;
- bounded VER-lane acceptance: 0 of 1 (aborted before evidence handoff);
- total attempted implementation slices: 6; accepted slices: 1; acceptance rate: 16.7%;
- total estimated cost: approximately $62.76 plus the unpriced aborted lane;
- total approximate wall time: approximately 78 minutes.

The cost total is approximate because the first-pass value is approximate. The
wall-time total uses the result duration for the controlled rework, not API time.

## Evidence Provenance

The controller retained the raw DeepSeek/Claude transcripts and command results
for these implementation sessions:

- differential-runner first pass:
  `703bb5c1-63cb-4485-9881-ed61fbf3ef3e`;
- reproducible-Oracle first pass:
  `85d6728c-645c-4d12-977f-e82489a95a1d`;
- controlled inventory rework:
  `7af1bc77-ca3f-45c9-83c4-6e7cf688b259`.

The first-pass inventory decision, lane timing, and first-pass aggregate cost
come from the controller evaluation ledger. The controlled-rework cost and
duration come from controller-supplied invocation-result metadata; those fields
are not embedded in the Claude transcript, whose timestamps include queue and
permission time and are not used as attempt wall time. Repository-facing
failure counts below were independently rerun against the resulting worktree.
Session transcripts are implementation provenance, not project compatibility
evidence.
First-pass findings describe the evaluated delivery snapshot. Later controller
or Codex changes may already address some of them; they MUST NOT be reported as
current-tree defects without a fresh review.

## First-Pass Findings

### Inventory Lane

**Decision: reject.** The first pass did not establish an acceptable review
overlay and generated inventory boundary. It reported 12 shards, but the actual
directory contained 15 JSON files, including a stale 2,735-line shard and
duplicate positional/support shards. The generated inventory still exposed the
old 394-option and 130-config counts without an independent reviewed status.

The implementation also conflated `review_status` with classification, modeled
singular `--ignore-error` tokens incorrectly, used subset rather than exact
source assertions, claimed the pinned upstream checkout was unavailable when it
existed and was clean, weakened Clippy with allow flags, and edited runner files
outside the assigned inventory scope. It was therefore limited to the
controlled inventory-only rework evaluated below.

### Differential-Runner Lane

**Decision: reject.** The first-pass runner changed safety-critical process and
evidence behavior without proving the actual runtime semantics.

Critical findings:

1. Blocking stdout and stderr collection could deadlock when a child filled a
   pipe before exit.
2. Recorded executable or image identity could differ from the process that was
   actually executed under its effective path, work directory, user, mounts,
   and Docker context.
3. Cleanup and observer failures could be treated as successful absence checks,
   making descendant cleanup fail open.
4. Signal and reaping fields described outcomes that were not directly
   observed, so the retained evidence could fabricate lifecycle semantics.
5. The required real Docker end-to-end case was skipped. Unit-level process
   tests could not prove environment propagation, immutable image execution,
   timeout behavior, or cleanup under Docker.

The claimed `POSIXLY_CORRECT` Docker case only echoed an environment value,
skipped when Docker or the image was unavailable, and did not prove an actual
parser-behavior change.

These defects affect process safety and evidence identity, not formatting. The
lane cannot be accepted until a replacement passes real local and Docker
end-to-end cases plus mutation and cleanup guards. The affected code surface is
[the differential runner](../../../compat/oracle/src/differential.rs) and its
process/evidence modules.

### Reproducible-Oracle Lane

**Decision: reject.** The first-pass Oracle work did not produce an honest,
reproducible, content-addressed M0 Oracle.

Critical findings:

1. Evidence remained bound to local image ID
   `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`,
   which had no `RepoDigest` and was not a retained OCI artifact.
2. The build definition was not reproducible across clean no-cache builds.
   Mutable package and documentation inputs remained in the build path.
3. Manifest fields overstated what had actually been observed or verified,
   including the distinction between a local Docker image ID and a publishable
   OCI digest.
4. Disabling intersphinx and changing installed documentation made the Oracle
   payload semantically different instead of reproducing the pinned upstream
   installation.
5. No accepted two-build comparison proved equal package-closure bytes,
   installed-tree bytes, executable identities, and manifest observations.

The implementation also relaxed missing provenance labels and mismatches into
warnings and trusted claim-bearing lock booleans instead of recomputing their
observed identities. Disabling intersphinx removed the pinned Python
`objects.inv` relationship and changed generated HTML/man date content, which
is public installed-documentation drift rather than a valid normalization.

The replacement must preserve installed upstream semantics while making every
external input explicit. Build determinism cannot be achieved by silently
removing installed content.

## Controlled Inventory Rework

### Positive Mechanical Evidence

The controlled rework made measurable progress:

- 584 generated entries were represented across command options, config keys,
  support scripts, and positional arguments;
- 37 JSON shards were generated, with every shard below 1,800 lines;
- `cargo test -p ferricov-oracle --lib -- inventory` passed 35 of 35 tests;
- two regenerations produced inventory SHA-256
  `e3215d85196a1dafb5f147ad47de8074927e213343205487313823be4fdb2606`;
- two singular `--ignore-error` tokens each recorded a default-profile unique
  abbreviation and a `POSIXLY_CORRECT` rejection, for four profile observations.

These results prove bounded generation, local Rust test coverage, deterministic
bytes for the produced artifact, and four parser observations. They do not prove
that the artifact is valid, reviewed, applicable, or accepted.

### Hard Blocking Findings

**Decision: reject.** The controller reran the acceptance checks rather than
accepting the completion report.

| Finding | Evidence | Consequence |
| --- | --- | --- |
| Review-overlay shards violate their schema | 1,391 Draft 2020-12 validation errors across 37 shards | The review input is not a valid contract |
| Generated inventory violates the main schema | 736 validation errors | The canonical output cannot be consumed safely |
| Main verification fails | `python3 compat/verify.py --skip-oracle` exits 1 | The repository gate is red before Oracle execution |
| Applicability is still unresolved | 575 of 584 entries retain unreviewed applicability | A classification label is not a reviewed runtime applicability decision |
| Documentation/help tokens were promoted without parser evidence | Six options classified public have no parser-definition source | Auto-abbreviations and documentation names became false public options |
| Dynamic config source is incomplete | `lcovrc.config-file` omits `lib/lcovutil.pm:1400` | The `config_file` runtime include behavior is not source-complete |
| Verification integration is stale | `compat/verify.py` still invokes the old three-argument generator and expects 33 generated tokens | The new four-argument overlay path and 35-token result are not verified |
| Ownership boundary was crossed | Differential runner files were modified during inventory-only rework | The slice is not independently reviewable or safely mergeable |

The six false-public entries are:

- `command.lcov.option.build-dir`
- `command.lcov.option.history`
- `command.genhtml.option.erase-function`
- `command.genhtml.option.no-source`
- `command.geninfo.option.mcdc`
- `command.llvm2lcov.option.output`

The relevant artifacts are the
[review-overlay schema](../../../compat/schema/inventory-review-overlay.schema.json),
[inventory schema](../../../compat/schema/inventory.schema.json),
[generated inventory](../../../compat/inventory/v2.5.json), and
[verification entry point](../../../compat/verify.py).

### Reproducible Rejection Checks

The core failure evidence can be reproduced with:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

schema = json.loads(
    Path("compat/schema/inventory-review-overlay.schema.json").read_text()
)
errors = 0
for path in sorted(Path("compat/inventory/review").glob("*.json")):
    document = json.loads(path.read_text())
    errors += len(list(Draft202012Validator(schema).iter_errors(document)))
print(errors)
PY

python3 compat/verify.py --skip-oracle
cargo test -p ferricov-oracle --lib -- inventory
git diff --check
```

The first command reports 1,391. The second exits 1. The Rust inventory tests
pass, demonstrating why local unit success must not override schema and
integration failures.

## Codex Replacement Route

The controller selected a Codex-owned replacement route. Its purpose is not to
repair completion claims; it is to re-establish one accepted slice at a time
from the pinned requirements and negative findings above.

1. Quarantine or remove rejected DeepSeek changes before attributing later gate
   results to Codex.
2. Rebuild only one bounded lane at a time with an explicit file boundary.
3. Define semantic invariants and negative cases before implementation.
4. Make generated data, schemas, validators, and the main verification command
   agree in the same slice.
5. Require real runtime evidence for process, Docker, and reproducibility claims.
6. Run an independent Critical review and return findings to the implementing
   owner for rework.
7. Accept only a coherent slice whose focused, workspace, integration, and
   reverse gates all pass.

Codex final data is recorded in the bounded VER lane below using the same
controller acceptance criteria.

## DeepSeek V4 Pro Bounded Configuration Lane

The controller dispatched a fresh implementation-only lane to
`deepseek-v4-pro` after the previous evaluation's four rejected attempts. The
brief assigned exactly 17 `lcovrc` primary plans and permitted only one authored
fragment plus the derived behavior contract. DeepSeek first stopped on a real
duplicate-target conflict (`lcovrc.branch-coverage` already belonged to the
existing configuration fragment); the controller replaced that target with
`lcovrc.fork-fail-timeout`, then resumed the same bounded lane.

DeepSeek produced the authored fragment and regenerated contract with 17 unique
planning-only cases and no boundary violations. The controller independently
reworked descriptions that inferred downstream effects, added the invariant test,
and updated SSoT/spec/changelog records. After that rework, the following gates
passed: 44 behavior tests, deterministic generation, current validation at
`107/424`, `compat/verify.py --skip-oracle`, Rust fmt/check/106 tests/clippy,
source closure for all 33 config references, and `git diff --check`. No Oracle
capture, product evidence, or M1 authorization was claimed.

**Decision: accepted after controller rework and hosted CI.** This is an
accepted implementation contribution, not autonomous model acceptance: the
controller owns semantic review, test additions, documentation, commit, push,
and hosted CI. The implementation-only worker did not commit or push. The
accepted configuration slice is on commit `2ae34280355aaa3583258c53c7246589a9d2a690`;
the follow-up tracefile documentation/resource-contract correction is on
`eb19e73edb7b82caf0adbb8d549d28c100157ad7`. Hosted CI run
`30805082580` passed all four jobs, including rebuilt Oracle and clean Docker
execution.

## DeepSeek V4 Pro Bounded VER Lane

The controller dispatched a second `deepseek-v4-pro` implementation-only lane for
`M1-TF-007` after writing an explicit brief with semantic invariants, an
allowlist, and stop conditions. The worker produced only an unverified draft of
three fixtures and generated case files, then stalled before Oracle capture,
contract regeneration, tests, or a structured handoff. The controller
interrupted it after approximately 17 minutes, restored the worktree to
`0a0c0cc`, and recorded the rejection in
[`m0-tracefile-ver-agent-review.md`](m0-tracefile-ver-agent-review.md).

This attempt demonstrates that `deepseek-v4-pro` is useful for bounded drafting
but is not reliable as an autonomous evidence/contract implementer. The
controller therefore takes over the VER lane manually; the draft does not count
toward accepted implementation output.

## Codex Bounded VER Lane

The controller implemented the `M1-TF-007` lane after rejecting the incomplete
worker draft. The accepted slice adds three VER fixtures and one canonical
rewrite case, captures four new observations from the pinned LCOV 2.5 Oracle,
and updates the generated manifest, baseline, schema, contract, tests, and
controller-owned SSoT/spec records. All 59 prior observations were compared
byte-for-byte and remained unchanged.

Evidence and gates passed:

- `python3 compat/fixtures/m0-tracefiles/validate.py`: 42 fixtures and 63 observations;
- `python3 compat/tracefile/contract.py --write`: 20 records, 15 reader lines, 18 writer lines;
- `python3 -m unittest compat.tracefile.test_contract`: 16/16;
- `python3 compat/verify.py --skip-oracle`: pass with product compatibility still false;
- `python3 compat/behavior/validate.py --mode current`: 531 public, 107 reviewed, 424 gaps.

The pinned outcomes are: equal repeat accepted, different repeat exits 1 with
`expected to set version ID at most once`, independent source versions accepted,
and canonical output retains one `VER`. No Ferricov parser or product evidence
was added.

**Decision: accepted as a controller-owned implementation slice.** It is not
DeepSeek implementation credit; the model lane remains rejected/aborted.

## Comparison Metrics

| Metric | DeepSeek observed | Codex |
| --- | --- | --- |
| Attempted implementation slices | 6 | 1 |
| Accepted slices | 1 (after controller rework) | 1 controller-owned slice |
| Acceptance rate | 16.7% (1 of 6) | 100% of the one reviewed slice |
| Critical findings and required rework | Four prior attempts rejected; accepted config lane required duplicate-target correction and controller wording/test/doc rework; VER lane aborted before evidence handoff and draft crossed into unresolved repeated-section semantics | Fixed optional M0 mapping handling and synchronized generated counts/hashes; no product code changed |
| Focused gate results | v4-pro lane accepted after 44 behavior tests, generation/current validation, and source closure passed | VER lane accepted after 4 pinned Oracle observations, 16 contract tests, fixture/baseline validation, and `compat/verify.py --skip-oracle` |
| Workspace/integration gate results | Rust fmt/check/106 tests/clippy passed; hosted CI run `30805082580` passed all four jobs | Python/contract gates passed; Rust/hosted CI pending |
| Wall time | approximately 61 min | controller implementation time not tracked as model cost |
| Cost | approximately $62.76 | no model cost; controller execution |

Future comparisons MUST report accepted slices, Critical findings, rework
cycles, exact gate results, wall time, and cost. Source lines changed, tokens
consumed, or tests written are supporting observations, not acceptance metrics.

## Decision

The four historical DeepSeek implementation attempts remain rejected. The
fifth `deepseek-v4-pro` attempt is accepted only as the implementation portion
of the bounded configuration lane after controller rework and independent
gates; the sixth VER lane was aborted and rejected before evidence handoff. No
model-produced slice may support an M0 or compatibility claim without controller
acceptance.

The useful model outputs are the negative findings, bounded test ideas, and
mechanical inventory observations. They guide controller-owned implementation
but do not transfer implementation credit. The Codex VER replacement is
accepted below only after independent evidence and gates.

The model worker made no commit or push; the controller committed and pushed the accepted slices after review.
