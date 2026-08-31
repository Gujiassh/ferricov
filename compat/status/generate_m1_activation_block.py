#!/usr/bin/env python3
"""Render the normative M1 activation block from its canonical contract."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "compat"))
import verify  # noqa: E402


def main() -> int:
    contract_path = ROOT / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.activation.json"
    markdown_path = ROOT / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md"
    raw = contract_path.read_text(encoding="utf-8")
    document = json.loads(raw)
    if raw != json.dumps(document, indent=2, sort_keys=True) + "\n":
        raise SystemExit("activation contract is not canonical JSON")
    text = markdown_path.read_text(encoding="utf-8")
    start = text.index(verify._ACTIVATION_BLOCK_START)
    end = text.index(verify._ACTIVATION_BLOCK_END) + len(verify._ACTIVATION_BLOCK_END)
    block = verify._render_m1_activation_block(document)
    markdown_path.write_text(text[:start] + block + text[end:], encoding="utf-8")
    print(f"WROTE {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
