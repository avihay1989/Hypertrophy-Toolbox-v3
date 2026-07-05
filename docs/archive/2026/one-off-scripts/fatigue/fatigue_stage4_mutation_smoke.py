"""
Stage 4 owner smoke item 2 — badge updates when user_selection mutates.

Add an exercise to routine A, observe the fatigue badge change, remove the
exercise, observe the badge return to the original value. Verifies:

  - The badge is *not* statically cached or hardcoded.
  - It reads `user_selection` live (D10).
  - Adding/removing planned volume moves the projected score.

This complements the badge-coherence check (rendered == computed) by
exercising the data-flow path end-to-end.

Temporary script: delete after Stage 4 §4.1 owner smokes complete.
"""
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("FLASK_USE_RELOADER", "0")

DB = "data/database.db"
ROUTINE = "A"
CANDIDATE_EXERCISE = "Abductor Leg Raise Side Lying"  # not in user_selection, has movement_pattern


def show(label, ok, extra=""):
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {label}" + (f"  — {extra}" if extra else ""))
    return ok


def extract_score(html: str) -> str:
    m = re.search(
        r'class="fatigue-badge__score[^"]*"[^>]*>\s*(.*?)\s*</div>',
        html,
        flags=re.DOTALL,
    )
    if not m:
        return "UNKNOWN"
    text = m.group(1).strip()
    return text if text.isdigit() else "EMPTY"


def snapshot_user_selection_count():
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM user_selection").fetchone()[0]
    con.close()
    return n


def main():
    from app import app

    client = app.test_client()
    failures = []

    print("=" * 70)
    print("Stage 4 owner smoke item 2 — mutation roundtrip")
    print("=" * 70)

    pre_count = snapshot_user_selection_count()
    pre_html = client.get("/weekly_summary").get_data(as_text=True) or ""
    pre_score_str = extract_score(pre_html)

    routine_a_pre_html = client.get(f"/session_summary?routine={ROUTINE}").get_data(as_text=True) or ""
    routine_a_pre_score_str = extract_score(routine_a_pre_html)

    print(f"\nPre-state:")
    print(f"  user_selection rows: {pre_count}")
    print(f"  weekly badge score:  {pre_score_str}")
    print(f"  routine {ROUTINE} badge score: {routine_a_pre_score_str}")

    # ------------------------------------------------------------------
    # Step 1: add the candidate exercise to routine A
    # ------------------------------------------------------------------
    print(f"\n--- Step 1: POST /add_exercise (routine={ROUTINE}, exercise={CANDIDATE_EXERCISE!r}) ---")
    add_payload = {
        "routine": ROUTINE,
        "exercise": CANDIDATE_EXERCISE,
        "sets": 4,
        "min_rep_range": 8,
        "max_rep_range": 12,
        "rir": 2,
        "weight": 1,  # min positive — exercise_manager validates `not all([..., weight])`
    }
    rA = client.post("/add_exercise", json=add_payload)
    show("Step 1: POST returned 200", rA.status_code == 200, f"status={rA.status_code} body={rA.get_data(as_text=True)[:200]}")
    if rA.status_code != 200:
        failures.append("Step 1 status")
        print("ABORT — could not add the candidate. State unchanged.")
        return 1

    mid_count = snapshot_user_selection_count()
    show("Step 1: user_selection row count incremented by 1", mid_count == pre_count + 1, f"{pre_count} -> {mid_count}")

    # Look up the new row's id (the most-recently-inserted matching exercise)
    con = sqlite3.connect(DB)
    new_id_row = con.execute(
        "SELECT MAX(id) FROM user_selection WHERE routine = ? AND exercise = ?",
        (ROUTINE, CANDIDATE_EXERCISE),
    ).fetchone()
    con.close()
    new_id = new_id_row[0] if new_id_row else None
    show("Step 1: new user_selection row id captured", bool(new_id), f"id={new_id}")
    if not new_id:
        failures.append("Step 1 could not capture new id; aborting")
        print("ABORT — new id missing. Cleanup will need manual intervention.")
        return 1

    # ------------------------------------------------------------------
    # Step 2: re-render summary pages, verify scores moved
    # ------------------------------------------------------------------
    print(f"\n--- Step 2: re-render summary pages, expect scores to differ from baseline ---")
    mid_weekly_html = client.get("/weekly_summary").get_data(as_text=True) or ""
    mid_weekly_score = extract_score(mid_weekly_html)
    show(
        "Step 2: weekly badge score changed",
        mid_weekly_score != pre_score_str,
        f"pre={pre_score_str} mid={mid_weekly_score}",
    )
    if mid_weekly_score == pre_score_str:
        failures.append("Step 2 weekly score did not change")

    mid_routine_html = client.get(f"/session_summary?routine={ROUTINE}").get_data(as_text=True) or ""
    mid_routine_score = extract_score(mid_routine_html)
    show(
        f"Step 2: routine {ROUTINE} badge score changed",
        mid_routine_score != routine_a_pre_score_str,
        f"pre={routine_a_pre_score_str} mid={mid_routine_score}",
    )
    if mid_routine_score == routine_a_pre_score_str:
        failures.append(f"Step 2 routine {ROUTINE} score did not change")

    # ------------------------------------------------------------------
    # Step 3: remove the added exercise (cleanup)
    # ------------------------------------------------------------------
    print(f"\n--- Step 3: POST /remove_exercise (id={new_id}) ---")
    rR = client.post("/remove_exercise", json={"id": new_id})
    show("Step 3: POST returned 200", rR.status_code == 200, f"status={rR.status_code}")
    if rR.status_code != 200:
        failures.append("Step 3 status")
        print(f"WARNING — removal failed. The added row id={new_id} is still in user_selection.")
        return 1

    post_count = snapshot_user_selection_count()
    show("Step 3: user_selection row count back to baseline", post_count == pre_count, f"baseline={pre_count} now={post_count}")

    # ------------------------------------------------------------------
    # Step 4: scores must return exactly to pre-state
    # ------------------------------------------------------------------
    print(f"\n--- Step 4: scores must return to baseline ---")
    post_weekly_html = client.get("/weekly_summary").get_data(as_text=True) or ""
    post_weekly_score = extract_score(post_weekly_html)
    show(
        "Step 4: weekly badge score back to baseline",
        post_weekly_score == pre_score_str,
        f"pre={pre_score_str} post={post_weekly_score}",
    )
    if post_weekly_score != pre_score_str:
        failures.append("Step 4 weekly did not return to baseline")

    post_routine_html = client.get(f"/session_summary?routine={ROUTINE}").get_data(as_text=True) or ""
    post_routine_score = extract_score(post_routine_html)
    show(
        f"Step 4: routine {ROUTINE} badge score back to baseline",
        post_routine_score == routine_a_pre_score_str,
        f"pre={routine_a_pre_score_str} post={post_routine_score}",
    )
    if post_routine_score != routine_a_pre_score_str:
        failures.append(f"Step 4 routine {ROUTINE} did not return to baseline")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    if failures:
        print(f"OVERALL: FAIL ({len(failures)} check(s) failed)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OVERALL: PASS — badge mutates with user_selection and returns to baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
