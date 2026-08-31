# M0 Support-Script Planning Wave Review

Status: accepted as planning-only evidence

## Scope

This wave closes the three remaining support-script primary planning gaps:

- `support-script.analyzeinfofiles`
- `support-script.annotateutil-pm`
- `support-script.get-signature`

The compatibility suite is `m0-support-script-contract`. It compares exact
exit, stdout, stderr, and filesystem dimensions for every case and uses
committed deterministic fixture directories.

## Oracle Executability Check

The suite argv was exercised against pinned LCOV v2.5 image
`sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
with network disabled, clean locale/timezone/home values, read-only fixture
mounts, and a 30-second host deadline.

| Case | Result | Observed boundary |
| --- | --- | --- |
| `m0-support-analyze-info-files` | exit 0 | installed `analyzeInfoFiles` consumed two tracefiles; stdout 49 bytes; Perl smartmatch warnings retained on stderr |
| `m0-support-annotateutil-compute-md5` | exit 0 | `perl` loaded installed `annotateutil.pm` with its required host `File::Spec` dependency and invoked `compute_md5` |
| `m0-support-get-signature` | exit 0 | installed `get_signature` emitted the fixture MD5 with empty stderr |

The first annotateutil probe deliberately failed because the module calls
`File::Spec->devnull()` without importing that package itself. The accepted
suite therefore preloads `File::Spec`, matching the module's real host-loaded
boundary rather than hiding the dependency.

## Contract Effect

- substantive reviewed primary plans: 361 -> 364
- explicit M0 behavior gaps: 170 -> 167
- fixed primary/interaction projections: 363 -> 366
- product evidence: unchanged and empty
- product compatibility: not claimed

The Oracle execution above validates that the planned argv is real. It is not
stored as a Ferricov differential result and cannot promote any case to pass.

## Verification

- behavior generation stable
- current behavior validation passed with `public=531`,
  `reviewed_primary=364`, `m0_gaps=167`
- 48 behavior mutation and contract tests passed
