"""
Fatigue Meter — pure calculation module (Phase 1 + Phase 2).

Phase 1 ships a single global fatigue score for a planned training session
or week. This module is the math layer; route wiring (which reads
`user_selection`) and the badge template come in later chapters.

Per `docs/fatigue_meter/PLANNING.md` Stage 0:
- D3: fatigue uses **raw set count**, independent of `CountingMode`.
  Effective-sets logic in `utils/effective_sets.py` is unrelated and is
  not consulted here.
- D6: no decay in Phase 1.
- D7: no technique modifier in Phase 1.
- D8: RIR multiplier is the discrete-bucket form below.
- D10: planned `user_selection` is the data source — the route layer
  passes already-loaded rows in; this module never touches the DB.
- D11: numbers locked from `BRAINSTORM.md §24.B`.

Per-set formula (§24.B):
    set_fatigue = pattern_weight * load_multiplier * intensity_multiplier
Aggregations:
    session_fatigue = Σ (sets * set_fatigue) across exercises in the session
    weekly_fatigue  = Σ session_fatigue across sessions in the week

Threshold convention: lower-inclusive, upper-exclusive. A score equal to
a band's upper bound classifies into the next-higher band (e.g. 20.0 →
"moderate", 50.0 → "heavy").

This module is pure: no DB access, no Flask imports, no `routes` imports.

Structure (WP2.4, Refactor Plan v3 Phase 2)
-------------------------------------------
The four banner-delimited concerns now live in the internal package
``utils/_fatigue/`` and are re-exported here so ``utils.fatigue`` stays the
single public facade with a byte-identical surface and import order:
- ``utils._fatigue.core``       — Phase 1 per-set / session / weekly math.
- ``utils._fatigue.per_muscle`` — Phase 2 per-muscle channel (Stage 2).
- ``utils._fatigue.period``     — Phase 2 period selector + logged adapters.
- ``utils._fatigue.sfr``        — Phase 2 Stimulus-to-Fatigue Ratio.
Import the internal leaves only through this facade.
"""
from utils._fatigue.core import (  # noqa: F401
    PATTERN_WEIGHTS,
    DEFAULT_PATTERN_WEIGHT,
    LOAD_MULTIPLIER_BUCKETS,
    DEFAULT_LOAD_MULTIPLIER,
    INTENSITY_MULTIPLIER_BUCKETS,
    DEFAULT_INTENSITY_MULTIPLIER,
    SESSION_FATIGUE_BANDS,
    WEEKLY_FATIGUE_BANDS,
    SetFatigueResult,
    SessionFatigueResult,
    WeeklyFatigueResult,
    _resolve_pattern_weight,
    _resolve_load_multiplier,
    _rir_to_bucket,
    _resolve_intensity_multiplier,
    calculate_set_fatigue,
    _coerce_sets,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    _classify,
    classify_session_fatigue,
    classify_weekly_fatigue,
)
from utils._fatigue.per_muscle import (  # noqa: F401
    MUSCLE_CONTRIBUTION_WEIGHTS,
    UNASSIGNED_MUSCLE_BUCKET,
    MUSCLE_VOLUME_LANDMARKS,
    MuscleFatigueResult,
    canonicalize_muscle_for_fatigue,
    classify_muscle_fatigue,
    muscle_percent_of_mrv,
    aggregate_muscles_for_session,
    summarize_muscle_bars,
)
from utils._fatigue.period import (  # noqa: F401
    VALID_PERIODS,
    DEFAULT_PERIOD,
    PERIOD_LABELS,
    normalize_period,
    _coerce_date,
    compute_period_window,
    filter_rows_by_date_window,
    adapt_logged_row,
    aggregate_logged_muscles,
)
from utils._fatigue.sfr import (  # noqa: F401
    SFR_FATIGUE_ZERO_SENTINEL,
    compute_sfr,
)
