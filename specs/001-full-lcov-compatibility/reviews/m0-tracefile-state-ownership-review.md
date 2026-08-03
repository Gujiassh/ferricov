# M0 Tracefile State-Ownership Oracle Evidence Review

Status: Critical review complete for the bounded ownership slice only.
Product compatibility evidence: false.
M1 authorization: not granted.

## Semantic Oracle

Pinned immutable Oracle image
`sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e` with
executable SHA
`d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252`.

### Late TN (`M0-TF-TN-MCDC-001` / `M1-TF-021`)

Exact input:

```text
TN:A
SF:/m0/late-tn.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,edge,1
MCDC:1,1,t,1,0,cond
DA:1,1
TN:B
MCDC:1,1,f,1,0,cond
end_of_record
```

Observed ownership:

- retained source `/m0/late-tn.c`
- line/function/branch testcase maps stay on `A`
- aggregate MC/DC contains both senses on line 1 (`found=2,hit=2`)
- testcase MC/DC map contains empty `A` and line1 clone under `B`
- exceptional cached-count/data divergence: `B` MC/DC cached `found=0,hit=0`
  while line data is present
- canonical writer enumerates testcase `A` only and omits B MC/DC
- canonical output SHA
  `6af975d55989695523fce76a562cf0dc8d4513234929e610b7a7d131f317237e`
- semantic snapshot stdout SHA
  `9a8e89a672436d90...` retained in `oracle-baseline.json`

### Cross-SF success (`M0-TF-MCDC-SF-001` / `M1-TF-022`)

Exact success input:

```text
TN:A
SF:/m0/first.c
MCDC:1,1,t,1,0,first
DA:1,1
TN:B
SF:/m0/next.c
MCDC:2,1,t,1,0,second
DA:2,1
end_of_record
```

Profile: `lcov --no-function-coverage --mcdc-coverage`.

Observed ownership:

- first source filtered because no terminator closed it
- retained source `/m0/next.c` / testcase `B` only
- aggregate MC/DC cached counts `found=4,hit=2` while aggregate line data is
  only line 2 and aggregate MC/DC line objects retain only line 2
- testcase MC/DC under `B` contains line1 clone (`first`) and line2 (`second`)
  with cached `found=0,hit=0`
- canonical output SHA
  `0fc19d686b099477165a80ff9909acc9f1a9480fd1441830f6434c20ceac3b95`
- semantic snapshot stdout SHA
  `02c3e58fa26211e3...` retained in `oracle-baseline.json`

### Cross-SF duplicate (`M1-TF-026`)

Exact return-to-line1 variant inserts `MCDC:1,1,f,1,0,first` after line2 MC/DC.
Pinned result: exit status 1; stderr contains `MCDC already defined for 1`.
Baseline identity uses `input.info` path text and is retained by hash rather
than a host-temporary path SHA.

## Commands And Evidence

```sh
python3 compat/fixtures/m0-tracefiles/generate.py
python3 compat/fixtures/m0-tracefiles/capture_oracle.py \
  --image sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e
python3 compat/fixtures/m0-tracefiles/validate.py
python3 compat/tracefile/contract.py --write
python3 -m unittest compat.tracefile.test_contract -v
python3 compat/resources/contract.py --write
python3 compat/verify.py --skip-oracle
```

The first `compat/verify.py --skip-oracle` attempt exposed that the updated
tracefile source-section line references changed `compat/resources/v2.5.json`
without rebinding the retained result metadata. After regenerating the resource
contract and updating only the retained result's `contract` artifact bytes/SHA
(the 13 samples and their raw observations are unchanged), the final
`compat/verify.py --skip-oracle` rerun passed.

Retained artifacts:

- `compat/fixtures/m0-tracefiles/fixtures/state/*.info`
- `compat/fixtures/m0-tracefiles/inspect_model.pl`
- `compat/fixtures/m0-tracefiles/manifest.json`
- `compat/fixtures/m0-tracefiles/oracle-cases.json`
- `compat/fixtures/m0-tracefiles/oracle-baseline.json`
- `compat/tracefile/v2.5.json`

Exact totals after this slice: 39 fixtures, 59 Oracle cases, 2 semantic
snapshots, 40 exit-zero / 19 exit-nonzero. Exact structured mappings added for
`M1-TF-021`, `M1-TF-022`, `M1-TF-026`. Missing exact executable IDs: 25.
M0 primary behavior review remains 73/458. Existing first-52 observation
payloads preserved by case ID.

## Review-Area Statuses

| Area | Status | Notes |
| --- | --- | --- |
| goal alignment | pass | Bounded ownership Oracle evidence only; no product claim |
| user-visible flow/timing | not applicable | No product UI or runtime flow |
| architecture/boundaries | pass | Inspector is fixture support; model remains independent of product crates |
| data contracts/types | pass | Snapshot JSON and contract schema bind ownership maps and hashes |
| implementation quality | pass | Generator/capture/validate/contract extended narrowly |
| verification/evolution | pass | Fail-closed validate + mutation tests + immutable image capture |

## Reverse Mutations

1. Swap semantic-snapshot stdout hashes between late-TN and cross-SF -> rejected.
2. Change `requirement_ids` on a state case -> rejected as mapping drift.
3. Change semantic snapshot runner away from `inspect_model.pl` -> rejected.
4. Promote `evidence_status` to product_pass -> rejected.
5. Drift `inspect_model.pl` bytes / artifact hash -> rejected.
6. Alter one of the first 52 baseline identities by case ID -> would fail
   baseline/case equality and identity checks.

## Residual Risks

- Semantic snapshots inspect installed `lcovutil.pm` object shape; future Oracle
  packaging changes need inspector + hash rebind.
- Cross-SF aggregate cached-count/data divergence is Oracle-observed and must not
  be "cleaned up" by product code without an explicit approved behavior change.
- Exact executable mappings cover three M1-TF IDs only; whole M1-MD rows and the
  remaining 25 M1-TF IDs stay open.
- M1 remains unauthorized.

## Compatibility Claim

None. All new evidence is `oracle_reference` only.
