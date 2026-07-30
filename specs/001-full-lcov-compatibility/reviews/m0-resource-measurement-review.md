# M0 Oracle Resource Observation Review

## Decision

The retained `M0-RSRC-MEASURE-001` result is acceptable as a bounded M0 Oracle
resource observation. It makes the reviewed controlled scale profiles
executable, binds every generated input and harness component by SHA-256, and
retains real container resource observations. It does not select Ferricov
input limits, close the M1 model/fuzz cases, provide candidate parity, establish
a stable performance distribution, or authorize M1.

## Classification

- Review class: `Critical`
- Reason: resource boundaries, timeout/cleanup behavior, and large inputs can
  affect accepted inputs, process outcomes, and service safety.
- Product code changed: no.
- Existing persisted/product contracts changed: no. The two standalone schemas
  describe Oracle evidence only.

## Semantic Oracle

1. The static contract contains exactly 13 ordered controlled profiles: four
   field sizes, three `DA` record counts, three section counts, and three equal
   four-family cardinalities.
2. Every profile has one primary scale axis and records dependent dimensions.
   Cardinalities are source-scoped so repeated line/function/branch/MC/DC keys
   in different `SF` sections remain distinct.
3. Targets are exact: field payloads 1 KiB, 64 KiB, 1 MiB, and 16 MiB; `DA`
   counts 1, 1,024, and 65,536; sections 1, 1,024, and 16,384; and all four
   family cardinalities 1, 1,024, and 65,536.
4. Execution uses immutable image
   `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
   and `/usr/local/bin/lcov` SHA-256
   `d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252`.
5. The exact command is `lcov --branch-coverage --mcdc-coverage --summary
   input.info`. Each profile statically binds clean outcome, exact stdout and
   stderr bytes/hashes, and parsed line/function/branch/condition-outcome
   semantics. One logical generated MC/DC condition has two outcomes, one hit.
6. The command environment is cleared and replaced by five recorded values;
   network is disabled, user is `root`, memory is capped at 1 GiB, PIDs at 128,
   and the host-side bounded Docker run is the sole 60-second deadline observer.
   There is no inner GNU timeout. Only `subprocess.TimeoutExpired` means timeout;
   a target exit code of 124 before the deadline is nonzero with timeout false.
7. Six exact harness/schema files are content-bound. The execution manifest,
   measurement tool, two normative source sections, contract, image, and LCOV
   executable are also bound.
8. Every successful sample retains canonical raw `metrics.json`, stdout, stderr,
   wall and CPU time, peak RSS, exact outcome, input immutability, unexpected
   output, and confirmed work/evidence/container cleanup. The result tree is
   closed over exactly `result.json` and three artifacts in each expected sample
   directory; any extra file, directory, or symlink is rejected.
9. When output storage remains writable, post-generation failures retain
   canonical evidence under `failures/<profile-id>/`: exact generated input,
   available raw metrics/target streams, Docker streams/status, failure
   class/reason, deadline/measured-outcome provenance, and post-cleanup facts.
   Artifact or manifest retention failure is reported with the original capture
   failure and does not claim a failure manifest exists.
10. Docker container observation fails closed. Observer failure is never treated
    as absence, capture requires a fresh/empty output directory, and named-
    container plus temporary work/evidence cleanup is attempted unconditionally,
    including when failure-evidence retention itself raises.
11. All 13 retained profiles exit zero. None signal, time out, write stderr,
    mutate input, or create an unexpected output entry.
12. Allocation count remains `not_observable`; harness budgets are not product
    limits; product-limit and product-compatibility evidence remain empty/false.
13. `M1-MD-020`, `M1-TF-063`, and `M1-TF-064` remain blocked on Ferricov
    boundary/parity and executable fuzz evidence.

## Evidence

Final capture used a fresh temporary directory and replaced canonical evidence
only after capture self-validation plus an independent validation pass:

```sh
python3 -m py_compile compat/resources/contract.py \
  compat/resources/generate.py compat/resources/capture.py \
  compat/resources/validate.py compat/resources/test_contract.py
python3 compat/resources/contract.py --write
python3 compat/resources/contract.py
output="$(mktemp -d /tmp/ferricov-resource-retention-final.XXXXXX)"
python3 compat/resources/capture.py --output "$output"
python3 compat/resources/validate.py --result "$output/result.json"
python3 compat/resources/validate.py --result \
  compat/resources/results/oracle-x86_64-linux-20260729/result.json
python3 -m unittest compat/resources/test_contract.py
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current
python3 compat/verify.py --skip-oracle
(cd compat/resources && basedpyright --level error \
  capture.py contract.py generate.py validate.py test_contract.py)
git check-attr -a -- compat/resources/results/oracle-x86_64-linux-20260729/samples/field-1k/stdout.bin
git diff --check
git diff --cached --quiet
rustup run 1.85.0 cargo fmt --all --check
rustup run 1.85.0 cargo check --workspace --all-targets --locked
rustup run 1.85.0 cargo test --workspace --all-targets --locked
rustup run 1.85.0 cargo clippy --workspace --all-targets --locked -- -D warnings
```

Observed final evidence:

- contract SHA-256:
  `4de3f0b2474034c96dcac068909bcb7f8a2d23240ae0265b7797e653c8777ada`;
- retained result SHA-256:
  `526d2c81b33776928cbd1e049a32c16cf5229f2764fd36c9063c35ee453894f4`;
- 13 total, 13 accepted, 0 nonzero, 0 signal, 0 timeout;
- 0 stderr bytes and 0 unexpected output entries;
- maximum observed peak RSS: 565,981,184 bytes on `cardinality-65536`;
- maximum observed wall time: 5,959,904,982 ns on `cardinality-65536`;
- source closure: 2 normative sections and 94 lines;
- harness closure: 6 exact generator/capture/validator/schema files;
- successful tree closure: 1 result file, 14 exact directories, and 39 exact
  sample artifacts with no symlinks;
- host: Linux x86_64, WSL2 kernel `6.6.87.2-microsoft-standard-WSL2`,
  20 logical CPUs, Docker `29.1.3`, systemd cgroup v2;
- resource tests: 42/42 pass;
- BasedPyright: 0 errors, 0 warnings;
- resource `*.bin` Git attributes: `binary` set; `diff`, `merge`, and `text`
  unset;
- Rust 1.85 workspace tests: 106/106 pass;
- full current compatibility verification: pass;
- product limits selected: false;
- product compatibility evidence: false.

The wall/RSS values are one captured observation per profile and are not
performance gates or stable benchmark distributions.

## Reverse Review

Focused mutations prove rejection of profile removal/reordering, target/input
shape drift, source/Oracle/harness identity drift, blocked-case removal, product
limit or allocation claims, non-clean outcomes, stream mutation even when
artifact metadata is coherently rewritten, semantic summary drift, summarized
metric drift from raw metrics, raw artifact byte/hash drift, non-canonical raw
metrics/result JSON, cleanup drift, result total drift, extra files, and
symlinks. Required host/runtime shape and omitted, empty, or invalid identity
values are rejected; coherent nonempty provenance values are retained as
observations and attested by the canonical result/repository digest rather than
compared with a static machine identity. Failure-path tests prove that exit 124
is retained as nonzero/timeout false, host `TimeoutExpired` is timeout true,
and both leave exact-input/raw-artifact/Docker/deadline/post-cleanup evidence
when storage is writable. Signal-path coverage proves raw `exit_code=null`/`signal=9` becomes
`oracle_signal`, remains non-timeout, and retains canonical measured outcome and
post-cleanup facts. Fault injection proves artifact retention failure reports
the original nonzero outcome and storage error, while combined injection also
preserves the distinct named-container cleanup error; both claim no manifest,
call cleanup, remove both temporary directories, and produce no success result.
Cleanup tests also prove exact-name absence checks, container removal,
observer-failure propagation, and nonempty-output rejection.

Assuming a regression occurred, exact generation and source-scoped input
analysis identify the affected profile; static stream/outcome semantics expose
Oracle behavior drift; retained raw metrics expose observation drift; and
fail-closed cleanup prevents an observer error from being misreported as clean.
No observed value can silently become a Ferricov limit or compatibility claim.

## Review Areas

| Area | Status | Judgment |
| --- | --- | --- |
| Goal alignment | pass | Completes the bounded Oracle-only resource observation without starting M1. |
| User-visible flow | not applicable | No Ferricov runtime or UI changed. |
| Architecture boundaries | pass | Generation, contract, capture, validation, and policy claims remain separate. |
| Data contracts | pass | Exact schema/semantic/static bindings fail closed; existing product contracts are unchanged. |
| Input semantics | pass | Source-scoped cardinalities and dependent dimensions are explicit. |
| Runtime identity | pass | Immutable image/executable/environment/harness/tool identities are checked; required host/Docker/cgroup provenance shape is validated, and coherent observed values are retained and digest-attested. |
| Resource evidence | pass | Successful evidence is retained/recomputed; writable storage retains canonical failure diagnostics, while retention errors fail closed without bypassing cleanup. |
| Allocation evidence | blocked | The rusage backend exposes no allocation counter. |
| Product limits | blocked | Exact accepted inputs are lower-bound observations only. |
| Fuzz execution | blocked | `M1-TF-064` has no executable corpus or run. |
| Tests | pass | 42 focused positive/reverse tests plus real capture validation pass. |
| CI | pass | Oracle CI exercises capture into a fresh temporary directory. |
| Documentation | pass | README, changelog, model/grammar, plan/tasks, and compatibility/performance SSoT agree. |
| M1 authorization | blocked | Remaining M0 gates and go/no-go approval are open. |
| Product compatibility | blocked | No Ferricov candidate executed any profile. |

## Residual Risk

Each profile has one resource sample, so timing and RSS describe this capture,
not a stable distribution. The profiles qualify exact summary inputs only; they
do not cover parse/write round trips, gzip/stdin transport, malformed nesting,
concurrent workers, other platforms, larger inputs, or a Ferricov rejection
path. The 1 GiB/60-second harness budgets detect bounded failure but cannot
define product policy. Product limits require a candidate, exact boundary
outcomes, and an approved safety deviation when Ferricov intentionally rejects
an Oracle-accepted input.
