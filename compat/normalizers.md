# Normalizer Registry

Normalizers are reviewed compatibility rules, not generic diff cleanup. The
differential runner rejects any identifier that is not compiled into the
registry and declared by the suite schema.

## `exact-v1`

- Transformation: none
- Allowed for: exit-independent byte streams and filesystem snapshots
- Risk: none; every byte remains observable

## `text-crlf-to-lf-v1`

- Transformation: replace each CRLF byte pair with LF
- Allowed for: cross-platform comparisons of documented text output
- Not allowed for: tracefiles, binary files, same-platform release evidence,
  or any output where carriage returns have semantic meaning
- Risk: can hide a platform line-ending difference; every use requires the
  suite to declare a cross-platform purpose

Generated timestamps, temporary paths, ordering, warning text, coverage
counters, and HTML semantics currently have no approved normalizer. A new rule
requires an SSoT update, focused unit tests, and review before use.
