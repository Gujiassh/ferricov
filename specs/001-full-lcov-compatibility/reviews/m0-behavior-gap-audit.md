# M0 Behavior Gap Audit

Status: active ledger

## Baseline

The behavior contract covers all 531 public inventory entries with primary
plans. After the first support-script suite wave, 364 primary plans are
substantive and reviewed; 167 remain explicit M0 planning gaps. Product
compatibility evidence remains absent.

The remaining gaps partition exactly as follows:

| Lane | Remaining | Authored ownership |
| --- | ---: | --- |
| `lcovrc` consumer semantics | 100 | `m0-lcovrc-wave1-repair-a.json` through `d.json` |
| command options and positionals | 67 | command-owned `m0-*-wave1-repair-*.json` fragments |
| support scripts | 0 | `m0-support-wave1-repair-a.json` |

The command lane consists of 27 `genhtml`, 12 `lcov`, 9 `geninfo`, 7
`llvm2lcov`, 6 `perl2lcov`, 4 `genpng`, 1 `gendesc`, and 1 `py2lcov` entry.
The totals reconcile to `100 + 67 = 167`.

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
