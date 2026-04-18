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

**All JSON routes must use `success_response()` / `error_response()`.** Known exceptions (verified 2026-04-18):
- `routes/weekly_summary.py:133,139` — pattern coverage still returns legacy `success`/`error` JSON
- `routes/workout_plan.py:1079,1093,1114,1125` — replace-exercise fallback paths return legacy ad-hoc JSON with 200 error payloads

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

**Latent risk**: `utils/filter_cache.py:85` has `f"SELECT DISTINCT {column} FROM {table}"` — column/table NOT parameterized there. Only caller is `warm_cache()` (line 113) with hardcoded names. Any new caller must pre-validate.

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
