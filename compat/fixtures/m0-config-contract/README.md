# M0 Configuration Contract Fixtures

These fixtures make LCOV 2.5 configuration discovery and precedence observable
through `lcov --summary trace.info`. The shared tracefile contains branch data:
`branch_coverage=1` adds the branch summary line, while `branch_coverage=0`
omits it.

- `common/` covers explicit files, CLI order, `--rc` and option overrides,
  relative includes, unknown keys, missing environment references, and early
  read failures without an automatically discovered file.
- `home-auto/` contains `$HOME/.lcovrc` and an explicit file that must bypass
  automatic discovery.
- `lcov-home/` contains only `$LCOV_HOME/etc/lcovrc` for fallback discovery.
- `home-first/` contains conflicting HOME and LCOV_HOME files; HOME must win.
- `env/` expands one or multiple arbitrary `$ENV{...}` references.

The generated suites compare exit status, stdout, stderr, and filesystem trees
exactly. Raw observations remain Oracle-only evidence and never establish
Ferricov compatibility.
