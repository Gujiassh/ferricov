# M0 CLI Contract Fixtures

The three generated suites define 126 static command-line cases:

- `m0-cli-contract-core.json`: 40 per-command startup, help, version, and
  invalid/ignored-argv controls.
- `m0-cli-contract-policy.json`: 52 default-profile parser-policy cases.
- `m0-cli-contract-posix.json`: 34 cases with the exact suite override
  `POSIXLY_CORRECT=1`.

Run the deterministic contract, schema, global-ID, inventory-link, family-
equivalence, environment, and reverse-mutation checks with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 compat/cases/m0-cli-contract.py
```

Use `--write` only when intentionally regenerating the suites and their static
contract artifacts. Generation is checked byte-for-byte before completion.

## Contract Links

`case-contract.json` binds every case ID to one or more exact reviewed public
inventory entries or to a machine-verified parser-policy equivalence partition.
It also hashes every suite, the current inventory, and the suite schema. The
equivalence proof compares the complete parser-policy object for every command
in a family; filename prefixes and case counts are not used as coverage proof.

The same file defines a non-inheriting execution environment. A future raw
baseline executor must begin with only `HOME`, `LANG`, `LC_ALL`, `PATH`, and
`TZ` from the recorded allowlist, resolve `{workdir}` per case, and then apply
the suite override. The core and default-policy overrides are empty. The POSIX
override is exactly `POSIXLY_CORRECT=1`.

## Input Fixtures

`config/empty.lcovrc` isolates exact `--config-file` parsing from configuration
values. All five shared Getopt commands execute exact `--config-file` and
`--rc` cases in both default and POSIX profiles.

`--config-f` is the exact-only negative discriminator because it is otherwise a
unique prefix of `--config-file`. `--rc` has no observable shorter unique
prefix: `--r` also matches remove/resolve-related parser definitions. The suite
therefore executes exact `--rc` and case-folded `--RC` forms without inventing a
false abbreviation-negative partition.

`plus-positional/+help` is a valid XML document whose filename starts with `+`.
Successful `xml2lcov` conversion proves argparse treats the token as a
positional input.

`argparse-cluster/input.xml` makes `--verb`, ambiguous `--ver`, case-sensitive
forms, rejected single-dash long forms, and the `-vk` cluster observable without
resolving to `--help`.

Direct Getopt no-bundling uses `gendesc -??`. `?` is an explicit parser alias,
so a bundling-enabled reverse mutation splits and accepts the token while the
pinned disabled policy rejects the combined spelling in default and POSIX
profiles.

## Evidence Boundary

`oracle-baseline-status.json` is deliberately `pending_reproducible_oracle`.
The former raw shards from development image
`sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`
were removed and are not qualification evidence. Raw observations must be
recorded only after a reproducible Oracle image and matching validated execution
manifest are available. These suites remain a planned executable contract, not
Ferricov product compatibility evidence.
