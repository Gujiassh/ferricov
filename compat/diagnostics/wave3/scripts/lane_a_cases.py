"""Wave3 Lane A CASE_SPECS — geninfo child stop/keep/ignore Oracle matrix.

Owned planned IDs:
  PAR-GENINFO-CHILD-STOP-001
  PAR-GENINFO-CHILD-EXIT-ORACLE-001
  PAR-GENINFO-CHILD-IGNORE1-ORACLE-001
  PAR-GENINFO-CHILD-IGNORE2-ORACLE-001

Must NOT bind *-FERRICOV-001 IDs.
"""

from __future__ import annotations

from typing import Any

# Implementer fills CASE_SPECS. Each entry mirrors wave2 capture schema:
# id, argv, fixtures, planned_case_ids, kind, optional env, optional notes,
# optional timeout_seconds (for watchdog 124 cases).
CASE_SPECS: list[dict[str, Any]] = []
