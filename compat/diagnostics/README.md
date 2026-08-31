# LCOV 2.5 Diagnostics Contract

This directory contains the standalone, fail-closed M0 inventory of LCOV 2.5
diagnostic classes, error-control rules, unclassified failure surfaces, and
command exit policies. It does not implement Ferricov runtime behavior or
provide product-compatibility evidence.

The generated contract freezes:

- all 32 ordered, case-insensitive shared message classes;
- the complete symbol-reference closure under `bin/`, `lib/`, and `scripts/`;
- the reserved `branch` class, which has no production emitter at the pinned
  commit;
- ignore-list precedence, repeated-name counts, keep-going, warning promotion,
  suppression, summary, and command exit-folding controls;
- parser, raw Perl, native Python, and early dependency failure surfaces;
- all 71 planned diagnostic and parallel case identities;
- 146 retained historical Oracle references from correctness and tracefile
  baselines;
- 26 wave1 diagnostics Oracle references under `compat/diagnostics/wave1/`; and
- 32 wave2 diagnostics Oracle references under `compat/diagnostics/wave2/`.

## Wave1 Oracle references

`compat/diagnostics/wave1/` retains a bounded executable Oracle batch for the
highest-priority remaining diagnostics gaps:

- true `geninfo` no-args with writable temporary storage
  (`DIAG-NOARGS-GENINFO-001`, exit `255`);
- ignore zero / one / two ladders;
- keep-going, unknown ignore, and CLI-over-RC ignore precedence;
- warning and warning-promotion ladders;
- max-message suppression and expected-count spellings;
- message-log capture;
- converter keep-going traps with real conversion inputs;
- converter keep-going boundary with structural XML failure; and
- basic `--parallel 1` / `--parallel 2` parity smoke.

Wave1 validation is fail-closed:

- an independent expected-case table binds all 19 planned IDs to exact case
  identity (id/kind/argv/fixtures/exit);
- validators recompute stdout/stderr hashes from committed
  `reference/*.bin` bytes and recompute the workspace file-tree from case
  directories rather than trusting observation self-hashes alone;
- file-tree semantics are explicitly
  `workspace_including_inputs` (inputs + outputs under the case workdir);
- capture runs the Oracle command under in-container `env -i` with only the
  declared clean variables, probes/retains the exact effective command
  environment, and does not inherit ambient host PATH/HOME;
- timeout path kills the docker CLI child, force-removes the named container,
  and retains verified cleanup outcomes; `docker ps` observer failures fail
  closed and are never treated as absence;
- contract schema enumerates every supported `oracleObservation` field with
  `additionalProperties: false` so unknown fields fail independently;
- every wave1 case retains an `execution_manifest` with locale/timezone,
  invoked executable hashes, Perl/Python/compiler versions, and package
  availability (or explicit not_applicable);
- capture launchers always pass `stdin=subprocess.DEVNULL`; env/manifest
  probes use try/finally force-remove cleanup on timeout/error.

Wave1 observations remain `oracle_reference` only and do **not** set
`product_compatibility_evidence`.

The retained correctness `m0-core-geninfo-startup-control` observation remains a
`startup_environment_intercept` with exit `30` because its read-only environment
fails temporary-file creation before the true no-argument path. Wave1 adds the
separate writable-temp observation and must not replace or reclassify the
intercept.

Regenerate wave1 only after an intentional reviewed capture change against the
pinned Oracle image:

```sh
python3 compat/diagnostics/wave1/scripts/capture_wave1.py
```

## Wave2 Oracle references

`compat/diagnostics/wave2/` retains a second bounded executable Oracle batch for
the remaining high-priority diagnostics and parallel gaps that are executable on
the pinned image without claiming Ferricov product compatibility:

- registry reserved-class acceptance and singular ignore-prefix / POSIX profile;
- environment clean/precedence/allowlist/LCOV_HOME/LCOV_VALIDATE/show-location;
- config discovery/explicit/include/unknown-key/env-expand/early-error;
- raw Perl, Python traceback, and GD-present genpng dependency path;
- callback finalize and cleanup/package lifecycle diagnostics;
- parallel child exit, callback state/lifecycle, missing payload, message log,
  memory admission/fallback, capture status, and partial-commit control.

Empty directory fixture `emptyhome` is retained with a tracked zero-byte regular `emptyhome/.gitkeep` marker. Only that exact path is excluded from Oracle fixture and file-tree hashes; nonzero markers, `.keep`, symlink/broken-symlink markers, or markers elsewhere fail closed. Capture staging validates the source marker then stages a truly empty runtime HOME (marker not copied into `/work/emptyhome`), so clean Git checkouts remain valid without precreated empty dirs.

Wave2 reuses the accepted wave1 provenance contract (clean `env -i`, DEVNULL
stdin, fail-closed named-container cleanup, execution manifests, independent
raw stream/tree facts, mutation rejection). Case-local environment extras remain
declared clean-env variables rather than ambient host inheritance.

Wave2 binds 30 planned identities across 32 observations. Across historical,
wave1, and wave2 references, 59 of 71 planned diagnostic/parallel identities
are exactly bound. The remaining 12 geninfo-child watchdog/Ferricov pair,
signal/unknown-child/parent-death/fork-retry/corrupt-payload paths stay unbound
and `planned`.

Regenerate wave2 only after an intentional reviewed capture change against the
pinned Oracle image:

```sh
python3 compat/diagnostics/wave2/scripts/capture_wave2.py
```

## Validate

Validate against a clean pinned upstream checkout:

```sh
python3 compat/diagnostics/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference
python3 -m unittest compat/diagnostics/test_contract.py
```

Regenerate the contract inventory only after an intentional reviewed contract
change:

```sh
python3 compat/diagnostics/contract.py \
  --upstream-root /home/cc/code1/lcov-upstream-reference \
  --write
```

## Wave3 Oracle references

`compat/diagnostics/wave3/` retains the third bounded executable Oracle batch for
the remaining parallel/geninfo-child planned identities that are executable on
the pinned image without claiming Ferricov product compatibility:

- geninfo child default-stop, keep-going watchdog, ignore1/ignore2 watchdog;
- child signal vs ordinary exit matrix;
- fork-retry exhaustion, corrupt payload, unknown positive PID child, parent death.

Wave3 binds **9** planned identities across **11** observations. Across
historical, wave1, wave2, and wave3 references, **68** of **71** planned
diagnostic/parallel identities have exact bindings. The residual floor is the
three `*-FERRICOV-001` parity IDs, which the contract requires to remain unbound
until a product executable exists.

Wave3 reuses the wave1/wave2 provenance contract and adds optional per-case
host/in-container watchdog timeout handling for keep/ignore loops.

Regenerate wave3 only after an intentional reviewed capture change:

```sh
python3 compat/diagnostics/wave3/scripts/capture_wave3.py
```

