# M0 Representative Tracefile Corpus

This directory pins representative LCOV 2.5 tracefile input behavior before
the Ferricov parser and model are implemented. The behavioral Oracle is LCOV
2.5 at commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, executed from the
content-identified image and executable recorded in `manifest.json`.

## Contents

- `fixtures/current-all-records.info` covers every current writer record,
  including stable `FNL`/`FNA`, `BRDA` fallthrough/unreachable, and `MCDC U`.
- `fixtures/legacy.info` pins `FN`/`FNDA` input and its current-format rewrite.
- `fixtures/permissive-prefix.info` pins `KF`, `TN:,diff`, suffix-tolerant
  `DA`, malformed summary payloads, and a suffixed terminator.
- `fixtures/malformed/` has a single-record perturbation for every record
  family. Summary payload cases intentionally succeed because the Oracle only
  checks their prefixes.
- `fixtures/numeric-boundary.info` and `fixtures/numeric/` pin the Perl numeric
  acceptance, negative/zero, malformed-field, threshold, suppression, checksum,
  and stop-on-error boundaries used by counts. The exact cross-family atom matrix
  required by `M1-TF-030` remains a follow-up gap.
- `fixtures/bytes/` pins CRLF, no final newline, invalid UTF-8, and NUL input.
- `fixtures/state/` pins late-TN MC/DC ownership, cross-SF MC/DC success, and
  the cross-SF return-to-line1 duplicate hard failure. Success ownership is
  captured with `inspect_model.pl` semantic snapshots as well as canonical
  rewrite observations.
- `fixtures/functions/` pins current `FNL`/`FNA` behavior, mixed legacy/current
  function records, and FNL index scope/hard-failure cases. Successful model
  shaping uses `inspect_model.pl` semantic snapshots plus canonical rewrites;
  hard failures retain exact diagnostics and output-file absence.
- `fixtures/branches/` pins `BRDA` form coverage (vanilla, exception,
  fallthrough, `U`/`fU`/`eU`, dash taken, comma-bearing and numeric expressions,
  no-final-comma, empty-taken, empty-expression, positional expressions, and a
  two-tracefile expression-independence merge probe) and branch-block construction (input gaps, noncontiguous
  reuse, interleaved same-line tokens, and signature sort/renumber). Successful
  model shaping uses `inspect_model.pl` semantic snapshots plus canonical
  rewrites; both unreachable-flag modes and hard-failure diagnostics are
  retained.
- `generated/medium.info` and `generated/large.info` are manifest entries but
  are not committed. They are deterministic outputs of `generate.py`.

The explicit NUL decision is acceptance with a Perl pathname warning. With a
NUL in an otherwise complete `SF` path, the pinned Oracle retains the source
record, produces canonical output, and exits zero. Invalid UTF-8 bytes are a
separate accepted case and are also retained as raw bytes in the Oracle output
identity.

## Reproduction

Regenerate committed fixtures and the manifest:

```sh
python3 generate.py
```

Materialize scale fixtures outside the checkout:

```sh
python3 generate.py --include-scale --output-root /tmp/ferricov-m0-tracefiles
```

After the fixture and case set is stable, capture the pinned Docker Oracle
  baseline once with networking disabled:

```sh
python3 capture_oracle.py
```

Validate committed bytes, deterministic temporary regeneration, provenance,
case references, statuses, semantic snapshot content, and all stdout/stderr/output identities:

```sh
python3 validate.py
```

`oracle-baseline.json` stores exact stdout and stderr as base64 plus SHA-256
and byte size. Small canonical outputs are stored the same way. Scale cases
use summary commands, so repeated multi-megabyte canonical outputs are never
committed.
