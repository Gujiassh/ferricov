#!/usr/bin/env python3
"""Bind LCOV's Python intersphinx mapping to the vendored inventory."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: pin-intersphinx.py <conf.py> <objects.inv>")
    config_path = Path(sys.argv[1])
    inventory_path = Path(sys.argv[2])
    header = inventory_path.read_bytes().splitlines()[:3]
    expected_header = [
        b"# Sphinx inventory version 2",
        b"# Project: Python",
        b"# Version: 3.14",
    ]
    if header != expected_header:
        raise SystemExit(f"unexpected Python inventory header: {header!r}")

    old = "'python': ('https://docs.python.org/3/', None),"
    new = "'python': ('https://docs.python.org/3.14/', 'python-objects.inv'),"
    content = config_path.read_text(encoding="utf-8")
    if content.count(old) != 2:
        raise SystemExit("expected exactly two remote Python inventory mappings")
    patched = content.replace(old, new)
    if old in patched or patched.count(new) != 2:
        raise SystemExit("Python inventory mapping replacement was not exact")
    config_path.write_text(patched, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
