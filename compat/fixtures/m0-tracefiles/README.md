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
  acceptance and error boundaries used by counts.
- `fixtures/bytes/` pins CRLF, no final newline, invalid UTF-8, and NUL input.
- `fixtures/state/` pins late-TN MC/DC ownership, cross-SF MC/DC success, and
  the cross-SF return-to-line1 duplicate hard failure. Success ownership is
  captured with `inspect_model.pl` semantic snapshots as well as canonical
  rewrite observations.
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

Capture the pinned Docker Oracle baseline with networking disabled:

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
