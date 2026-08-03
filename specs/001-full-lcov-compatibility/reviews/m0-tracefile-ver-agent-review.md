# M0 Tracefile VER Worker Review

## Decision

**Rejected/aborted.** The `deepseek/deepseek-v4-pro` implementation-only worker
was assigned the bounded `M1-TF-007` lane from
[`m0-tracefile-ver-agent-brief.md`](m0-tracefile-ver-agent-brief.md) at starting
SHA `0a0c0cc2443598bd9dd239742e1dd059e2926419`. It ran for approximately 17
minutes and was interrupted after it stopped producing progress or a handoff.
The controller did not accept any of its changes.

## Observed Output

The worker changed only the allowed draft surface before interruption:

- `compat/fixtures/m0-tracefiles/generate.py`
- `compat/fixtures/m0-tracefiles/manifest.json`
- `compat/fixtures/m0-tracefiles/oracle-cases.json`
- three uncommitted `fixtures/ver/*.info` files

It did not produce or validate `oracle-baseline.json`, `compat/tracefile/v2.5.json`,
`validate.py`, or `test_contract.py`. No required gate completed and no exact
structured mapping for `M1-TF-007` was generated.

## Findings

1. The draft `ver-repeat-equal` and `ver-repeat-different` fixtures reopen the
   same `SF` across sections. That couples the lane to the unresolved repeated
   source/test section model `M1-TF-023`, despite the brief's explicit boundary.
2. The draft had no pinned Oracle stream/exit evidence, so its `oracle_default`
   values were unverified claims.
3. The draft did not update contract validation or tests, so the expected
   `39 -> 42` fixture and `59 -> 63` case closure was not executable.
4. The worker left a root-owned `tmp_out/input.info` runtime artifact outside
   the allowlist. The controller quarantined it under `/tmp` and restored all
   repository files to the starting SHA before continuing.

## Acceptance Status

- Goal alignment: **blocked**; no evidence-backed mapping was delivered.
- File boundary: **partial**; source edits stayed inside the allowlist, but a
  runtime artifact escaped it.
- Data contract: **not satisfied**; generated manifest/cases were incomplete.
- Tests and verification: **not run to completion**.
- Product compatibility evidence: **unchanged false/empty**.
- M1 authorization: **unchanged blocked**.

The controller takes over this lane as a single-agent implementation. The
aborted model draft is not part of the delivery and must not be counted as an
accepted model slice.
