"""Read-only DB facts for the Stage 4 automation health check (JSON on stdout).

The PowerShell health-check script (``check_fatigue_stage4_automation.ps1``)
consumes this so it never has to shell out to ``sqlite3`` (not guaranteed on
PATH). Strictly read-only: a single ``COUNT(*)`` against ``workout_log`` via
``DatabaseHandler``. It never writes thresholds, scenarios, calibration rows,
or the database — it only counts whether real logged workouts exist yet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import utils.config as config  # noqa: E402
from utils.database import DatabaseHandler  # noqa: E402


def main() -> int:
    db_path = str(config.DB_FILE)
    out: dict[str, object] = {
        "db_path": db_path,
        "db_exists": Path(db_path).exists(),
        "workout_log_rows": None,
        "error": None,
    }
    if out["db_exists"]:
        # A fresh / mid-migration DB may not have workout_log yet, and the file
        # can be locked by a running app — surface either to the PS layer as a
        # readable status rather than crashing the health check.
        try:
            with DatabaseHandler() as db:
                row = db.fetch_one("SELECT COUNT(*) AS c FROM workout_log")
                out["workout_log_rows"] = int(row["c"]) if row else 0
        except Exception as exc:
            out["error"] = str(exc)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
