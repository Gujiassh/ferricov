# M0 Remaining Residuals — Blocked Ledger

Status: open / blocked pending specialized fixtures or honest Oracle differentials

After residual4/capture/script waves (reviewed primary 493 / gaps 38):

## CLI (4)

| Target | Block reason |
| --- | --- |
| `command.geninfo.option.compat-libtool` | default libtool ON; no distinct filesystem delta |
| `command.lcov.option.compat-libtool` | same |
| `command.geninfo.option.history-script` | ordering-only; no content delta with minimal script |
| `command.perl2lcov.option.preserve` | needs Devel::Cover DB fixture |

## lcovrc (34)

These need specialized multi-file, language-extension, parallel, demangle, or filter fixtures
that did not produce exit/filesystem exact-v1 deltas on the hello/residual genhtml inputs:

- `lcovrc.c-file-extensions`
- `lcovrc.check-data-consistency`
- `lcovrc.demangle-cpp`
- `lcovrc.derive-function-end-line-all-files`
- `lcovrc.expected-message-count`
- `lcovrc.filter-bitwise-conditional`
- `lcovrc.filter-blank-aggressive`
- `lcovrc.filter-lookahead`
- `lcovrc.forget-testcase-names`
- `lcovrc.fork-fail-timeout`
- `lcovrc.geninfo-auto-base`
- `lcovrc.geninfo-capture-all`
- `lcovrc.geninfo-compat`
- `lcovrc.geninfo-compat-libtool`
- `lcovrc.geninfo-follow-symlinks`
- `lcovrc.geninfo-gcov-all-blocks`
- `lcovrc.geninfo-interval-update`
- `lcovrc.geninfo-unexecuted-blocks`
- `lcovrc.info-file-pattern`
- `lcovrc.java-file-extensions`
- `lcovrc.lcov-filter-chunk-size`
- `lcovrc.lcov-filter-parallel`
- `lcovrc.lcov-json-module`
- `lcovrc.max-fork-fails`
- `lcovrc.max-tasks-per-core`
- `lcovrc.no-exception-branch`
- `lcovrc.parallel`
- `lcovrc.perl-file-extensions`
- `lcovrc.python-file-extensions`
- `lcovrc.rtl-file-extensions`
- `lcovrc.select-script`
- `lcovrc.split-char`
- `lcovrc.suppress-function-aliases`
- `lcovrc.trivial-function-threshold`

Policy: do not close with cmd_line-only or hollow parse-only plans.
