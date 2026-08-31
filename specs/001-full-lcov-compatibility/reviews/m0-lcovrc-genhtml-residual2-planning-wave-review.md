# M0 lcovrc Genhtml Residual2 Planning Wave Review

Status: accepted after independent Critical audit

## Scope

Closes 15 residual `lcovrc.genhtml-*` config keys on one shared residual genhtml fixture:

dark-mode, flat-view, frames, footer, charset, desc-html, keep-descriptions,
synthesize-missing, show-noncode-owners, show-function-proportion, nav-resolution,
nav-offset, age-field-width, owner-field-width, date-labels.

Each variant is a distinct `.lcovrc` that appends one config-key assignment to
`control.lcovrc`. Control vs each variant has a sealed filesystem tree delta.

Fixture: `compat/fixtures/m0-lcovrc-genhtml-residual2-contract/`

## Oracle relations

- control: exit 0, baseline report tree
- each of 15 variants: exit 0, `file_tree_sha256 != control`

Compared dimensions: exit + filesystem (`exact-v1`). Stdout/stderr excluded.

## Explicit non-claims

- No Ferricov product compatibility evidence; M1 unauthorized.
- Not closed in this wave: `genhtml_show_owner_table` and `genhtml_date_bins`
  (Oracle exit 255 on this fixture without supporting annotate/date inputs).
- Remaining CLI blocked ledger still applies (compat-libtool, history-script, perl2lcov preserve).

## Contract effect

- reviewed primary: 459 -> 474
- gaps: 72 -> 57
