#!/usr/bin/env python3
"""Generate docs/ssot/m0-status.snapshot.json from live contracts.

This command only writes the status snapshot. It does not regenerate inventory
pins. Inventory pin updates remain a separate explicit maintainer step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "compat"))

import verify  # noqa: E402


def main() -> int:
    snapshot = verify.build_m0_status_snapshot(ROOT)
    # Fail closed if product evidence appeared.
    if snapshot["product_compatibility_evidence"] is True:
        raise SystemExit("refusing to write snapshot while product evidence is true")
    if snapshot["m1_authorized"] not in (False, True):
        raise SystemExit("refusing to write snapshot with non-boolean m1_authorized")
    if snapshot["m1_authorized"] is True and snapshot["product_compatibility_evidence"] is True:
        raise SystemExit(
            "refusing to write snapshot: conditional GO forbids product evidence true"
        )
    path = ROOT / "docs/ssot/m0-status.snapshot.json"
    path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    behavior = snapshot["behavior"]
    print(
        f"WROTE {path} public={behavior['public_inventory_entries']} "
        f"reviewed_primary={behavior['reviewed_primary_coverage']} "
        f"gaps={behavior['uncovered_public_entries']} "
        f"projections={behavior['fixed_source_interaction_projections']} "
        f"m1_authorized={snapshot['m1_authorized']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
