# M0 genhtml CLI Hard Planning Wave Review

Status: accepted after Critical audit rework — **history-script only**

Independent audit rejected the first draft for claiming `debug` closed under
cmd_line-only compared dimensions. This revision keeps only the substantive
history-script plan.

## Scope

Reviewed in `compat/behavior/fragments/authored/m0-genhtml-cli-hard-wave.json`:

- `command.genhtml.option.history-script` — **closed** (suite-bound, planned)

Explicitly **not** closed in this wave:

- `command.genhtml.option.debug` — compared dimensions were cmd_line-only once
  stderr was excluded (memory counter drift; no approved normalizer). Remains
  an M0 gap until a compared non-cmd_line effect is sealed.
- `command.genhtml.option.new-file-as-baseline` — still open; differential
  probes did not change TLA classification under exact-v1.

## Suite

`compat/cases/m0-genhtml-cli-hard-contract.json`:

- control
- history-script (`--history-script ./history.sh`)

All four dimensions use `exact-v1`. Two clean Oracle runs agree. Reverse exit
23. `product_compatibility_evidence=false`.

Observable effect for history-script: stdout differs from control under the
empty history-profile scheduling path (stable).

## Contract effect

- reviewed primary: 443 -> **444**
- explicit M0 gaps: 88 -> **87**
- product evidence empty; M1 unauthorized

## Verification

```text
python3 -m unittest compat.cases.test_m0_genhtml_cli_hard_contract
python3 compat/behavior/generate.py
python3 compat/behavior/validate.py --mode current
python3 compat/status/generate_m0_status.py
```
