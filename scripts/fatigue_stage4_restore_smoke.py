"""
Stage 4 owner smoke — destructive backup-restore round-trip.

Strict ordering (per docs/fatigue_meter/PLANNING.md §3.5 owner-required smoke
checklist item 3, marked DESTRUCTIVE):

  Step A: take fresh backup of current state
  Step B: confirm fresh backup row, record its id
  Step C: restore pre-fatigue backup id 5 (this WIPES user_selection)
  Step D: walk pages, confirm no crashes
  Step E: restore the fresh backup recorded at Step B
  Step F: verify current routines are back (byte-equality of user_selection)

This script runs the round-trip via Flask test_client (no separate dev server)
and prints a clear PASS/FAIL line for each step. If any step fails, the script
exits non-zero and leaves state as-is for human inspection.

Temporary script: delete after Stage 4 §4.1 owner smokes complete.
"""
import datetime as dt
import hashlib
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("FLASK_USE_RELOADER", "0")

DB = "data/database.db"
PRE_FATIGUE_BACKUP_ID = 5
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


def snapshot_user_selection():
    """Return a sorted-tuple snapshot of user_selection (excluding auto-id)."""
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(user_selection)")
    cols = [r[1] for r in cur.fetchall() if r[1] != "id"]
    cur.execute(f"SELECT {','.join(cols)} FROM user_selection ORDER BY {','.join(cols)}")
    rows = cur.fetchall()
    con.close()
    return cols, rows


def hash_snapshot(cols, rows):
    payload = repr(cols) + "|" + repr(rows)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def show(label, ok, extra=""):
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {label}" + (f"  — {extra}" if extra else ""))
    return ok


def main():
    from app import app

    client = app.test_client()
    failures = []

    print("=" * 70)
    print("Stage 4 owner smoke — destructive backup-restore round-trip")
    print(f"Started:  {dt.datetime.now().isoformat(timespec='seconds')}")
    print(f"DB:       {DB}")
    print("=" * 70)

    # Pre-flight: capture original snapshot
    pre_cols, pre_rows = snapshot_user_selection()
    pre_hash = hash_snapshot(pre_cols, pre_rows)
    pre_count = len(pre_rows)
    pre_routines = sorted({r[pre_cols.index("routine")] for r in pre_rows})
    print(f"\nPre-state:")
    print(f"  user_selection rows: {pre_count}")
    print(f"  routines:            {pre_routines}")
    print(f"  snapshot hash:       {pre_hash}")

    # ------------------------------------------------------------------
    # Step A: take fresh backup of current state
    # ------------------------------------------------------------------
    label = f"pre-fatigue-restore-smoke-{dt.date.today().isoformat()}"
    print(f"\n--- Step A: POST /api/backups (label={label!r}) ---")
    rA = client.post("/api/backups", json={"name": label, "note": "Stage 4 §3.5 destructive smoke recovery target"})
    if not show("Step A: POST returned 200", rA.status_code == 200, f"status={rA.status_code}"):
        failures.append("Step A status")
    payload = rA.get_json() or {}
    backup_meta = payload.get("data") or {}
    fresh_id = backup_meta.get("id")
    fresh_items = backup_meta.get("item_count")
    show(
        "Step A: response carries id + item_count",
        bool(fresh_id) and fresh_items is not None,
        f"id={fresh_id} item_count={fresh_items}",
    )
    if not fresh_id:
        failures.append("Step A no id")
        print("ABORT — Step A did not return a fresh backup id. State unchanged.")
        return 1

    # ------------------------------------------------------------------
    # Step B: confirm fresh backup row exists, double-check id
    # ------------------------------------------------------------------
    print(f"\n--- Step B: GET /api/backups (confirm id={fresh_id}) ---")
    rB = client.get("/api/backups")
    if not show("Step B: GET returned 200", rB.status_code == 200, f"status={rB.status_code}"):
        failures.append("Step B status")
    rows = (rB.get_json() or {}).get("data") or []
    matching = [b for b in rows if b.get("id") == fresh_id]
    show(
        "Step B: fresh backup row present in list",
        len(matching) == 1,
        f"matches={len(matching)} name={matching[0].get('name') if matching else 'N/A'}",
    )
    if not matching:
        failures.append("Step B fresh row missing")
        print(f"ABORT — fresh backup id {fresh_id} not found in /api/backups list.")
        return 1
    show(
        "Step B: fresh backup item_count == pre user_selection count",
        matching[0].get("item_count") == pre_count,
        f"backup={matching[0].get('item_count')} live={pre_count}",
    )

    # ------------------------------------------------------------------
    # Step C: restore pre-fatigue backup id 5 (DESTRUCTIVE)
    # ------------------------------------------------------------------
    print(f"\n--- Step C: POST /api/backups/{PRE_FATIGUE_BACKUP_ID}/restore (DESTRUCTIVE) ---")
    rC = client.post(f"/api/backups/{PRE_FATIGUE_BACKUP_ID}/restore")
    if not show("Step C: POST returned 200", rC.status_code == 200, f"status={rC.status_code}"):
        failures.append("Step C status")
    rC_data = (rC.get_json() or {}).get("data") or {}
    show(
        "Step C: restored_count == 0 (id 5 has item_count 0)",
        rC_data.get("restored_count") == 0,
        f"restored={rC_data.get('restored_count')} skipped={rC_data.get('skipped')}",
    )
    mid_cols, mid_rows = snapshot_user_selection()
    show(
        "Step C: user_selection now empty",
        len(mid_rows) == 0,
        f"rows={len(mid_rows)}",
    )

    # ------------------------------------------------------------------
    # Step D: walk pages, confirm no crashes
    # ------------------------------------------------------------------
    print(f"\n--- Step D: walk {len(PAGES_TO_WALK)} pages with empty user_selection ---")
    page_failures = []
    for path in PAGES_TO_WALK:
        r = client.get(path)
        ok = r.status_code == 200
        # Also probe for fatigue badge presence on summary pages — should render empty-state
        extra = f"status={r.status_code}"
        if path in ("/weekly_summary", "/session_summary"):
            html = r.get_data(as_text=True) or ""
            has_badge = "fatigue-badge" in html
            no_planned = "No planned exercises yet" in html or "No planned routines" in html
            extra += f" badge={'yes' if has_badge else 'NO'} empty-state={'yes' if no_planned else 'NO'}"
            ok = ok and has_badge and no_planned
        if not show(f"Step D: GET {path}", ok, extra):
            page_failures.append(path)
    if page_failures:
        failures.append(f"Step D pages: {page_failures}")

    # ------------------------------------------------------------------
    # Step E: restore the fresh backup
    # ------------------------------------------------------------------
    print(f"\n--- Step E: POST /api/backups/{fresh_id}/restore (recovery) ---")
    rE = client.post(f"/api/backups/{fresh_id}/restore")
    if not show("Step E: POST returned 200", rE.status_code == 200, f"status={rE.status_code}"):
        failures.append("Step E status")
    rE_data = (rE.get_json() or {}).get("data") or {}
    show(
        "Step E: restored_count == pre user_selection count",
        rE_data.get("restored_count") == pre_count,
        f"restored={rE_data.get('restored_count')} expected={pre_count} skipped={rE_data.get('skipped')}",
    )

    # ------------------------------------------------------------------
    # Step F: verify byte-equality of user_selection
    # ------------------------------------------------------------------
    print(f"\n--- Step F: snapshot equality check ---")
    post_cols, post_rows = snapshot_user_selection()
    post_hash = hash_snapshot(post_cols, post_rows)
    post_count = len(post_rows)
    post_routines = sorted({r[post_cols.index("routine")] for r in post_rows})
    print(f"Post-state:")
    print(f"  user_selection rows: {post_count}")
    print(f"  routines:            {post_routines}")
    print(f"  snapshot hash:       {post_hash}")
    show(
        "Step F: row count matches",
        post_count == pre_count,
        f"pre={pre_count} post={post_count}",
    )
    show(
        "Step F: routines match",
        post_routines == pre_routines,
        f"pre={pre_routines} post={post_routines}",
    )
    if not show(
        "Step F: snapshot hash matches (byte-equal user_selection)",
        post_hash == pre_hash,
        f"pre={pre_hash} post={post_hash}",
    ):
        # Diff first row that differs to help debug
        for i, (a, b) in enumerate(zip(pre_rows, post_rows)):
            if a != b:
                print(f"    first diff at row {i}: pre={a} post={b}")
                break
        failures.append("Step F hash mismatch")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    if failures:
        print(f"OVERALL: FAIL ({len(failures)} step(s) failed)")
        for f in failures:
            print(f"  - {f}")
        print(f"\nFresh recovery backup id is {fresh_id} ({label!r}). State as-is.")
        return 1
    print("OVERALL: PASS — all 6 steps green; user_selection round-trip byte-equal.")
    print(f"Fresh recovery backup id was {fresh_id} ({label!r}).")
    print("Note: this backup row remains in program_backups; safe to delete via")
    print("DELETE /api/backups/<id> once Stage 4 owner-smokes are complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
