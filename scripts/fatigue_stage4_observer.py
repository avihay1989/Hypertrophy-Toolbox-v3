"""Fatigue Meter - Phase 2 Stage 4 calibration observer (read-only).

Automates the *measurement* half of the Stage 4 calibration window so the owner
only has to supply felt labels. It reuses ``utils.fatigue_data
.build_fatigue_page_context`` verbatim, so every band it prints is byte-identical
to what ``GET /fatigue`` renders. It is strictly read-only against
``data/database.db`` and never edits thresholds, scenarios, or tests (the Stage 4
guardrails in ``docs/fatigue_meter/PHASE2_PLANNING.md`` §10 / ``CLAUDE.md``).

Two modes:

  --observe  (default)  Print a per-period digest (planned + logged bands for
                        all three windows) and, when real logged data exists,
                        append one *logged-side* pending row per muscle to the
                        calibration CSV for the owner to annotate with a felt
                        label. Logged-only because the Stage 4 signal is
                        real-use: ``workout_log`` data drives it (Phase 1 §4.2).

  --analyze            Read the CSV, compute engine-vs-felt direction for every
                       row the owner has filled, and report which muscles have
                       reached the **two same-direction disagreements = signal**
                       bar. One isolated disagreement is noise.

Nothing here lowers the methodology bar: threshold tuning still requires >=2
same-direction *real-use* disagreements AND a fresh owner go-ahead. Synthetic
data is out of scope on purpose (the ``hard_4d`` precedent).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.fatigue import VALID_PERIODS, PERIOD_LABELS  # noqa: E402
from utils.fatigue_data import build_fatigue_page_context  # noqa: E402

DEFAULT_CSV = REPO_ROOT / "docs" / "fatigue_meter" / "stage4_calibration_log.csv"

CSV_FIELDS = [
    "run_date",
    "period",
    "muscle",
    "side",
    "engine_band",
    "percent_of_mrv",
    "score",
    "felt_band",  # owner fills: light | moderate | heavy | very_heavy
    "note",       # owner fills: free text
]

# Band ordering for direction math - must match SESSION_FATIGUE_BANDS order.
BAND_ORDINAL = {"light": 0, "moderate": 1, "heavy": 2, "very_heavy": 3}

# Six canonical labels that intentionally render neutral ("-") pending vetted
# MEV/MAV/MRV (Phase-3 follow-up, PHASE2_PLANNING.md §10). Seeing them with no
# landmarks is expected, not a bug.
UNRANKED_LABELS = {
    "Front-Shoulder",
    "Rear-Shoulder",
    "Lower Back",
    "Hip-Adductors",
    "Middle-Traps",
    "Neck",
}


def _fmt_pct(pct: Optional[float]) -> str:
    return "-" if pct is None else f"{pct:.0f}%"


def _print_side(label: str, bars: list[dict[str, Any]], has_data: bool) -> None:
    print(f"  {label}:")
    if not has_data:
        print("    (no data in this window)")
        return
    if not bars:
        print("    (no muscles)")
        return
    for bar in bars:
        flags = []
        if bar["muscle"] == "Unassigned":
            flags.append("[!] UNASSIGNED leaked into bars - name the offending exercise")
        if bar["muscle"] in UNRANKED_LABELS:
            flags.append("unranked (neutral by design)")
        flag_str = ("   <- " + "; ".join(flags)) if flags else ""
        band = bar["band"] or "-"
        print(
            f"    {bar['muscle']:<20} band={band:<11} "
            f"%MRV={_fmt_pct(bar['percent_of_mrv']):>5} "
            f"score={bar['score']:.1f}{flag_str}"
        )


def _pending_combos(csv_path: Path) -> set[tuple[str, str]]:
    """(period, muscle) pairs that already have an unannotated row awaiting a
    felt label. Skipping these keeps a daily schedule from appending duplicate
    pending rows — a fresh row is only added once the previous one is filled."""
    if not csv_path.exists():
        return set()
    pending: set[tuple[str, str]] = set()
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not (r.get("felt_band") or "").strip():
                pending.add((r.get("period", ""), r.get("muscle", "")))
    return pending


def observe(csv_path: Path, today: Optional[date] = None) -> int:
    """Print the digest and append logged-side pending rows. Returns appended count."""
    run_date = (today or date.today()).isoformat()
    print("=" * 78)
    print(f"Fatigue Stage 4 observer - {run_date}")
    print("=" * 78)

    pending = _pending_combos(csv_path)
    appended_rows: list[dict[str, Any]] = []
    any_logged = False

    for period in VALID_PERIODS:
        ctx = build_fatigue_page_context(period, today=today)
        print(f"\n[{period}] {PERIOD_LABELS[period]}  "
              f"(window {ctx['window_start']} -> {ctx['window_end']})")
        print(f"  planned fatigue: {ctx['planned_fatigue_score']:.1f} "
              f"({ctx['planned_fatigue_band']})   "
              f"SFR {ctx['sfr_planned'] if ctx['sfr_planned'] is not None else '-'}")
        print(f"  logged fatigue:  {ctx['logged_fatigue_score']:.1f} "
              f"({ctx['logged_fatigue_band']})   "
              f"SFR {ctx['sfr_logged'] if ctx['sfr_logged'] is not None else '-'}")
        _print_side("planned bars", ctx["muscles_planned"], ctx["planned_has_data"])
        _print_side("logged bars", ctx["muscles_logged"], ctx["logged_has_data"])

        # Calibration rows are logged-side only (real-use signal).
        if ctx["logged_has_data"]:
            any_logged = True
            for bar in ctx["muscles_logged"]:
                if (period, bar["muscle"]) in pending:
                    continue  # already has an unfilled row awaiting annotation
                appended_rows.append({
                    "run_date": run_date,
                    "period": period,
                    "muscle": bar["muscle"],
                    "side": "logged",
                    "engine_band": bar["band"] or "",
                    "percent_of_mrv": ("" if bar["percent_of_mrv"] is None
                                       else f"{bar['percent_of_mrv']:.1f}"),
                    "score": f"{bar['score']:.2f}",
                    "felt_band": "",
                    "note": "",
                })

    print("\n" + "-" * 78)
    if not any_logged:
        print("No logged real-use data in any window yet. Nothing appended to the")
        print("calibration log - Stage 4 stays blocked on actual logged workouts.")
        print("(workout_log is empty; the badge/page are correct, there's just")
        print(" nothing to calibrate against until you train and log sessions.)")
        return 0

    if not appended_rows:
        print("Logged data present, but every (period, muscle) already has an")
        print("unannotated pending row. Fill the 'felt_band' values in the log,")
        print("then re-run to collect the next round.")
        return 0

    _append_csv(csv_path, appended_rows)
    print(f"Appended {len(appended_rows)} logged-side pending row(s) to:")
    print(f"  {csv_path}")
    print("Fill the 'felt_band' column (light|moderate|heavy|very_heavy) for any")
    print("muscle you have an opinion on, then run with --analyze.")
    return len(appended_rows)


def _append_csv(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _direction(engine_band: str, felt_band: str) -> Optional[str]:
    """engine_high = engine over-reports vs felt; engine_low = under-reports."""
    e = BAND_ORDINAL.get(engine_band)
    f = BAND_ORDINAL.get(felt_band)
    if e is None or f is None:
        return None
    if e > f:
        return "engine_high"
    if e < f:
        return "engine_low"
    return "agree"


def analyze(csv_path: Path) -> int:
    """Tally filled disagreements. Returns count of muscles at signal level."""
    if not csv_path.exists():
        print(f"No calibration log yet at {csv_path}. Run --observe first.")
        return 0

    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    filled = [r for r in rows if (r.get("felt_band") or "").strip()]
    print("=" * 78)
    print(f"Fatigue Stage 4 analysis - {csv_path.name}")
    print("=" * 78)
    print(f"Total rows: {len(rows)}   annotated rows: {len(filled)}")
    if not filled:
        print("No felt_band values filled yet - nothing to analyze.")
        return 0

    # (muscle, direction) -> list of (run_date, period, engine, felt)
    tally: dict[tuple[str, str], list[tuple[str, str, str, str]]] = {}
    invalid = 0
    for r in filled:
        d = _direction(r["engine_band"], r["felt_band"].strip())
        if d is None:
            invalid += 1
            continue
        if d == "agree":
            continue
        key = (r["muscle"], d)
        tally.setdefault(key, []).append(
            (r["run_date"], r["period"], r["engine_band"], r["felt_band"].strip())
        )

    if invalid:
        print(f"[!] {invalid} row(s) had an unrecognized felt_band - "
              f"use light|moderate|heavy|very_heavy.")

    signals = {k: v for k, v in tally.items() if len(v) >= 2}
    noise = {k: v for k, v in tally.items() if len(v) == 1}

    print("\nDisagreements at SIGNAL level (>=2 same-direction):")
    if not signals:
        print("  none - no muscle has >=2 same-direction real-use disagreements.")
    else:
        for (muscle, direction), hits in sorted(signals.items()):
            print(f"  * {muscle}  [{direction}]  x{len(hits)}")
            for run_date, period, engine, felt in hits:
                print(f"      {run_date} {period}: engine={engine} vs felt={felt}")

    print("\nIsolated disagreements (noise - 1 occurrence each):")
    if not noise:
        print("  none.")
    else:
        for (muscle, direction), hits in sorted(noise.items()):
            run_date, period, engine, felt = hits[0]
            print(f"  * {muscle} [{direction}] - {run_date} {period}: "
                  f"engine={engine} vs felt={felt}")

    print("\n" + "-" * 78)
    if signals:
        print(f"{len(signals)} muscle/direction pair(s) reached the signal bar.")
        print("Threshold tuning is *eligible* but still requires a fresh owner")
        print("go-ahead before editing utils/fatigue.py landmarks/bands.")
    else:
        print("No threshold change warranted. Keep observing.")
    return len(signals)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze filled felt labels instead of observing.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help=f"Calibration log path (default: {DEFAULT_CSV}).")
    parser.add_argument("--date", type=str, default=None,
                        help="Override 'today' as YYYY-MM-DD (testing only).")
    args = parser.parse_args(argv)

    today = (datetime.strptime(args.date, "%Y-%m-%d").date()
             if args.date else None)

    if args.analyze:
        analyze(args.csv)
    else:
        observe(args.csv, today=today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
