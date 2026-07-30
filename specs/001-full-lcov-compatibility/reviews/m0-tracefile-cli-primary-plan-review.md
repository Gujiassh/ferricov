# M0 Tracefile CLI Primary Plan Review

## Decision

Accepted as M0 behavior planning only. This bounded slice replaces exactly four
generated primary skeletons: `command.lcov.option.add-tracefile`,
`command.lcov.option.output-file`,
`command.lcov.option.no-function-coverage`, and
`command.lcov.option.mcdc-coverage`.

The slice raises reviewed primary coverage from 69 to 73 and reduces explicit
M0 primary-review gaps from 462 to 458. It does not add Ferricov execution,
product compatibility evidence, a compatibility-suite binding, or M1
authorization.

## Semantic Oracle

Each reviewed case must satisfy all of these invariants:

1. Its stable primary case ID replaces exactly one generated inventory skeleton
   and retains the original public target and inventory source references.
2. Its description states only exact retained argv, output-path, exit, stream
   hash, output hash, or reviewed upstream-reference facts.
3. `origin` is `manually_curated`, `review_status` is `reviewed`, and
   `evidence_status` remains `none`.
4. `evidence` and `suite_cases` remain empty. Oracle references are not product
   evidence and are not rebound as compatibility-suite cases.
5. Summary, branch-coverage, and ignore-errors retain their existing primary
   ownership; this fragment contains only the four named targets.
6. Deterministic generation removes only the four matching skeletons, current
   validation passes, and M0 readiness still fails on exactly 458 gaps.

## Retained Planning Sources

| Planning fact | Exact retained source | Use in this slice |
| --- | --- | --- |
| Eight successful canonical rewrites carry `--add-tracefile input.info --output-file output.info` | `compat/fixtures/m0-tracefiles/oracle-cases.json` and the matching `canonical_rewrite` entries in `compat/tracefile/v2.5.json` | Bounds the add-tracefile and output-file descriptions to exact argv, zero exits, named output, and retained hashes. |
| Five of those canonical rewrites carry `--no-function-coverage` | The same exact Oracle case and tracefile-contract entries | Bounds the no-function-coverage description to observed argv, zero exits, and output hashes; no broader filtering claim is made. |
| Two of those canonical rewrites carry `--mcdc-coverage` | The same exact Oracle case and tracefile-contract entries | Bounds the mcdc-coverage description to observed canonical rewrite behavior; summary observations are excluded. |
| Eight successful diagnostic recovery observations also carry add/output/no-function options | Matching `tracefile:*` entries in `compat/diagnostics/v2.5.json` | Used only to verify the reference boundary. They remain `oracle_reference` observations and are not assigned as evidence or suite cases. |
| Public upstream drivers for function rewriting, add/prune, function mapping, tracefile formatting, and set operations | Reviewed `public_behavior` entries in `compat/inventory/tests/upstream-test-map.json` | Added as planning links only; they do not prove Ferricov compatibility. |

The authored source is
`compat/behavior/fragments/authored/m0-tracefile-cli-primary.json`.
`compat/behavior/generate.py` is the only writer used for the generated
inventory fragments and aggregate behavior contract.

## Evidence Boundary

The tracefile contract records Oracle reference observations and the diagnostics
contract records `oracle_observation_evidence_status=oracle_reference`. Both
contracts keep `product_compatibility_evidence=false`; diagnostics product
evidence is empty. The authored behavior cases therefore use
`evidence_status=none`, not `planned`, `pass`, or `fail`, and keep both
`evidence` and `suite_cases` empty.

The focused tests cross-check the exact eight canonical IDs, the five
no-function argv observations, the two MC/DC argv observations, all eight
diagnostic recovery references, every linked upstream test classification, and
the complete source-reference list for each authored case against its reviewed
inventory target. Mutation guards reject source-reference removal or field
drift, evidence-status promotion, product evidence, and suite bindings in the
four-case authored fragment.

## Review Result

| Area | Result | Evidence |
| --- | --- | --- |
| Goal alignment | pass | Exactly four named public primary skeletons are replaced; summary, branch-coverage, and ignore-errors primary cases are unchanged. |
| User-visible flow | not applicable | No executable implementation or runtime behavior changes. |
| Architecture and ownership | pass | Human review lives in one authored fragment; generated skeleton buckets and the aggregate contract are generator outputs. |
| Data and evidence contracts | pass | Four unique primary targets exactly retain their complete reviewed inventory source references and remain reference-only with empty evidence and suite arrays; source removal/change and evidence-boundary mutations are rejected. |
| Implementation quality | pass | The fragment follows the existing authored format and remains below the 2,000-line authoring limit. |
| Verification and evolution | pass | Generation, byte-stability, current validation, focused tests, retained tracefile/diagnostics checks, and the repository verifier pass while M0 reports 458 honest gaps. |

## Verification

```bash
python3 compat/behavior/generate.py
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current
python3 compat/behavior/validate.py --mode m0-ready
python3 -m unittest compat/behavior/test_validate.py
python3 compat/fixtures/m0-tracefiles/validate.py
python3 compat/tracefile/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 compat/diagnostics/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest \
  compat/tracefile/test_contract.py \
  compat/diagnostics/test_contract.py
python3 compat/verify.py --skip-oracle
```

Observed result: 531 public entries, 531 primary plans, 73 reviewed primary
plans, 458 remaining primary-review gaps, all four critical interaction domains
reviewed, and no Ferricov product evidence. Current validation passes. The
strict M0-ready command fails only because those 458 public entries still lack
reviewed primary cases.

## Residual Risk And Next Step

These plans do not prove merge meaning, complete function or MC/DC filtering,
summary totals, diagnostic recovery, output-path failure behavior, or Ferricov
parity. Continue M0 with another bounded exact-reference primary review slice;
do not begin M1 until the full M0 exit gate is accepted.
