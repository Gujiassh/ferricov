# M0 Tracefile Writer/Converter Wave 2 Review Note

Status: lane implementation complete (Oracle/contract evidence only)
Branch worktree: `/tmp/ferricov-trace-writer-wave2` (from `e4d5264`)
Scope: M1-TF-041 / 042 / 043 / 044 / 045 / 046 / 050 / 051 / 052 / 060 / 061
`product_compatibility_evidence`: **false** (unchanged)
M1 / Ferricov parser-model: **not unlocked**

## Ownership

Lane-owned paths only:

- `compat/fixtures/m0-tracefiles/**` (writer fixtures, generator, capture pin, validators, tests, baseline/cases/manifest)
- `compat/tracefile/contract.py`, `compat/tracefile/v2.5.json`, `compat/tracefile/test_contract.py`
- `compat/schema/tracefile-contract.schema.json`
- `specs/001-full-lcov-compatibility/tracefile-grammar.md` inventory/blocker slice
- this review note

Not modified: crates, behavior/diagnostics/installation lanes, shared `tasks.md`, README, docs/ssot.

## Evidence package

| Item | Value |
| --- | --- |
| Writer fixtures | 13 under `fixtures/writer/` |
| Writer oracle cases | 17 (`WRITER_CASE_IDS`) |
| Total fixtures / cases | 137 / 271 |
| Baseline file SHA-256 | `94787d0820a228e716954961fb7c611af807721e3a547b65cec5ae4dcb89fb4a` |
| Cases SHA-256 | `3b31382fc6239fb447fd92f8d21694a6957e3c0472ef227baf12da31b7ee5503` |
| Manifest SHA-256 | `e6e6e3efa28a1f8c82cb5892c62b414737f26af973defe661d91c2409aeffd5a` |
| TF-030 registry SHA-256 | `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c` (unchanged) |
| Oracle pin | LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, image `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e` |

## Capture method

1. Regenerated fixtures/manifest/cases via `python3 generate.py`.
2. Selective Docker capture of writer prefixes (`writer-`, `gzip-`, `converter-coverage.`) into `/tmp/ferricov-writer-only-baseline.json` (17 cases).
3. Composed new `oracle-baseline.json` by **appending** writer observations in `oracle-cases.json` order while keeping all previous 254 observations byte-identical as JSON objects.
4. Did **not** use TF-030-gated `--merge-into` for writer cases (that path remains exact-15 TF-030 only).

Retained comparison vs HEAD baseline:

- `common=254 changed=0 removed=0 added=17`

Relative to the accepted wave2 254-observation set, writer/converter is purely additive.

## Blocker → case binding

| Requirement | Fixture / case evidence |
| --- | --- |
| M1-TF-041 ordering | `writer-order-core.canonical`, `writer-mcdc-groups.canonical` |
| M1-TF-042 summaries | `writer-summaries.canonical` |
| M1-TF-043 comments/checksum drop | `writer-comments.canonical` |
| M1-TF-044 forbidden records | `writer-forbidden.canonical` |
| M1-TF-046 repeated write | `writer-fixedpoint.repeated-write` |
| M1-TF-050 xml2lcov | `converter-coverage.xml2lcov` |
| M1-TF-051 py2lcov | `converter-coverage.py2lcov-no-functions`, `converter-coverage.py2lcov-with-functions` |
| M1-TF-060 gzip transport | `gzip-valid.summary`, `gzip-plain.write-gz`, `gzip-corrupt.summary`, `gzip-empty.summary`, `gzip-valid.missing-gzip` |

Exact requirement bindings live in `compat/tracefile/contract.py` `EXACT_CASE_REQUIREMENTS` for the 14 writer cases above. Three retained captures remain observational-only (no exact mapping):

| Observational capture | Partial identity (blocked) |
| --- | --- |
| `writer-fixedpoint.canonical` | M1-TF-045 needs multi-corpus parse-write-parse |
| `converter-coverage.canonical-rewrite` | M1-TF-052 needs semantic no-loss snapshots |
| `writer-non-utf8.canonical` | M1-TF-061 needs full non-UTF-8 field matrix |

M1-TF-045 / M1-TF-052 / M1-TF-061 / M1-TF-063 / M1-TF-064 remain unbound.

## Independent validators / reverse mutations

- Structured section-model semantic predicates in `validation_common.py` (not substring-only).
- Identity self-hash refresh checks plus poisoned-hash rejection for every writer observation.
- Focused reverse mutation suite: `WriterTracefileMutationTests` in `test_validate.py`.
- Contract mapping suite: `test_writer_mapping_is_exact_and_source_scoped` in `test_contract.py`.
- Existing TF-030 mutation/merge gates remain green against the expanded baseline (merge baseline pin updated to new canonical SHA; TF-030 selection still exact 15).

## Residual risks

1. Writer capture used selective compose rather than full recapture of all 271 cases; retained 254 objects were verified equal to HEAD baseline, but a future full recapture could still surface nondeterministic stderr outside writer if environment drifts.
2. `gzip-valid.missing-gzip` uses a shell PATH sandbox rather than a dedicated container without gzip; Oracle diagnostic is pinned, but the PATH construction is host/container-layout sensitive.
3. Converter cases stage real XML plus companion `mod.py`; path forms differ between xml2lcov (`mod.py`) and py2lcov-with-functions (`./mod.py`) by Oracle design.
4. Remaining named TF blockers outside this wave (`M1-TF-063`, `M1-TF-064`, and any unbound partials) stay open.
5. No M0 go/no-go and no Ferricov parser/model authorization is implied by this lane.
