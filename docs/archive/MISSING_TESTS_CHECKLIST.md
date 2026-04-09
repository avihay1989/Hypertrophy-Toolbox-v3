# Missing Tests Checklist

> **Goal**: Cover all untested modules with proper unit and integration tests.
> **Tracking**: Update status as tests are implemented.

---

## Progress Summary

| Priority | Total | Completed | Remaining |
|----------|-------|-----------|-----------|
| 🔴 Critical | 3 | 3 | 0 |
| 🟠 High | 4 | 4 | 0 |
| 🟡 Medium | 4 | 4 | 0 |
| 🟢 Low | 3 | 3 | 0 |
| **TOTAL** | **14** | **14** | **0** |

---

## 🔴 CRITICAL Priority

These modules contain core business logic that directly affects data integrity and calculations.

### 1. `utils/business_logic.py`
- [x] **Status**: ✅ COMPLETED (23 tests)
- **Risk**: Core weekly summary calculations, affects all volume tracking
- **Functions to test**:
  - [x] `BusinessLogic.calculate_weekly_summary()` - Total method
  - [x] `BusinessLogic.calculate_weekly_summary()` - Fractional method  
  - [x] `BusinessLogic.calculate_weekly_summary()` - Direct method
  - [x] `BusinessLogic._get_query_for_method()` - Invalid method handling
  - [x] Edge cases: empty database, null values, closed connection
- **Test file**: `tests/test_business_logic.py`

### 2. `utils/session_summary.py`
- [x] **Status**: ✅ COMPLETED (28 tests)
- **Risk**: Session-level analytics, per-routine volume tracking
- **Functions to test**:
  - [x] `calculate_session_summary()` - basic aggregation
  - [x] `calculate_session_summary()` - with routine filter
  - [x] `calculate_session_summary()` - with time_window filter
  - [x] `calculate_session_summary()` - RAW counting mode
  - [x] `calculate_session_summary()` - EFFECTIVE counting mode
  - [x] `calculate_session_summary()` - DIRECT_ONLY contribution mode
  - [x] `calculate_session_summary()` - TOTAL contribution mode
  - [x] Warning level calculations (ok/borderline/excessive)
- **Test file**: `tests/test_session_summary.py`

### 3. `utils/exercise_manager.py`
- [x] **Status**: ✅ COMPLETED (36 tests)
- **Risk**: Exercise CRUD operations, data mutations
- **Functions to test**:
  - [x] `ExerciseManager.get_exercises()` - with filters
  - [x] `ExerciseManager.get_exercises()` - without filters
  - [x] `ExerciseManager.add_exercise()` - success case
  - [x] `ExerciseManager.add_exercise()` - duplicate prevention
  - [x] `ExerciseManager.add_exercise()` - missing required fields
  - [x] `ExerciseManager.delete_exercise()` - success case
  - [x] `ExerciseManager.save_exercise()` - insert new
  - [x] `ExerciseManager.save_exercise()` - update existing
  - [x] `ExerciseManager.save_exercise()` - missing exercise_name
- **Test file**: `tests/test_exercise_manager.py`

---

## 🟠 HIGH Priority

Important features that impact user experience and data accuracy.

### 4. `utils/volume_ai.py`
- [x] **Status**: ✅ COMPLETED (38 tests)
- **Risk**: AI-based volume suggestions, user recommendations
- **Functions to test**:
  - [x] `generate_volume_suggestions()` - basic mode
  - [x] `generate_volume_suggestions()` - advanced mode
  - [x] `generate_volume_suggestions()` - invalid mode defaults to basic
  - [x] Total volume warning threshold
  - [x] Sets per session warning (>10 sets)
  - [x] Low sets per session info (<3 sets)
  - [x] Category volume suggestions (push/pull/legs < 30)
  - [x] Edge cases: empty muscle_volumes, 0 training_days
- **Test file**: `tests/test_volume_ai.py`

### 5. `utils/volume_classifier.py`
- [x] **Status**: ✅ COMPLETED (57 tests)
- **Risk**: Volume classification for UI display
- **Functions to test**:
  - [x] `get_volume_class()` - all thresholds (low/medium/high/ultra)
  - [x] `get_volume_label()` - all labels
  - [x] `get_effective_volume_label()` - integration with effective_sets
  - [x] `get_volume_tooltip()` - all ranges
  - [x] `get_session_warning_tooltip()` - OK/BORDERLINE/EXCESSIVE
  - [x] `get_category_tooltip()` - Mechanic/Utility/Force
  - [x] `get_subcategory_tooltip()` - all subcategories
- **Test file**: `tests/test_volume_classifier.py`

### 6. `utils/filter_predicates.py`
- [x] **Status**: ✅ COMPLETED (43 tests)
- **Risk**: SQL query building, potential injection vectors
- **Functions to test**:
  - [x] `FilterPredicates.build_filter_query()` - valid filters
  - [x] `FilterPredicates.build_filter_query()` - invalid field rejection
  - [x] `FilterPredicates.build_filter_query()` - empty filters
  - [x] `FilterPredicates.build_filter_query()` - partial match fields (LIKE)
  - [x] `FilterPredicates.build_filter_query()` - exact match fields
  - [x] `FilterPredicates.build_filter_query()` - advanced_isolated_muscles special case
  - [x] `FilterPredicates.get_exercises()` - integration test
  - [x] SQL injection prevention validation
- **Test file**: `tests/test_filter_predicates.py`

### 7. `routes/session_summary.py`
- [x] **Status**: ✅ COMPLETED (36 tests)
- **Risk**: Session summary API endpoints
- **Functions to test**:
  - [x] `GET /session_summary` - page load
  - [x] `GET /session_summary` - with routine filter
  - [x] `GET /session_summary` - with date range
  - [x] `GET /api/session_summary` - JSON response format
  - [x] `_parse_counting_mode()` - raw/effective
  - [x] `_parse_contribution_mode()` - direct/total
  - [x] Response structure validation
- **Test file**: `tests/test_session_summary_routes.py`

---

## 🟡 MEDIUM Priority

Supporting functionality that enhances reliability.

### 8. `utils/filter_cache.py`
- [x] **Status**: ✅ COMPLETED (46 tests)
- **Risk**: Caching correctness, thread safety
- **Functions to test**:
  - [x] `FilterCache.get()` - cache hit
  - [x] `FilterCache.get()` - cache miss
  - [x] `FilterCache.get()` - expired entry
  - [x] `FilterCache.set()` - store value
  - [x] `FilterCache.invalidate()` - entire cache
  - [x] `FilterCache.invalidate()` - specific table
  - [x] `FilterCache.invalidate()` - specific column
  - [x] `FilterCache.get_stats()` - statistics
  - [x] Cache disabled mode
  - [x] Thread safety (concurrent access)
- **Test file**: `tests/test_filter_cache.py`

### 9. `utils/muscle_group.py`
- [x] **Status**: ✅ COMPLETED (22 tests)
- **Risk**: Muscle group queries for exercises
- **Functions to test**:
  - [x] `MuscleGroupHandler.get_exercise_names()` - success
  - [x] `MuscleGroupHandler.get_exercise_names()` - empty database
  - [x] `MuscleGroupHandler.get_muscle_groups()` - valid exercise
  - [x] `MuscleGroupHandler.get_muscle_groups()` - unknown exercise
  - [x] `MuscleGroupHandler.fetch_muscle_groups_summary()` - aggregation
  - [x] `MuscleGroupHandler.fetch_full_muscle_data()` - full data
- **Test file**: `tests/test_muscle_group.py`

### 10. `utils/maintenance.py`
- [x] **Status**: ✅ COMPLETED (18 tests)
- **Risk**: Database maintenance, schema migrations
- **Functions to test**:
  - [x] `_exec_many()` - transaction execution
  - [x] `_exec_many()` - rollback on error
  - [x] `_exec_many()` - retry on database locked
  - [x] Normalize SQL statements execution
  - [x] Rebuild exercise_isolated_muscles mapping
  - [x] Index creation
- **Test file**: `tests/test_maintenance.py`

### 11. `utils/database_indexes.py`
- [x] **Status**: ✅ COMPLETED (22 tests)
- **Risk**: Database performance optimization
- **Functions to test**:
  - [x] Index creation functions
  - [x] Index existence checks
  - [x] Performance impact validation
- **Test file**: `tests/test_database_indexes.py`

---

## 🟢 LOW Priority

Utility functions and edge cases.

### 12. `utils/config.py`
- [x] **Status**: ✅ COMPLETED (20 tests)
- **Risk**: Configuration loading
- **Functions to test**:
  - [x] Default values
  - [x] Environment variable overrides
  - [x] DB_FILE path handling
- **Test file**: `tests/test_config.py`

### 13. `utils/logger.py`
- [x] **Status**: ✅ COMPLETED (14 tests)
- **Risk**: Logging configuration
- **Functions to test**:
  - [x] `get_logger()` returns configured logger
  - [x] Log level configuration
  - [x] File handler setup
- **Test file**: `tests/test_logger.py`

### 14. `utils/constants.py`
- [x] **Status**: ✅ COMPLETED (46 tests)
- **Risk**: Application constants and mappings
- **Functions to test**:
  - [x] MUSCLE_GROUPS constant validation
  - [x] FORCE mapping normalization
  - [x] MECHANIC mapping normalization
  - [x] EQUIPMENT_SYNONYMS normalization
  - [x] MUSCLE_ALIAS normalization
- **Test file**: `tests/test_constants.py`

---

## Implementation Order

1. 🔴 `test_business_logic.py` - Core calculations
2. 🔴 `test_session_summary.py` - Session analytics
3. 🔴 `test_exercise_manager.py` - CRUD operations
4. 🟠 `test_volume_ai.py` - AI suggestions
5. 🟠 `test_volume_classifier.py` - UI classifications
6. 🟠 `test_filter_predicates.py` - Query building
7. 🟠 `test_session_summary_routes.py` - API endpoints
8. 🟡 `test_filter_cache.py` - Caching
9. 🟡 `test_muscle_group.py` - Muscle queries
10. 🟡 `test_maintenance.py` - DB maintenance
11. 🟡 `test_database_indexes.py` - Indexes
12. 🟢 `test_config.py` - Configuration
13. 🟢 `test_logger.py` - Logging
14. 🟢 `test_constants.py` - Constants

---

## Notes

- Each test file should follow the existing pattern in `tests/conftest.py`
- Use fixtures: `client`, `db_handler`, `exercise_factory`, `workout_plan_factory`
- Test both success and error cases
- Include edge cases: empty data, null values, invalid inputs
- Mark completed items with `[x]` and update the progress summary table

---

*Last updated: February 8, 2026*
