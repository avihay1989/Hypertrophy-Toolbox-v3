"""Fatigue Meter — Phase 2 Stimulus-to-Fatigue Ratio (page-level, D2.6).

Internal leaf of the ``utils.fatigue`` facade (WP2.4). Bodies moved verbatim from
the original ``utils/fatigue.py`` SFR section. Pure: no sibling leaf dependency,
no DB access. Stimulus is the page-level effective_sets sum computed by the route
layer; fatigue is the Phase 1 session/weekly score for the same side.
"""
from typing import Optional


# =============================================================================
# Phase 2 — Stimulus-to-Fatigue Ratio (page-level, D2.6)
# =============================================================================
# SFR ships as two cards at the top of /fatigue (planned + logged). Stimulus
# is the page-level effective_sets sum (computed by the route layer from
# utils.effective_sets); fatigue is the Phase 1 session/weekly score for the
# same side. Per-muscle SFR stays deferred (D2.6).


SFR_FATIGUE_ZERO_SENTINEL: Optional[float] = None
"""Sentinel used when the denominator (fatigue) is zero — render as "—",
never as `inf`. Per §16.1 SFR test row."""


def compute_sfr(
    stimulus: Optional[float],
    fatigue: Optional[float],
) -> Optional[float]:
    """
    stimulus / fatigue, with two guarded cases per §16.1:
      - fatigue == 0 (or None)  → returns SFR_FATIGUE_ZERO_SENTINEL (None);
                                  the template renders "—".
      - stimulus == 0           → returns 0.0; the user did the work but
                                  it produced no recorded stimulus.
    Both positive → straightforward ratio.
    """
    if fatigue is None or fatigue <= 0:
        return SFR_FATIGUE_ZERO_SENTINEL
    if stimulus is None:
        return 0.0
    return float(stimulus) / float(fatigue)
