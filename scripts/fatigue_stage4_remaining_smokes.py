"""
Stage 4 owner smokes — remaining items after the destructive restore round-trip.

Walks the §3.5 owner-required smoke checklist items 1, 2, 6 against the
populated state (24 exercises, routines A-D) using Flask test_client. Items
4 and 5 (375px viewport, dark-mode contrast) are browser-only and are
documented but not exercised.

Checks:
  1. Navbar HTTP-200 sweep (re-runs Step D's page walk, populated state)
  2. Badge coherence: rendered fatigue score == utils.fatigue_data score
  3. D3 invariance under populated state: ?counting_mode=raw vs ?counting_mode=effective
     produce byte-identical fatigue badge HTML

Temporary script: delete after Stage 4 §4.1 owner smokes complete.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("FLASK_USE_RELOADER", "0")


PAGES_TO_WALK = [
    "/",
    "/workout_plan",
    "/workout_log",
    "/weekly_summary",
    "/session_summary",
    "/progression",
    "/volume_splitter",
    "/user_profile",
    "/backup",
]


def show(label, ok, extra=""):
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {label}" + (f"  — {extra}" if extra else ""))
    return ok


def _attr(html: str, cls: str) -> str:
    m = re.search(
        rf'class="{cls}[^"]*"[^>]*>\s*(.*?)\s*</div>',
        html,
        flags=re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def extract_card_class(html: str) -> str:
    m = re.search(r'<div class="card fatigue-badge ([^"]*)"', html)
    return m.group(1).strip() if m else ""


def extract_fatigue_block(html: str) -> str:
    """Extract the full fatigue-badge card from <div class="card fatigue-badge..."
    through its matching closing </div> by counting div tags."""
    start = html.find('<div class="card fatigue-badge')
    if start < 0:
        return ""
    depth = 0
    i = start
    while i < len(html):
        m = re.search(r'<(/?)div\b', html[i:])
        if not m:
            return ""
        i += m.start()
        if m.group(1) == "/":
            depth -= 1
            i += len("</div>")
            if depth == 0:
                return html[start:i]
        else:
            depth += 1
            close = html.find(">", i)
            if close < 0:
                return ""
            i = close + 1
    return ""


def extract_score(html: str) -> str:
    """Pull the visible numeric score (or empty-state marker) out of the badge HTML."""
    block = extract_fatigue_block(html)
    if not block:
        return "UNKNOWN"
    score_text = _attr(block, "fatigue-badge__score")
    if not score_text:
        return "UNKNOWN"
    if score_text.isdigit():
        return score_text
    if "No planned exercises yet" in block or "No planned routines" in block:
        return "EMPTY"
    if score_text in ("—", "—"):
        return "EMPTY"
    return score_text


def main():
    from app import app
    from utils.fatigue_data import (
        compute_heaviest_session_fatigue,
        compute_session_fatigue_for_routine,
        compute_weekly_fatigue,
    )

    client = app.test_client()
    failures = []

    print("=" * 70)
    print("Stage 4 owner smokes — remaining items (populated state)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Navbar HTTP-200 sweep (populated state)
    # ------------------------------------------------------------------
    print("\n--- 1. Navbar HTTP-200 sweep (populated state) ---")
    for path in PAGES_TO_WALK:
        r = client.get(path)
        ok = r.status_code == 200
        extra = f"status={r.status_code}"
        if path in ("/weekly_summary", "/session_summary"):
            html = r.get_data(as_text=True) or ""
            block = extract_fatigue_block(html)
            score = extract_score(html)
            extra += f" badge={'yes' if block else 'NO'} score={score}"
            ok = ok and bool(block)
        if not show(f"GET {path}", ok, extra):
            failures.append(f"page {path}")

    # ------------------------------------------------------------------
    # 2. Badge coherence: rendered score == compute_*_fatigue() score
    # ------------------------------------------------------------------
    print("\n--- 2. Badge coherence (rendered HTML vs utils.fatigue_data) ---")
    weekly = compute_weekly_fatigue()
    weekly_expected = round(weekly.score)
    weekly_html = client.get("/weekly_summary").get_data(as_text=True) or ""
    weekly_rendered = extract_score(weekly_html)
    show(
        "weekly_summary: rendered score == compute_weekly_fatigue().score (rounded)",
        weekly_rendered == str(weekly_expected),
        f"rendered={weekly_rendered} expected={weekly_expected} (band={weekly.band})",
    )
    if weekly_rendered != str(weekly_expected):
        failures.append("weekly badge coherence")

    heaviest_routine, heaviest = compute_heaviest_session_fatigue()
    heaviest_expected = round(heaviest.score)
    session_html = client.get("/session_summary").get_data(as_text=True) or ""
    session_rendered = extract_score(session_html)
    show(
        "session_summary (no routine filter): rendered score == compute_heaviest_session_fatigue().score (rounded)",
        session_rendered == str(heaviest_expected),
        f"rendered={session_rendered} expected={heaviest_expected} routine={heaviest_routine!r} (band={heaviest.band})",
    )
    if session_rendered != str(heaviest_expected):
        failures.append("session no-filter badge coherence")

    # Per-routine: pick first known routine
    routine = "A"
    routine_session = compute_session_fatigue_for_routine(routine)
    routine_expected = round(routine_session.score)
    routine_html = client.get(f"/session_summary?routine={routine}").get_data(as_text=True) or ""
    routine_rendered = extract_score(routine_html)
    show(
        f"session_summary?routine={routine}: rendered score == compute_session_fatigue_for_routine({routine!r}).score",
        routine_rendered == str(routine_expected),
        f"rendered={routine_rendered} expected={routine_expected} (band={routine_session.band})",
    )
    if routine_rendered != str(routine_expected):
        failures.append(f"session routine={routine} badge coherence")

    # ------------------------------------------------------------------
    # 3. D3 invariance: counting_mode=raw vs counting_mode=effective
    # ------------------------------------------------------------------
    print("\n--- 3. D3 invariance: counting_mode raw vs effective ---")
    for path_base in ("/weekly_summary", "/session_summary"):
        raw_html = client.get(f"{path_base}?counting_mode=raw").get_data(as_text=True) or ""
        eff_html = client.get(f"{path_base}?counting_mode=effective").get_data(as_text=True) or ""
        raw_block = extract_fatigue_block(raw_html)
        eff_block = extract_fatigue_block(eff_html)
        ok = bool(raw_block) and raw_block == eff_block
        show(
            f"{path_base}: badge byte-identical across counting_mode raw vs effective",
            ok,
            f"raw_score={extract_score(raw_html)} effective_score={extract_score(eff_html)}",
        )
        if not ok:
            failures.append(f"D3 invariance {path_base}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    if failures:
        print(f"OVERALL: FAIL ({len(failures)} check(s) failed)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OVERALL: PASS — all populated-state smokes green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
