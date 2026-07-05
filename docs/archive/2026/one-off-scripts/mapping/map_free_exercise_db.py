#!/usr/bin/env python3
"""Generate free-exercise-db image mapping proposals.

Reads ``static/vendor/free-exercise-db/exercises.json`` and the local
``exercises`` table, fuzzy-matches each local exercise to the best
upstream entry, and writes a 5-column CSV with one row per local
exercise. Every row starts with ``review_status=auto``; a human reviewer
flips that to ``confirmed`` / ``rejected`` / ``manual`` before
``scripts/apply_free_exercise_db_mapping.py`` is run.

Score combines:

  - Name similarity (0-100) via character-trigram Jaccard on tokenized
    names. Upstream variant suffixes (``" - Medium Grip"``, ``" - With
    Bands"``, etc.) are stripped before tokenization so e.g. local
    ``"Bench Press"`` matches upstream ``"Barbell Bench Press - Medium
    Grip"`` on its primary form.
  - Head/last token agreement boosts: +15 if last tokens agree (often
    the movement primitive like ``squat``/``press``/``curl``), +5 if
    first tokens agree.
  - Equipment compatibility bonus: +5 exact (after normalization), 0
    otherwise.
  - Primary-muscle compatibility bonus: +5 exact (after normalization),
    +2 if the upstream's primary muscle is a neighbour of the local's
    (e.g. ``shoulders`` <-> ``traps``), 0 otherwise.

The matcher deliberately favours under-matching with high confidence
over over-matching: a wrong match at score 80 is a worse review
experience than a blank row at score 40. Bonuses are small relative to
the name signal so equipment / muscle alignment cannot rescue a poor
name match.

Final score is clamped to [0, 100]. A score below ``--blank-floor``
(default 60) means "no plausible match" and the row's
``suggested_fed_id`` / ``suggested_image_path`` are emitted blank.

CSV columns (header required by apply script):

    exercise_name, suggested_fed_id, suggested_image_path, score, review_status

Coverage report (printed unless ``--quiet``):

  - whole-catalogue auto-match coverage by confidence band,
  - strength-only subset coverage (excluding Stretches / Recovery / Yoga
    / Cardio equipment categories),
  - top-N exercises by ``user_selection`` + ``workout_log`` appearance
    (the "common strength exercises" subset from PLANNING.md §4.7).

Usage::

    .venv/Scripts/python.exe scripts/map_free_exercise_db.py
    .venv/Scripts/python.exe scripts/map_free_exercise_db.py --output data/free_exercise_db_mapping.csv
    .venv/Scripts/python.exe scripts/map_free_exercise_db.py --blank-floor 30 --quiet
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.database import DatabaseHandler  # noqa: E402

DEFAULT_VENDOR_JSON = REPO_ROOT / "static" / "vendor" / "free-exercise-db" / "exercises.json"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"

CSV_HEADER: tuple[str, ...] = (
    "exercise_name",
    "suggested_fed_id",
    "suggested_image_path",
    "score",
    "review_status",
)

EQUIPMENT_NORMALIZATION: dict[str, str] = {
    "band": "bands",
    "bands": "bands",
    "barbell": "barbell",
    "trapbar": "barbell",
    "bodyweight": "body only",
    "body only": "body only",
    "stretches": "body only",
    "yoga": "body only",
    "cables": "cable",
    "cable": "cable",
    "dumbbells": "dumbbell",
    "dumbbell": "dumbbell",
    "kettlebells": "kettlebells",
    "machine": "machine",
    "smith_machine": "machine",
    "smith machine": "machine",
    "medicine_ball": "medicine ball",
    "medicine ball": "medicine ball",
    "exercise ball": "exercise ball",
    "bosu_ball": "exercise ball",
    "bosu ball": "exercise ball",
    "recovery": "foam roll",
    "foam roll": "foam roll",
    "e-z curl bar": "e-z curl bar",
    "ez curl bar": "e-z curl bar",
    "cardio": "other",
    "plate": "other",
    "trx": "other",
    "vitruvian": "other",
    "other": "other",
}

MUSCLE_NORMALIZATION: dict[str, str] = {
    "abs/core": "abdominals",
    "rectus abdominis": "abdominals",
    "external obliques": "abdominals",
    "abdominals": "abdominals",
    "back": "middle back",
    "upper back": "middle back",
    "middle back": "middle back",
    "lats": "lats",
    "latissimus dorsi": "lats",
    "lower back": "lower back",
    "biceps": "biceps",
    "triceps": "triceps",
    "forearms": "forearms",
    "shoulders": "shoulders",
    "front-shoulder": "shoulders",
    "middle-shoulder": "shoulders",
    "rear-shoulder": "shoulders",
    "chest": "chest",
    "calves": "calves",
    "quadriceps": "quadriceps",
    "hamstrings": "hamstrings",
    "gluteus maximus": "glutes",
    "glutes": "glutes",
    "hip-adductors": "adductors",
    "adductors": "adductors",
    "abductors": "abductors",
    "trapezius": "traps",
    "middle-traps": "traps",
    "upper traps": "traps",
    "traps": "traps",
    "neck": "neck",
}

MUSCLE_NEIGHBOURS: dict[str, frozenset[str]] = {
    "abdominals": frozenset({"lower back"}),
    "lats": frozenset({"middle back", "lower back"}),
    "middle back": frozenset({"lats", "lower back", "traps"}),
    "lower back": frozenset({"middle back", "abdominals"}),
    "shoulders": frozenset({"traps"}),
    "traps": frozenset({"shoulders", "middle back"}),
    "biceps": frozenset({"forearms"}),
    "triceps": frozenset({"forearms"}),
    "forearms": frozenset({"biceps", "triceps"}),
    "glutes": frozenset({"hamstrings", "quadriceps"}),
    "hamstrings": frozenset({"glutes", "calves"}),
    "quadriceps": frozenset({"glutes"}),
    "adductors": frozenset({"abductors", "glutes"}),
    "abductors": frozenset({"adductors", "glutes"}),
    "calves": frozenset({"hamstrings"}),
    "chest": frozenset({"shoulders"}),
}

NAME_NOISE_RE = re.compile(r"[\-_/,()\[\]]+")
WHITESPACE_RE = re.compile(r"\s+")
STOPWORDS: frozenset[str] = frozenset({"the", "a", "an", "and", "with", "of", "for"})


@dataclass(frozen=True)
class UpstreamEntry:
    name: str
    fed_id: str
    image_path: str
    equipment_norm: str
    muscles_norm: frozenset[str]
    tokens: tuple[str, ...]
    trigrams: frozenset[str]


@dataclass(frozen=True)
class LocalExercise:
    name: str
    equipment_raw: str
    equipment_norm: str
    muscle_norm: str
    tokens: tuple[str, ...]
    trigrams: frozenset[str]


@dataclass(frozen=True)
class MatchProposal:
    local_name: str
    fed_id: str
    image_path: str
    score: int
    review_status: str


def tokenize_name(value: str) -> tuple[str, ...]:
    """Tokenize an exercise name. Strips upstream variant suffix.

    Free-exercise-db often appends a variant after `` - ``
    (``"Barbell Bench Press - Medium Grip"``, ``"Bench Press - With
    Bands"``). The primary form is what we want to match against, so
    everything from the first `` - `` onward is dropped.
    """
    if not value:
        return ()
    primary = value.split(" - ", 1)[0]
    lowered = primary.lower()
    cleaned = NAME_NOISE_RE.sub(" ", lowered)
    return tuple(t for t in WHITESPACE_RE.split(cleaned) if t and t not in STOPWORDS)


def char_trigrams(tokens: tuple[str, ...]) -> frozenset[str]:
    joined = "".join(tokens)
    if len(joined) < 3:
        return frozenset({joined}) if joined else frozenset()
    return frozenset(joined[i:i + 3] for i in range(len(joined) - 2))


def normalize_equipment(value: str | None) -> str:
    if not value:
        return ""
    return EQUIPMENT_NORMALIZATION.get(value.strip().lower(), value.strip().lower())


def normalize_muscle(value: str | None) -> str:
    if not value:
        return ""
    return MUSCLE_NORMALIZATION.get(value.strip().lower(), value.strip().lower())


def equipment_bonus(local_eq: str, upstream_eq: str) -> int:
    if not local_eq or not upstream_eq:
        return 0
    return 5 if local_eq == upstream_eq else 0


def muscle_bonus(local_muscle: str, upstream_muscles: frozenset[str]) -> int:
    if not local_muscle or not upstream_muscles:
        return 0
    if local_muscle in upstream_muscles:
        return 5
    for upstream in upstream_muscles:
        if local_muscle in MUSCLE_NEIGHBOURS.get(upstream, frozenset()):
            return 2
        if upstream in MUSCLE_NEIGHBOURS.get(local_muscle, frozenset()):
            return 2
    return 0


def name_score(local: LocalExercise, upstream: UpstreamEntry) -> float:
    if not local.trigrams or not upstream.trigrams:
        return 0.0
    intersect = len(local.trigrams & upstream.trigrams)
    union = len(local.trigrams | upstream.trigrams)
    jaccard = intersect / union if union else 0.0
    boost = 0.0
    if local.tokens and upstream.tokens:
        if local.tokens[-1] == upstream.tokens[-1]:
            boost += 0.15
        if local.tokens[0] == upstream.tokens[0]:
            boost += 0.05
    return min(1.0, jaccard + boost) * 100.0


def score_pair(local: LocalExercise, upstream: UpstreamEntry) -> int:
    raw = name_score(local, upstream)
    raw += equipment_bonus(local.equipment_norm, upstream.equipment_norm)
    raw += muscle_bonus(local.muscle_norm, upstream.muscles_norm)
    return max(0, min(100, int(round(raw))))


def best_match(local: LocalExercise, upstream_entries: Iterable[UpstreamEntry]) -> tuple[UpstreamEntry, int] | None:
    best: tuple[UpstreamEntry, int] | None = None
    for entry in upstream_entries:
        s = score_pair(local, entry)
        if best is None or s > best[1]:
            best = (entry, s)
    return best


def load_upstream(json_path: Path) -> list[UpstreamEntry]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    entries: list[UpstreamEntry] = []
    for raw in data:
        images = raw.get("images") or []
        if not images:
            continue
        fed_id = (raw.get("id") or "").strip()
        if not fed_id:
            continue
        muscles = frozenset(normalize_muscle(m) for m in (raw.get("primaryMuscles") or []) if m)
        name = (raw.get("name") or "").strip()
        tokens = tokenize_name(name)
        entries.append(
            UpstreamEntry(
                name=name,
                fed_id=fed_id,
                image_path=str(images[0]).strip(),
                equipment_norm=normalize_equipment(raw.get("equipment")),
                muscles_norm=muscles,
                tokens=tokens,
                trigrams=char_trigrams(tokens),
            )
        )
    return entries


def load_local() -> list[LocalExercise]:
    with DatabaseHandler() as db:
        rows = db.fetch_all(
            "SELECT exercise_name, equipment, primary_muscle_group "
            "FROM exercises ORDER BY exercise_name"
        )
    locals_: list[LocalExercise] = []
    for row in rows:
        tokens = tokenize_name(row["exercise_name"])
        locals_.append(
            LocalExercise(
                name=row["exercise_name"],
                equipment_raw=(row["equipment"] or "").strip(),
                equipment_norm=normalize_equipment(row["equipment"]),
                muscle_norm=normalize_muscle(row["primary_muscle_group"]),
                tokens=tokens,
                trigrams=char_trigrams(tokens),
            )
        )
    return locals_


def propose(
    local_exercises: list[LocalExercise],
    upstream_entries: list[UpstreamEntry],
    blank_floor: int,
) -> list[MatchProposal]:
    proposals: list[MatchProposal] = []
    for local in local_exercises:
        match = best_match(local, upstream_entries)
        if match is None or match[1] < blank_floor:
            proposals.append(
                MatchProposal(
                    local_name=local.name,
                    fed_id="",
                    image_path="",
                    score=match[1] if match else 0,
                    review_status="auto",
                )
            )
            continue
        entry, score = match
        proposals.append(
            MatchProposal(
                local_name=local.name,
                fed_id=entry.fed_id,
                image_path=entry.image_path,
                score=score,
                review_status="auto",
            )
        )
    return proposals


def write_csv(proposals: Iterable[MatchProposal], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for p in proposals:
            writer.writerow([p.local_name, p.fed_id, p.image_path, p.score, p.review_status])
            count += 1
    return count


def usage_subset_names(top_n: int) -> list[str]:
    """Return the top-N exercise names by appearance in user_selection + workout_log."""
    with DatabaseHandler() as db:
        rows = db.fetch_all(
            """
            SELECT exercise, COUNT(*) AS hits FROM (
                SELECT exercise FROM user_selection
                UNION ALL
                SELECT exercise FROM workout_log
            )
            GROUP BY exercise
            ORDER BY hits DESC, exercise ASC
            LIMIT ?
            """,
            (top_n,),
        )
    return [r["exercise"] for r in rows]


def starter_plan_exercise_names() -> list[str]:
    """Return the exercises a default starter plan would select.

    Runs ``generate_starter_plan(persist=False)`` with the documented
    defaults (3 days, gym, novice, hypertrophy). No DB writes. Used by
    the coverage report's "common strength exercises" subset per
    ``docs/workout_cool_integration/PLANNING.md §4.7``.
    """
    from utils.plan_generator import generate_starter_plan  # late import: heavy
    plan = generate_starter_plan(
        training_days=3,
        environment="gym",
        experience_level="novice",
        goal="hypertrophy",
        persist=False,
    )
    names: list[str] = []
    for routine_exercises in (plan.get("routines") or {}).values():
        for entry in routine_exercises:
            n = entry.get("exercise") if isinstance(entry, dict) else None
            if n:
                names.append(n)
    return names


def confidence_band(score: int) -> str:
    if score >= 80:
        return "high (>=80)"
    if score >= 60:
        return "med (60-79)"
    if score >= 35:
        return "low (35-59)"
    return "blank (<35)"


BANDS: tuple[str, ...] = ("high (>=80)", "med (60-79)", "low (35-59)", "blank (<35)")


def _band_counts(proposals: Iterable[MatchProposal]) -> dict[str, int]:
    counts = {b: 0 for b in BANDS}
    for p in proposals:
        counts[confidence_band(p.score)] += 1
    return counts


@dataclass(frozen=True)
class SubsetReport:
    label: str
    description: str
    total: int
    matched: int
    bands: dict[str, int]


def _subset(label: str, description: str, proposals: list[MatchProposal]) -> SubsetReport:
    return SubsetReport(
        label=label,
        description=description,
        total=len(proposals),
        matched=sum(1 for p in proposals if p.image_path),
        bands=_band_counts(proposals),
    )


def _pct(n: int, total: int) -> str:
    return f"{(n * 100 / total):.1f}%" if total else "n/a"


def compute_coverage(
    proposals: list[MatchProposal],
    local_exercises: list[LocalExercise],
    usage_top_n: int,
    starter_names: list[str] | None,
) -> list[SubsetReport]:
    name_to_proposal = {p.local_name: p for p in proposals}

    reports: list[SubsetReport] = []
    reports.append(_subset("Whole catalogue", "all rows in `exercises`", proposals))

    strength_exclude = {"Stretches", "Yoga", "Recovery", "Cardio"}
    strength_props = [
        proposals[i] for i, local in enumerate(local_exercises)
        if local.equipment_raw not in strength_exclude
    ]
    reports.append(_subset(
        "Strength subset",
        "excludes equipment in {Stretches, Yoga, Recovery, Cardio}",
        strength_props,
    ))

    usage_names = usage_subset_names(usage_top_n)
    usage_props = [name_to_proposal[n] for n in usage_names if n in name_to_proposal]
    reports.append(_subset(
        f"Usage top-{usage_top_n}",
        "top by appearance count in `user_selection` + `workout_log`",
        usage_props,
    ))

    if starter_names is not None:
        starter_unique = list(dict.fromkeys(starter_names))
        starter_props = [name_to_proposal[n] for n in starter_unique if n in name_to_proposal]
        reports.append(_subset(
            "Starter plan (default args)",
            "exercises chosen by `generate_starter_plan(persist=False)` with defaults (3 days, gym, novice, hypertrophy)",
            starter_props,
        ))

        common_names = list(dict.fromkeys(list(usage_names) + starter_unique))
        common_props = [name_to_proposal[n] for n in common_names if n in name_to_proposal]
        reports.append(_subset(
            "Common strength (usage + starter)",
            "PLANNING §4.7 candidate: top-N usage UNION default starter-plan exercises",
            common_props,
        ))

    return reports


def render_coverage_text(reports: list[SubsetReport], blank_floor: int) -> str:
    out: list[str] = []
    for r in reports:
        out.append("=" * 60)
        out.append(f"{r.label.upper()}  ({r.description})")
        out.append("=" * 60)
        out.append(f"  size:                  {r.total}")
        if r.total:
            out.append(f"  matched (score >= {blank_floor}):  {r.matched} / {r.total}  ({_pct(r.matched, r.total)})")
            for band in BANDS:
                n = r.bands.get(band, 0)
                out.append(f"    {band:<14}  {n:>5}  ({_pct(n, r.total)})")
        out.append("")
    return "\n".join(out)


def render_coverage_markdown(reports: list[SubsetReport], blank_floor: int) -> str:
    lines: list[str] = ["# free-exercise-db mapping coverage", ""]
    lines.append(f"`blank_floor = {blank_floor}` (scores below this emit blank `suggested_fed_id` / `suggested_image_path`).")
    lines.append("")
    lines.append("| Subset | Size | Matched | High ≥80 | Med 60–79 | Low 35–59 | Blank <35 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in reports:
        if not r.total:
            lines.append(f"| {r.label} | 0 | — | — | — | — | — |")
            continue
        h = r.bands.get("high (>=80)", 0)
        m = r.bands.get("med (60-79)", 0)
        l = r.bands.get("low (35-59)", 0)
        b = r.bands.get("blank (<35)", 0)
        lines.append(
            f"| {r.label} | {r.total} | {r.matched} ({_pct(r.matched, r.total)}) | "
            f"{h} ({_pct(h, r.total)}) | {m} ({_pct(m, r.total)}) | "
            f"{l} ({_pct(l, r.total)}) | {b} ({_pct(b, r.total)}) |"
        )
    lines.append("")
    lines.append("## Subset definitions")
    lines.append("")
    for r in reports:
        lines.append(f"- **{r.label}** — {r.description}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate free-exercise-db mapping proposals.")
    parser.add_argument("--vendor-json", type=Path, default=DEFAULT_VENDOR_JSON,
                        help="Path to vendored exercises.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_CSV,
                        help="Output CSV path")
    parser.add_argument("--blank-floor", type=int, default=60,
                        help="Scores below this emit blank fed_id/image_path (default 60)")
    parser.add_argument("--usage-top-n", type=int, default=200,
                        help="Top-N exercises for the usage-subset coverage report (default 200)")
    parser.add_argument("--coverage-md", type=Path, default=None,
                        help="Optional path to write the coverage report as markdown")
    parser.add_argument("--include-starter-plan", action="store_true",
                        help="Run a default starter plan (persist=False) and include its exercises in the coverage subset")
    parser.add_argument("--quiet", action="store_true", help="Skip coverage report output")
    args = parser.parse_args(argv)

    if not args.vendor_json.exists():
        print(f"ERROR: vendor JSON not found: {args.vendor_json}", file=sys.stderr)
        return 2

    upstream_entries = load_upstream(args.vendor_json)
    local_exercises = load_local()
    proposals = propose(local_exercises, upstream_entries, args.blank_floor)
    count = write_csv(proposals, args.output)

    print(f"wrote {count} rows to {args.output}")

    starter_names: list[str] | None = None
    if args.include_starter_plan:
        starter_names = starter_plan_exercise_names()

    reports = compute_coverage(proposals, local_exercises, args.usage_top_n, starter_names)

    if not args.quiet:
        print()
        print(render_coverage_text(reports, args.blank_floor))

    if args.coverage_md is not None:
        args.coverage_md.parent.mkdir(parents=True, exist_ok=True)
        args.coverage_md.write_text(render_coverage_markdown(reports, args.blank_floor), encoding="utf-8")
        print(f"wrote coverage markdown to {args.coverage_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
