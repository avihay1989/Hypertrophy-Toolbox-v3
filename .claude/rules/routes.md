---
paths:
  - "routes/**/*.py"
---

# Routes guide

## Response contract (`utils/errors.py`)
```python
# Success (line 33):  {"ok": True, "status": "success", "data": ..., "message": ..., "requestId": ...}
# Error (line 91):    {"ok": False, "status": "error", "message": ..., "error": {"code": ..., "message": ..., "requestId": ...}}
```
XHR detection (`utils/errors.py:47-64`): checks `X-Requested-With`, `Accept: application/json`, or `/api/` prefix.

**All JSON routes must use `success_response()` / `error_response()`** (legacy `success`/`error` exceptions cleaned up 2026-05-21).

The replace-exercise "no result" cases (`NO_CANDIDATES`, `DUPLICATE`, `SELECTION_FAILED` in `routes/workout_plan.py`) intentionally pass `status_code=200` to `error_response()` so the response is `200 + {"ok": false, "error": {"code": "...", "reason": "..."}}` — the JS swap handler in `static/js/modules/workout-plan.js` keys off `error.reason` rather than HTTP status, and the E2E spec `e2e/replace-exercise-errors.spec.ts` mocks the same shape. If you add a new "couldn't be processed" outcome, follow the same pattern: `error_response("CODE", "message", 200, reason="...")`.

## Endpoint template
```python
from flask import Blueprint, request
from utils.errors import success_response, error_response
from utils.logger import get_logger

myfeature_bp = Blueprint('myfeature', __name__)
logger = get_logger()

@myfeature_bp.route('/api/myfeature', methods=['POST'])
def my_endpoint():
    try:
        data = request.get_json() or {}
        field = data.get('field')
        if not field:
            return error_response("VALIDATION_ERROR", "field is required", 400)
        result = do_something(field)
        return success_response(data=result, message="Done")
    except Exception as e:
        logger.exception("Error in my_endpoint")
        return error_response("INTERNAL_ERROR", "Unexpected error", 500)
```

## Adding a blueprint — three places
1. Create `routes/newbp.py` with `newbp_bp = Blueprint('newbp', __name__)`
2. In `app.py`: `from routes.newbp import newbp_bp` + `app.register_blueprint(newbp_bp)`
3. In `tests/conftest.py` `app` fixture (~line 59-69): same import + `app.register_blueprint(newbp_bp)`

Missing step 3 = 404s in tests.

## Filters & SQL injection prevention
Two layers:
1. **Column whitelist** — `ALLOWED_COLUMNS` dict in `routes/filters.py:115-139`. Call `validate_column_name()` (line 147) before any dynamic column name.
2. **Parameterized values** — `FilterPredicates.build_filter_query()` in `utils/filter_predicates.py:45` uses `?`. `PARTIAL_MATCH_FIELDS` (line 34) use `LIKE ?` with `%value%`; others use exact match.

To add a filterable column:
- [ ] Add to `ALLOWED_COLUMNS` in `routes/filters.py`
- [ ] Add to `FilterPredicates.VALID_FILTER_FIELDS` in `utils/filter_predicates.py:17`
- [ ] If partial match: add to `PARTIAL_MATCH_FIELDS` (line 34)
- [ ] If muscle-type: add mapping in `SIMPLE_TO_DB_MUSCLE` / `SIMPLE_TO_ADVANCED_ISOLATED` (`routes/filters.py:17-69`)

## Input validation
Routes validate bounds before calling utils. Example pattern in `routes/workout_plan.py`: sets 1-20, reps 1-100, weight ≥ 0, RIR 0-10.

## Auth boundaries
**No authentication exists.** Single-user local app. `POST /erase-data` (`app.py:125`) requires `{"confirm": "ERASE_ALL_DATA"}` in body; requests without it return 400. A pre-erase snapshot writes to `data/auto_backup/` before wiping. **Do not expose this app to an untrusted network.**

## Filename sanitization
`utils/export_utils.py` has `sanitize_filename()` to strip path traversal and dangerous characters from export filenames.

## Logger pattern
```python
from utils.logger import get_logger
logger = get_logger()
```
Never use `print()` or `logging.getLogger(...)` directly.
