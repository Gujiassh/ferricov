# Behavior Planning Contract

`contract.json` is the canonical M0 registry for behavior groups, interaction
planning, and compatibility case groups. It complements the executable-surface
inventory; it does not claim that Ferricov implements or passes any LCOV
behavior.

## Authoring Model

Do not edit `contract.json` directly. It is a deterministic merge artifact.
`generate.py --check` rejects any canonical bytes that do not match the
fragments and current inventory/test-map inputs.

Human-reviewed decisions live under `fragments/authored/`:

- `callback.json`: reviewed callback surfaces and runtime protocols
- `installation.json`: reviewed install, payload, discovery, and safety subjects
- `perl2lcov.json`: reviewed converter runtime, model, and matrix subjects
- `interactions.json`: the required critical interaction domains
- `m0-cli-*-primary.json`: reviewed argparse, direct Getopt, and shared Getopt
  primary plans already exercised by the retained M0 CLI Oracle contract

Machine-generated imports and inventory skeletons live under
`fragments/generated/`. The generator places inventory entries into eight stable
hash buckets per command/config/support responsibility domain. Generated files
are not authoring surfaces and are rewritten from the current inventory.
Every fragment is canonical JSON, validates against
`behavior-contract-fragment.schema.json`, and is limited to 2,000 lines. The
current largest authored fragment is 1,666 lines, below that limit.

The baseline imports the stable test-map behavior registry, imports reviewed
callback/install/converter planning from the normative contract, and creates one
unreviewed acceptance skeleton for each public inventory entry. The reviewed
imports have `evidence_status=none`; they establish planning semantics, not
Ferricov parity.

To replace an inventory skeleton with a reviewed plan, author a case with the
same stable case ID under `fragments/authored/`, change its origin to
`manually_curated`, resolve applicability and relationships, and regenerate.
The generator suppresses only that matching generated skeleton. IDs are unique
across every fragment and registry.

The dependency direction is one-way:

```text
reviewed inventory -> behavior contract -> validation/evidence
```

The inventory owns classification, review status, applicability, runtime
dependencies, and source references. This contract owns behavior groups,
interaction groups, planned cases, and product evidence. Behavior validation
uses inventory entries as its target registry but deliberately ignores any
relationship arrays present there; those arrays are not behavior-contract
inputs and are not projected back from reviewed cases.

## Commands

Rebuild generated fragments and the canonical contract:

```bash
python3 compat/behavior/generate.py
```

Prove generated fragments and canonical bytes are stable:

```bash
python3 compat/behavior/generate.py --check
```

Validate the current structure while reporting explicit review debt without
failing on that debt:

```bash
python3 compat/behavior/validate.py --mode current
```

Apply the strict M0 planning gate:

```bash
python3 compat/behavior/validate.py --mode m0-ready
```

Run focused positive and mutation guards:

```bash
python3 -m unittest compat/behavior/test_validate.py
```

## Readiness Rules

`m0-ready` requires a reviewed primary case group for every applicable public
inventory entry and a reviewed critical group for every interaction domain:

- `option_option`: at least two command-option members
- `option_config`: at least one command option and one `lcovrc` entry
- `callback`: a callback-protocol subject and an option or support script
- `error_control`: an error-class subject and a controlling option, config, or
  callback-protocol subject

The four required domains now have reviewed members and reciprocal planning
cases in `interactions.json`. Their cases retain `evidence_status=none`: this
closes interaction planning only, not differential evidence or product
compatibility.

The three M0 CLI primary fragments review 40 public entries and bind them to
154 exact cases in the core, default parser-policy, and POSIX parser-policy
suites. These cases use `evidence_status=planned` and retain empty evidence
arrays because the retained Oracle observations are reference baselines, not
Ferricov differential results. `m0-ready` now rejects the remaining 468 public
entries without reviewed primary case groups.

## Evidence Rules

Upstream test links are planning sources only. They must resolve to a reviewed
`public_behavior` mapping in `upstream-test-map.json`; fixture, internal, or
unreviewed mappings cannot prove public semantics.

Suite and evidence links may reference only suites with
`evidence_scope=compatibility`. Harness self-test suites are rejected as product
evidence. A `pass` or `fail` additionally requires a real differential result
whose scope, suite/case identity, execution fields, comparison dimensions,
normalizers, and outcome match the contract entry. Reference and candidate
executable identities must differ, and every retained artifact must exist below
the result directory with its recorded size and SHA-256 digest.
