# M0 Behavior Gap Audit

Status: active ledger

## Baseline

The behavior contract covers all 531 public inventory entries with primary
plans. After the support-script, small-command, `llvm2lcov`, and `perl2lcov`
suite waves, five trace-operation `lcov` cases, two `lcovrc` list-format cases,
and nineteen prior plus nine metric fixed-epoch `genhtml` config cases, 417
primary plans are substantive and reviewed; 114 remain explicit M0 planning
gaps. Product
compatibility evidence remains absent.

The remaining gaps partition exactly as follows:

| Lane | Remaining | Authored ownership |
| --- | ---: | --- |
| `lcovrc` consumer semantics | 70 | responsibility-split `m0-lcovrc-*.json` fragments |
| command options and positionals | 44 | command-owned `m0-*-wave1-repair-*.json` fragments |
| support scripts | 0 | `m0-support-wave1-repair-a.json` |

The command lane consists of 27 `genhtml`, 9 `geninfo`, 7 capture/reset-oriented
`lcov` entries, and the unbound `perl2lcov --preserve` entry. The other
`genpng`, `gendesc`, `py2lcov`, `llvm2lcov`, `perl2lcov`, and trace-operation
`lcov` residuals are closed. The totals reconcile to `70 + 44 = 114`.

## Closure Rule

A primary plan becomes substantive only when it is reviewed and either:

- binds at least one compatibility-scope suite case; or
- binds both a reviewed public-behavior upstream driver and a behavior group.

A source reference, description, or status label alone does not close a gap.
Suite planning remains distinct from evidence: `evidence_status=planned`, an
empty evidence array, and no product compatibility claim are required until a
distinct Ferricov executable is compared with the Oracle.

## Execution Order

1. Close command-owned option/positional lanes in bounded families, starting
   with the smallest commands and shared exact option forms.
2. Close `lcovrc` consumer semantics in four fragments, splitting any authored
   file before it crosses the 2,000-line review threshold.
3. Run `compat/behavior/validate.py --mode m0-ready`; only zero residual gaps
   closes this M0 gate.
4. Retain product differential results later under distinct executable
   identities; do not reinterpret planning closure as parity.

## Acceptance

- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current`
- `PYTHONPATH=. python3 -m unittest compat.behavior.test_validate`
- fixed `plan-bindings.json` SHA-256 updated only after reviewing regenerated
  primary and interaction projections
