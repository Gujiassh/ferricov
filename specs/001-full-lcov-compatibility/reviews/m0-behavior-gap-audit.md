# M0 Behavior Gap Audit

Status: active ledger

## Baseline

The behavior contract covers all 531 public inventory entries with primary
plans. After the support-script, small-command, `llvm2lcov`, and `perl2lcov`
suite waves, five trace-operation `lcov` cases, two `lcovrc` list-format cases,
nineteen prior plus nine metric and two report/differential fixed-epoch
`genhtml` config cases, the six-case `m0-genhtml-cli-output-contract` command
wave, the three-case `m0-genhtml-cli-metric-layout-contract` command wave, and
the three-case `m0-genhtml-cli-report-contract` command wave, the three-case
`m0-genhtml-cli-summary-contract` command wave, and the three-case
`m0-genhtml-cli-context-contract` command wave, 437 primary plans are
substantive and reviewed; 94 remain explicit M0 planning gaps. Product
compatibility evidence remains absent.

The `m0-genhtml-cli-metric-layout-contract` wave closes three command-owned
boundaries: `--frames`, `--precision 4`, and `--no-sort`. It uses one shared
metric trace/config control plus three direct-option targets. Two clean pinned
Oracle runs agree on the reference hashes, while the reverse harness exits 23;
the slice remains planning-only with product evidence absent.

The `m0-genhtml-cli-report-contract` wave closes three command-owned boundaries:
`--footer CLI Footer`, `--no-checksum`, and `--no-html`. It uses one shared
control plus three direct-option targets. Two clean pinned Oracle runs agree on
reference/output hashes, while the reverse harness exits 23; the slice remains
planning-only with product evidence absent.

The `m0-genhtml-cli-summary-contract` wave closes three command-owned
boundaries: `--fail-under-branches 50`, `--show-zero-columns`, and
`--sort-tables`. It uses one shared control plus three direct-option targets. Two
clean pinned Oracle runs agree on reference/output hashes, while the reverse
harness exits 23. A trial `--debug` case remains excluded because its stderr
contains run-specific temporary paths; the slice remains planning-only with
product evidence absent.

The `m0-genhtml-cli-context-contract` wave closes three command-owned boundaries:
`--baseline-title Baseline CLI`, `--merge-aliases`, and `--suppress-aliases`. It
uses one shared alias baseline/current/diff control plus three direct-option
targets with `--filter function`. Two clean pinned Oracle runs agree on
reference/output hashes, while the reverse harness exits 23; the slice remains
planning-only with product evidence absent.

The remaining gaps partition exactly as follows:

| Lane | Remaining | Authored ownership |
| --- | ---: | --- |
| `lcovrc` consumer semantics | 68 | responsibility-split `m0-lcovrc-*.json` fragments |
| command options and positionals | 26 | command-owned `m0-*-wave1-repair-*.json` fragments |
| support scripts | 0 | `m0-support-wave1-repair-a.json` |

The command lane consists of 9 `genhtml`, 9 `geninfo`, 7 capture/reset-oriented
`lcov` entries, and the unbound `perl2lcov --preserve` entry. The eighteen newly
closed `genhtml` options are command-owned CLI boundaries; the other
`genpng`, `gendesc`, `py2lcov`, `llvm2lcov`, `perl2lcov`, and trace-operation
`lcov` residuals are closed. The totals reconcile to `68 + 26 = 94`.

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
