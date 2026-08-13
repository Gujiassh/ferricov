# M0 Remaining CLI Residuals — Blocked Ledger

Status: open / blocked pending honest Oracle differentials

After external-derive, hard-residual, and genhtml-hard2 waves (reviewed primary 459 / gaps 72),
four CLI options remain without substantive plans:

| Target | Block reason | Probe evidence |
| --- | --- | --- |
| `command.geninfo.option.compat-libtool` | Default libtool compat is already ON; `--compat-libtool` / `--no-compat-libtool` did not produce a distinct sealed filesystem tree on compiled `.libs` fixtures | Oracle probe 2026-08-14 |
| `command.lcov.option.compat-libtool` | Same as geninfo (forwarded capture path) | same |
| `command.geninfo.option.history-script` | Minimal history script yields identical out.info tree vs control (ordering-only / no content delta) | same |
| `command.perl2lcov.option.preserve` | Requires sealed Devel::Cover DB fixture; not yet built in M0 harness | help inherits common options; no fixture |

Policy: do not close with cmd_line-only or hollow parse-only plans. Leave unreviewed until a real exit/filesystem/stderr exact-v1 oracle delta is sealed.

Next phase focus: 68 `lcovrc.*` config gaps (and other non-CLI residuals outside this ledger).
