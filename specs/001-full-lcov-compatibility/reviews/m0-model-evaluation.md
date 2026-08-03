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

The three first-pass lanes cost approximately $44.92 in total. The controlled
inventory rework recorded `duration_api_ms=781635` and result
`duration_ms=804657` in Claude session
`7af1bc77-ca3f-45c9-83c4-6e7cf688b259`.

Aggregate DeepSeek results for this evaluation:

- first-pass acceptance: 0 of 3, or 0%;
- controlled-rework acceptance: 0 of 1, or 0%;
- total acceptable implementation rate: 0 of 4;
- total estimated cost: approximately $62.76;
- total approximate wall time: 61 minutes.

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

Codex final data is intentionally pending. This document MUST be updated only
after the controller accepts or rejects a concrete Codex slice using the same
criteria.

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

## Comparison Metrics

| Metric | DeepSeek observed | Codex |
| --- | --- | --- |
| Attempted implementation slices | 5 | pending |
| Accepted slices | 1 (after controller rework) | pending |
| Acceptance rate | 20% (1 of 5) | pending |
| Critical findings and required rework | Four prior attempts rejected; v4-pro lane required duplicate-target correction and controller wording/test/doc rework | pending |
| Focused gate results | v4-pro lane accepted after 44 behavior tests, generation/current validation, and source closure passed | pending |
| Workspace/integration gate results | Rust fmt/check/106 tests/clippy passed; hosted CI run `30805082580` passed all four jobs | pending |
| Wall time | approximately 61 min | pending |
| Cost | approximately $62.76 | pending |

Future comparisons MUST report accepted slices, Critical findings, rework
cycles, exact gate results, wall time, and cost. Source lines changed, tokens
consumed, or tests written are supporting observations, not acceptance metrics.

## Decision

The four historical DeepSeek implementation attempts remain rejected. The
fifth attempt using `deepseek-v4-pro` is provisionally accepted only as the
implementation portion of the bounded configuration lane after controller
rework and independent gates. No model-produced slice may support an M0 or
compatibility claim without controller acceptance.

The useful outputs are the negative findings, bounded test ideas, and mechanical
inventory observations. Those inputs may guide the Codex replacement, but they
do not transfer implementation credit or acceptance. Codex status remains
pending until separately reviewed evidence is recorded here.

The model worker made no commit or push; the controller committed and pushed the accepted slices after review.
