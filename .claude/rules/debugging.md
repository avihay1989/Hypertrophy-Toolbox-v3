---
paths:
  - "utils/logger.py"
  - "utils/request_id.py"
  - "utils/errors.py"
  - "logs/**"
---

# Debugging guide

## Request tracing
1. Every request gets a UUID via `utils/request_id.py:19` → stored in `flask.g.request_id`.
2. Returned in response header `X-Request-ID` (`request_id.py:44`) and JSON `requestId` field.
3. Included in every log line via `RequestIdFilter` (`logger.py:10-20`).
4. Log format: `%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s [%(filename)s:%(lineno)d]`

## Searching logs
```bash
# bash / Git Bash
grep "req_abc123" logs/app.log
grep -i "ERROR" logs/app.log | tail -20

# PowerShell
Select-String "req_abc123" logs/app.log
Select-String -Pattern "ERROR" logs/app.log | Select-Object -Last 20
```
Log file: `logs/app.log` (rotating 10MB × 5, `logger.py:48-53`) and console (INFO+, `logger.py:61`).

## Slow request detection
- Queries >100ms: WARNING in `database.py:250`.
- Requests >1000ms: WARNING in `logger.py:97`.

## Typical failures
| Symptom | Cause | Evidence |
|---|---|---|
| `database is locked` | Concurrent writes (e.g. reloader spawned 2 processes) | Check `_DB_LOCK` in `database.py:24`; disable reloader |
| Empty exercise list on fresh start | No DB backup restored | `db_initializer.py:348` |
| `FK constraint failed` | Inserting log without valid `workout_plan_id` | `db_initializer.py:257` |
| 404 on new route in tests | Blueprint not in `conftest.py` | See routes rule, "Adding a blueprint" |
| Effective sets = raw sets | RIR/RPE null → neutral factor 1.0 | By design (`effective_sets.py:6-7`) |

## Response contract recap
```python
# Success:  {"ok": True, "status": "success", "data": ..., "message": ..., "requestId": ...}
# Error:    {"ok": False, "status": "error", "message": ..., "error": {"code": ..., "message": ..., "requestId": ...}}
```
XHR detection (`utils/errors.py:47-64`): checks `X-Requested-With`, `Accept: application/json`, or `/api/` prefix.
