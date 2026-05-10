"""Generate a non-persistent fatigue calibration report from starter plans.

The report uses the app's existing starter-plan generator with
``persist=False`` so the live ``user_selection`` table is not modified. It then
optionally applies post-generation edits and scores the resulting routines with
the shipped fatigue-meter math.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.fatigue import (  # noqa: E402
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    calculate_set_fatigue,
)
from utils.plan_generator import generate_starter_plan  # noqa: E402


DEFAULT_OUTPUT = (
    REPO_ROOT
    / "docs"
    / "fatigue_meter"
    / "generated-calibration-report.md"
)


@dataclass(frozen=True)
class Scenario:
    """One generated calibration case."""

    key: str
    label: str
    intended_anchor: str
    generator_kwargs: dict[str, Any]
    post_generate: dict[str, Any] = field(default_factory=dict)


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="deload_2d",
        label="Generated deload / easy 2-day",
        intended_anchor="light",
        generator_kwargs={
            "training_days": 2,
            "environment": "gym",
            "experience_level": "novice",
            "goal": "general",
            "volume_scale": 0.7,
            "time_budget_minutes": 45,
            "persist": False,
        },
        post_generate={"rir_delta": 2, "set_delta": -1, "min_sets": 1},
    ),
    Scenario(
        key="normal_3d",
        label="Generated normal 3-day hypertrophy",
        intended_anchor="moderate",
        generator_kwargs={
            "training_days": 3,
            "environment": "gym",
            "experience_level": "intermediate",
            "goal": "hypertrophy",
            "volume_scale": 1.0,
            "time_budget_minutes": 60,
            "persist": False,
        },
    ),
    Scenario(
        key="hard_4d",
        label="Generated hard 4-day accumulation",
        intended_anchor="heavy",
        generator_kwargs={
            "training_days": 4,
            "environment": "gym",
            "experience_level": "intermediate",
            "goal": "hypertrophy",
            "volume_scale": 1.35,
            "time_budget_minutes": 75,
            "priority_muscles": ["quadriceps", "hamstrings"],
            "persist": False,
        },
        post_generate={"rir_delta": -1},
    ),
    Scenario(
        key="overreach_5d",
        label="Generated overreach 5-day strength",
        intended_anchor="very_heavy",
        generator_kwargs={
            "training_days": 5,
            "environment": "gym",
            "experience_level": "advanced",
            "goal": "strength",
            "volume_scale": 2.0,
            "priority_muscles": ["quadriceps", "hamstrings"],
            "persist": False,
        },
        post_generate={"force_rir": 0, "set_delta": 1},
    ),
)


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _bounded_sets(
    value: Any,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    sets = _as_int(value, minimum)
    sets = max(minimum, sets)
    if maximum is not None:
        sets = min(maximum, sets)
    return sets


def apply_bulk_edit(
    exercise: dict[str, Any],
    edit: dict[str, Any],
) -> dict[str, Any]:
    """Apply a simple edit to one generated exercise row."""

    updated = dict(exercise)
    min_sets = _as_int(edit.get("min_sets"), 1)
    max_sets = edit.get("max_sets")
    max_sets_int = _as_int(max_sets, 0) if max_sets is not None else None

    if "sets" in edit:
        updated["sets"] = _bounded_sets(edit["sets"], min_sets, max_sets_int)
    if "set_delta" in edit:
        updated["sets"] = _bounded_sets(
            _as_int(updated.get("sets"), min_sets)
            + _as_int(edit["set_delta"], 0),
            min_sets,
            max_sets_int,
        )
    if "set_multiplier" in edit:
        try:
            scaled = round(
                _as_int(updated.get("sets"), min_sets)
                * float(edit["set_multiplier"])
            )
        except (TypeError, ValueError):
            scaled = _as_int(updated.get("sets"), min_sets)
        updated["sets"] = _bounded_sets(scaled, min_sets, max_sets_int)

    if "force_rir" in edit:
        fallback_rir = _as_int(updated.get("rir"), 2)
        updated["rir"] = max(0, _as_int(edit["force_rir"], fallback_rir))
    if "rir" in edit:
        fallback_rir = _as_int(updated.get("rir"), 2)
        updated["rir"] = max(0, _as_int(edit["rir"], fallback_rir))
    if "rir_delta" in edit:
        updated["rir"] = max(
            0,
            _as_int(updated.get("rir"), 2)
            + _as_int(edit["rir_delta"], 0),
        )

    for key in ("min_rep_range", "max_rep_range"):
        if key in edit:
            fallback_rep = _as_int(updated.get(key), 1)
            updated[key] = max(1, _as_int(edit[key], fallback_rep))
    return updated


def _matches(exercise: dict[str, Any], matcher: dict[str, Any]) -> bool:
    routine = matcher.get("routine")
    if routine is not None and exercise.get("routine") != routine:
        return False
    pattern = matcher.get("pattern")
    if pattern is not None and exercise.get("pattern") != pattern:
        return False
    role = matcher.get("role")
    if role is not None and exercise.get("role") != role:
        return False
    contains = matcher.get("exercise_contains")
    if contains is not None:
        name = str(exercise.get("exercise", "")).lower()
        if str(contains).lower() not in name:
            return False
    return True


def apply_scenario_edits(
    routines: dict[str, list[dict[str, Any]]],
    bulk_edit: dict[str, Any],
    targeted_edits: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return edited routines without mutating the generated plan."""

    edited: dict[str, list[dict[str, Any]]] = {}
    for routine, exercises in routines.items():
        edited[routine] = []
        for exercise in exercises:
            row = (
                apply_bulk_edit(exercise, bulk_edit)
                if bulk_edit
                else dict(exercise)
            )
            for targeted in targeted_edits:
                if _matches(row, targeted.get("match", {})):
                    row = apply_bulk_edit(row, targeted)
            edited[routine].append(row)
    return edited


def _fatigue_row(exercise: dict[str, Any]) -> dict[str, Any]:
    per_set = calculate_set_fatigue(
        exercise.get("pattern"),
        exercise.get("min_rep_range"),
        exercise.get("max_rep_range"),
        exercise.get("rir"),
    )
    sets = _as_int(exercise.get("sets"), 0)
    return {
        "routine": exercise.get("routine"),
        "exercise": exercise.get("exercise"),
        "pattern": exercise.get("pattern") or "unset",
        "role": exercise.get("role") or "",
        "sets": sets,
        "min_rep_range": exercise.get("min_rep_range"),
        "max_rep_range": exercise.get("max_rep_range"),
        "rir": exercise.get("rir"),
        "fatigue": per_set.fatigue * sets,
    }


def score_routines(
    routines: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Score generated routines and include per-exercise contributions."""

    routine_results: dict[str, Any] = {}
    sessions = []
    for routine, exercises in routines.items():
        rows = []
        fatigue_rows = []
        for exercise in exercises:
            fatigue_row = _fatigue_row(exercise)
            fatigue_rows.append(fatigue_row)
            rows.append(
                {
                    "sets": exercise.get("sets"),
                    "min_rep_range": exercise.get("min_rep_range"),
                    "max_rep_range": exercise.get("max_rep_range"),
                    "rir": exercise.get("rir"),
                    "movement_pattern": exercise.get("pattern"),
                }
            )
        session = aggregate_session_fatigue(rows)
        sessions.append(session)
        routine_results[routine] = {
            "score": session.score,
            "band": session.band,
            "set_count": session.set_count,
            "exercise_count": session.exercise_count,
            "exercises": fatigue_rows,
        }
    weekly = aggregate_weekly_fatigue(sessions)
    return {
        "weekly_score": weekly.score,
        "weekly_band": weekly.band,
        "session_count": weekly.session_count,
        "routines": routine_results,
    }


def load_edit_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def generate_report_data(
    edit_config: dict[str, Any],
    seed: int,
) -> list[dict[str, Any]]:
    """Generate and score all calibration scenarios."""

    # Seed before generating: plan_generator.py:568 uses random.uniform for
    # tie-breaking, so unseeded runs pick different exercises (scores stable).
    random.seed(seed)
    reports = []
    scenario_overrides = edit_config.get("scenarios", {})
    for scenario in SCENARIOS:
        override = scenario_overrides.get(scenario.key, {})
        generator_kwargs = dict(scenario.generator_kwargs)
        generator_kwargs.update(override.get("generator_kwargs", {}))
        generated = generate_starter_plan(**generator_kwargs)

        bulk_edit = deepcopy(scenario.post_generate)
        bulk_edit.update(override.get("post_generate", {}))
        targeted_edits = override.get("exercise_edits", [])
        routines = apply_scenario_edits(
            generated["routines"],
            bulk_edit,
            targeted_edits,
        )
        score = score_routines(routines)

        reports.append(
            {
                "key": scenario.key,
                "label": override.get("label", scenario.label),
                "intended_anchor": override.get(
                    "intended_anchor",
                    scenario.intended_anchor,
                ),
                "generator_kwargs": generator_kwargs,
                "post_generate": bulk_edit,
                "targeted_edit_count": len(targeted_edits),
                "total_exercises": sum(
                    len(exercises) for exercises in routines.values()
                ),
                "total_sets": sum(
                    exercise["sets"]
                    for exercises in routines.values()
                    for exercise in exercises
                ),
                "score": score,
            }
        )
    return reports


def _fmt_kwargs(kwargs: dict[str, Any]) -> str:
    visible = {
        key: value
        for key, value in kwargs.items()
        if key not in {"persist", "overwrite"}
    }
    return ", ".join(f"{key}={value!r}" for key, value in visible.items())


def _fmt_edit(edit: dict[str, Any], targeted_count: int) -> str:
    parts = [f"{key}={value!r}" for key, value in edit.items()]
    if targeted_count:
        parts.append(f"{targeted_count} targeted edit(s)")
    return ", ".join(parts) if parts else "none"


def render_markdown(
    reports: list[dict[str, Any]],
    edit_file: Path | None,
    seed: int,
) -> str:
    lines = [
        "# Fatigue Meter - Generated Calibration Report",
        "",
        f"**Generated:** {date.today().isoformat()}",
        f"**Seed:** {seed}",
        "**Source:** existing starter-plan generator with `persist=False`; "
        "live routines were not changed.",
        "",
        "This report exists so the owner can label generated plans from the "
        "full routine data, not from scores alone.",
        "The `intended anchor` column is only the calibration target used to "
        "build the scenario; the owner label is the value that matters.",
        "",
        "## How to use this report",
        "",
        "1. Read each scenario's full routine tables.",
        "2. Write an owner label for each scenario: `light`, `moderate`, "
        "`heavy`, or `very_heavy`.",
        "3. Tune thresholds only if at least two owner labels disagree with "
        "the computed bands.",
        "",
    ]
    if edit_file:
        lines.extend([
            f"External edit file: `{edit_file}`.",
            "",
        ])
    lines.extend([
        "## Summary",
        "",
        "| Scenario | Intended anchor | Owner label | Generator options | "
        "Post-generate edits | Sets | Weekly score | Weekly band | "
        "Session scores |",
        "|---|---|---|---|---:|---:|---:|---|---|",
    ])
    for report in reports:
        routines = report["score"]["routines"]
        session_scores = ", ".join(
            f"{routine}: {data['score']:.1f} {data['band']}"
            for routine, data in routines.items()
        )
        lines.append(
            (
                "| {label} | {anchor} |  | `{kwargs}` | `{edits}` | "
                "{sets} | {score:.1f} | {band} | {sessions} |"
            ).format(
                label=report["label"],
                anchor=report["intended_anchor"],
                kwargs=_fmt_kwargs(report["generator_kwargs"]),
                edits=_fmt_edit(
                    report["post_generate"],
                    report["targeted_edit_count"],
                ),
                sets=report["total_sets"],
                score=report["score"]["weekly_score"],
                band=report["score"]["weekly_band"],
                sessions=session_scores,
            )
        )

    for report in reports:
        post_edits = _fmt_edit(
            report["post_generate"],
            report["targeted_edit_count"],
        )
        lines.extend([
            "",
            f"## {report['label']}",
            "",
            f"- Intended anchor: `{report['intended_anchor']}`",
            "- Computed weekly score: "
            f"**{report['score']['weekly_score']:.1f} "
            f"({report['score']['weekly_band']})**",
            f"- Total sets: **{report['total_sets']}**",
            "- Generator options: "
            f"`{_fmt_kwargs(report['generator_kwargs'])}`",
            "- Post-generate edits: "
            f"`{post_edits}`",
            "- Owner label: ",
            "",
        ])
        for routine, data in report["score"]["routines"].items():
            lines.extend([
                f"### Routine {routine} - {data['score']:.1f} "
                f"({data['band']}), {data['set_count']} sets",
                "",
                "| # | Exercise | Pattern | Role | Sets | Reps | RIR | "
                "Fatigue |",
                "|---:|---|---|---|---:|---|---:|---:|",
            ])
            for index, exercise in enumerate(data["exercises"], start=1):
                reps = (
                    f"{exercise['min_rep_range']}-"
                    f"{exercise['max_rep_range']}"
                )
                lines.append(
                    f"| {index} | {exercise['exercise']} | "
                    f"{exercise['pattern']} | {exercise['role']} | "
                    f"{exercise['sets']} | {reps} | {exercise['rir']} | "
                    f"{exercise['fatigue']:.1f} |"
                )
            lines.append("")
    lines.extend([
        "## Optional edit-file format",
        "",
        "To test your own post-generate edits, create a JSON file and rerun:",
        "",
        "```powershell",
        "python scripts/fatigue_calibration_report.py "
        "--edits docs/fatigue_meter/my-calibration-edits.json",
        "```",
        "",
        "Example:",
        "",
        "```json",
        json.dumps(
            {
                "scenarios": {
                    "normal_3d": {
                        "post_generate": {"rir_delta": -1},
                        "exercise_edits": [
                            {
                                "match": {
                                    "routine": "A",
                                    "exercise_contains": "Squat",
                                },
                                "set_delta": 1,
                                "rir": 1,
                            }
                        ],
                    }
                }
            },
            indent=2,
        ),
        "```",
        "",
        "*End of generated calibration report. Regenerate after changing "
        "generator behavior or edit inputs.*",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown output path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--edits",
        type=Path,
        default=None,
        help=(
            "Optional JSON file with scenario overrides and post-generate "
            "edits."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help=(
            "Seed for the starter-plan generator's tie-breaking randomness. "
            "Same seed produces an identical report. Default: 42."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    edit_config = load_edit_file(args.edits)
    reports = generate_report_data(edit_config, args.seed)
    markdown = render_markdown(reports, args.edits, args.seed)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output}")
    for report in reports:
        print(
            f"{report['key']}: {report['score']['weekly_score']:.1f} "
            f"{report['score']['weekly_band']} ({report['total_sets']} sets)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
