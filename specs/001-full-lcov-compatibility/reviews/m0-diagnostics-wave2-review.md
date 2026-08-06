# M0 Diagnostics Wave2 Review Note

## Scope

Lane-owned diagnostics/parallel wave2 adds a second Oracle-reference batch under
`compat/diagnostics/**` plus this lane review note. No Ferricov parser/model,
shared tasks, root README, SSoT, tracefile fixtures, behavior, installation, or
Rust trees were modified.

## Provenance contract (inherits accepted wave1)

- clean in-container `env -i` with only declared variables (case-local extras
  such as `POSIXLY_CORRECT` / `LCOV_HOME` remain declared clean-env values)
- `stdin=subprocess.DEVNULL` on all docker launchers and probes
- named-container force cleanup; `docker ps` observer errors fail closed
- `execution_manifest` with locale/timezone, executable hashes, tool versions,
  and package availability
- pinned image `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- upstream LCOV `v2.5` commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`
- independent raw stdout/stderr/tree/exit facts plus refreshed-self-hash mutation
  rejection
- `evidence_status=oracle_reference`, `product_compatibility_evidence=false`,
  planned catalog remains `planned`

## Delivered

- 32 Docker-captured Oracle observations under `compat/diagnostics/wave2/`
- Durable capture script: `compat/diagnostics/wave2/scripts/capture_wave2.py`
- Contract/schema/test bindings with independent expected-case tables and reverse
  mutation coverage
- Prior 169 observations and all wave1 artifacts preserved; no duplicate case IDs

## Planned IDs newly bound by wave2 (30)

- `DIAG-REGISTRY-001`
- `DIAG-IGNORE-PREFIX-PROFILE-001`
- `DIAG-ENV-POSIX-PROFILE-001`
- `DIAG-ENV-CLEAN-001`
- `DIAG-ENV-SHOW-LOCATION-001`
- `DIAG-ENV-PRECEDENCE-001`
- `DIAG-ENV-LCOV-HOME-001`
- `DIAG-ENV-LCOV-VALIDATE-001`
- `DIAG-ENV-ALLOWLIST-001`
- `DIAG-CONFIG-DISCOVERY-001`
- `DIAG-CONFIG-EXPLICIT-001`
- `DIAG-CONFIG-INCLUDE-001`
- `DIAG-CONFIG-EARLY-ERROR-001` (additional executable depth; historical bindings retained)
- `DIAG-CONFIG-UNKNOWN-KEY-001` (additional executable depth)
- `DIAG-CONFIG-ENV-EXPAND-001` (additional executable depth)
- `DIAG-RAW-PERL-001`
- `DIAG-PYTHON-TRACEBACK-001`
- `DIAG-DEPENDENCY-GENPNG-001` (GD-present branch only)
- `DIAG-CALLBACK-FINALIZE-FAIL-001`
- `DIAG-CALLBACK-CLEANUP-001`
- `PAR-CHILD-EXIT-001`
- `PAR-CALLBACK-LIFECYCLE-FAIL-001`
- `PAR-CALLBACK-STATE-001`
- `PAR-PAYLOAD-MISSING-001`
- `PAR-MSG-LOG-001`
- `PAR-MESSAGE-ORDER-001`
- `PAR-MEMORY-ADMISSION-001`
- `PAR-MEMORY-FALLBACK-001`
- `PAR-LCOV-CAPTURE-STATUS-001`
- `PAR-PARTIAL-COMMIT-001`

## Explicit residual unbound planned IDs (12)

These remain `planned` with no wave2 executable binding:

- `PAR-GENINFO-CHILD-STOP-001`
- `PAR-GENINFO-CHILD-EXIT-ORACLE-001`
- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001` (Ferricov-approved pair; product false)
- `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001` (Ferricov-approved pair; product false)
- `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001` (Ferricov-approved pair; product false)
- `PAR-CHILD-SIGNAL-001`
- `PAR-FORK-RETRY-001`
- `PAR-PAYLOAD-CORRUPT-001`
- `PAR-UNKNOWN-CHILD-001`
- `PAR-PARENT-DEATH-001`

## Contract totals after wave2

- planned cases: 71 (still `planned`; no product evidence)
- oracle observations: 201 total
  - 143 historical correctness/tracefile references (pre-wave1 inventory + later
    trace expansions retained as prior 169 minus wave1's 26)
  - 26 wave1 diagnostics references
  - 32 wave2 diagnostics references
- product_compatibility_evidence: false
- oracle_observation_evidence_status: oracle_reference

## Evidence policy

All wave2 results remain `oracle_reference` only. They must not be promoted to
Ferricov product compatibility without a later differential against a distinct
Ferricov executable. Ferricov-parity planned IDs stay unbound and planned.

## Recapture

```sh
python3 compat/diagnostics/wave2/scripts/capture_wave2.py
python3 compat/diagnostics/contract.py \
  --upstream-root /path/to/lcov-upstream-reference \
  --write
python3 -m unittest compat.diagnostics.test_contract
```
