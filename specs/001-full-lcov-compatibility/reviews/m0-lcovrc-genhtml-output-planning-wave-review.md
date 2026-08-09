# M0 lcovrc genhtml Output Planning Wave Review

Status: accepted for eight primary plans

## Scope

The `m0-lcovrc-genhtml-output-contract` suite closes these configuration
consumers against a shared control:

- `genhtml_header`
- `genhtml_html_epilog`
- `genhtml_html_extension`
- `genhtml_html_gzip`
- `genhtml_html_prolog`
- `genhtml_legend`
- `genhtml_no_source`
- `genhtml_num_spaces`

The eight cases were moved from the 1,970-line
`m0-lcovrc-wave1-repair-b.json` into a 364-line consumer fragment before any
bindings were added. The retained B fragment is 1,618 lines. Object-set
regeneration remained stable across the split.

## Deterministic Envelope

`genhtml` embeds the current date in generated reports and internally uses
`lcov_tmp_dir`, not only `TMPDIR`. Exact comparison therefore requires:

- canonical image
  `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
- `SOURCE_DATE_EPOCH=946684800`
- `TZ=UTC`
- `lcov_tmp_dir=/work`
- read-only container root and a writable per-case `/work`

The paired genhtml launchers have identical environment-key sets. The reverse
launcher remains intentionally divergent and exits 23; it is harness evidence,
not Ferricov product evidence.

## Fixture

One tracefile covers five lines and one function in `/work/source.c`. The source
contains a tab so `genhtml_num_spaces` reaches its semantic consumer. Prolog and
epilog cases use distinct retained marker files. Every config carries the same
read-only-root temp setting and differs from the control only in its target
setting or added prolog/epilog path.

## Reproducibility Probe

Two independent pinned-Docker runs produced identical report-only tree hashes
for every case. All cases exited 0 with empty stderr. The control and each
nondefault report tree were byte-distinct; gzip was also stable across both
runs.

## Differential Artifact Facts

The Rust differential runner recorded 337-byte reference stdout and empty
reference stderr for every case. Exact full file-tree artifact hashes were:

| Case | Files | File-tree SHA-256 |
| --- | ---: | --- |
| control | 26 | `b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329` |
| header | 26 | `dd905f60222c6bbee4d49a3cf9bf2ca6f806a25eccc826fdc641b66143053e2b` |
| epilog | 26 | `1369bd3bb49513c1155be6debd60d2d16d6e7420b5ea45b546dc60a84d2568ca` |
| extension | 26 | `8b7ece3a9252b116da96543759c4e4c3d1def60ae8ee272433582de06ad02a73` |
| gzip | 27 | `61ca7006bcf456919d0ebde34291db0605bb6ab2e8ab77cadcdb7d03677034b3` |
| prolog | 26 | `7537b712392045180f090622fcdf855b81fdc79b2f5a49c6fcf2e964bfc608e1` |
| legend | 26 | `cc0d5c3ce4c4206abf7d1335b8c881c9ba518013273f02e9c976712de3cca54e` |
| no source | 23 | `d379b35ac10155127c6dd9c0bf473d535bfc4c959532cf06a4a3dfe282ac91b5` |
| two-space tabs | 26 | `5bf70dc8b7b36740587c8629d3eea41e7ce43e5724fe7771916b63b7a271901c` |

Artifact directory:
`/tmp/ferricov-lcovrc-genhtml-differential-1786287815`.

## Contract Effect

- substantive reviewed primary plans: 389 -> 397
- explicit M0 behavior gaps: 142 -> 134
- fixed primary/interaction projections: 391 -> 399
- product pass/fail evidence: unchanged and empty

## Verification

- exact nine-case suite and four comparison dimensions
- fixture and launcher SHA-256 locks
- matching fixed-epoch launcher environments
- suite-bound control and nondefault case for every plan
- explicit tab semantic input and writable temp configuration
- stable behavior generation and fixed plan-binding hash
