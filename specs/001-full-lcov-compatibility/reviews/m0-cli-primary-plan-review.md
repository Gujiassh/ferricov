# M0 CLI Primary Plan Review

## Decision

Accepted as M0 planning evidence only. This slice reviews 40 public CLI primary
entries already exercised by the retained 126-case LCOV 2.5 Oracle contract. It
does not add Ferricov execution results, product compatibility evidence, or a
reason to start M1.

## Semantic Oracle

Each reviewed entry must satisfy all of these invariants:

1. Its stable primary case ID replaces exactly one generated inventory
   skeleton without changing the public target ID.
2. Every suite binding resolves to an existing case in the startup, parser
   policy, or POSIX parser-policy contract.
3. The description states only the behavior exercised by those bound cases.
4. `review_status` is `reviewed`, while `evidence_status` remains `planned` and
   `evidence` remains empty until a distinct Ferricov candidate is executed.
5. The generated contract remains byte-stable and M0 readiness continues to
   fail on the remaining unreviewed public entries.

## Reviewed Scope

| Parser family | Public primary entries | Exact suite-case bindings |
| --- | ---: | ---: |
| Python `argparse` | 11 | 40 |
| Direct `Getopt::Long` | 5 | 22 |
| Shared LCOV `Getopt::Long` | 24 | 92 |
| **Total** | **40** | **154** |

The 40 entries cover `gendesc` (3), `genhtml` (4), `geninfo` (4), `genpng` (2),
`lcov` (8), `llvm2lcov` (4), `perl2lcov` (4), `py2lcov` (7), and `xml2lcov`
(4). The bindings comprise 18 core startup cases, 78 default parser-policy
cases, and 58 POSIX parser-policy cases.

The authored sources are:

- `compat/behavior/fragments/authored/m0-cli-argparse-primary.json`
- `compat/behavior/fragments/authored/m0-cli-direct-getopt-primary.json`
- `compat/behavior/fragments/authored/m0-cli-shared-getopt-primary.json`

## Evidence Boundary

The retained correctness baseline contains Oracle observations only. It is not
a differential result because no Ferricov candidate was executed. Therefore all
40 entries deliberately remain `planned`; none is `pass` or `fail`, and no raw
Oracle artifact is linked through the product-evidence field.

## Review Result

| Area | Result | Evidence |
| --- | --- | --- |
| Goal alignment | pass | The slice reduces reviewed M0 planning debt without changing the milestone or making a compatibility claim. |
| User-visible flow | not applicable | No executable or runtime behavior changed. |
| Architecture and ownership | pass | Human decisions live in three authored fragments; deterministic inventory fragments and the aggregate contract remain generated outputs. |
| Data and evidence contracts | pass | 40 unique primary targets, 154 resolving suite bindings, `planned` status, and zero evidence items are mutation-tested. |
| Implementation quality | pass | Each authored fragment remains below the 2,000-line authoring limit. |
| Verification and evolution | pass | Generation, byte-stability, current validation, and 39 behavior tests pass; M0 still reports 468 gaps. |

## Verification

```bash
python3 compat/behavior/generate.py
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current \
  --upstream-root "$LCOV_SOURCE_ROOT"
python3 -m unittest compat/behavior/test_validate.py
```

Observed result: 531 public entries, 531 primary plans, 63 reviewed primary
plans, 468 remaining primary-review gaps, 40 new planning-only cases, 154 exact
suite bindings, and zero product evidence items.

## Residual Risk And Next Step

These bindings establish parser-facing planning coverage only. They do not prove
operation semantics, configuration precedence, tracefile meaning, callbacks,
filesystem effects beyond the exercised cases, or candidate parity. Continue M0
with the next bounded public-primary review batch; do not begin M1.
