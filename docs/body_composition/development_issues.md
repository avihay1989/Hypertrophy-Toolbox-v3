# Development Issues — Body Composition Feature

This tracker covers the standalone `/body_composition` tab: tape-measurement
inputs, BFP estimation (U.S. Navy + BMI methods), and longitudinal snapshot
tracking.

## Background

This feature was originally specced as a section on the Profile page and
tracked as **Issue #21** in
[`docs/user_profile/development_issues.md`](../user_profile/development_issues.md).
On **2026-04-28** the scope changed: it was promoted to a standalone tab
(see the scope-change note inside the issue body) and moved to its own
docs folder. Issue numbering is preserved (so the issue keeps the same
identifier across the codebase, search history, and cross-references in
the Profile-page tracker — Issues #17 / #18 / #19 referenced inside the
issue body still point to that same parent doc).

Profile-page display hooks (Issue #18 bodyweight-tile *Lean mass* sub-line
and Issue #17 *"Body fat: X % · {ACE band}"* sub-line) are intentionally
deferred to a separate cross-page-display follow-up once `/body_composition`
has shipped and snapshots are routinely captured.

---

## Issue #21 — Body Composition tab: tape-measurement inputs, BFP estimation, and longitudinal tracking

**Severity:** 🟢 Enhancement — Large (new sub-feature, standalone tab)
**Area:** new template `templates/body_composition.html`,
new blueprint `routes/body_composition.py`,
new module `utils/body_fat.py`,
new bundle `static/js/modules/body-composition.js`,
new stylesheet `static/css/pages-body-composition.css`,
`utils/database.py` (new table),
`app.py` (register blueprint + run migration on startup),
`templates/base.html` + `static/js/modules/navbar.js` (navbar entry +
active-state pathMap),
new tests `tests/test_body_fat.py` + `tests/test_body_composition_routes.py`,
new spec `e2e/body-composition.spec.ts`.

> **Scope change (2026-04-28):** This feature was originally specced as
> a section on the Profile page. Reviewed and moved to a standalone
> `/body_composition` tab because (a) the design is already decoupled
> from the estimator math — the acceptance checklist explicitly
> requires byte-identical estimator outputs before / after; (b) the
> longitudinal snapshot history + trend chart deserve their own
> viewport without crowding the strength-focused Profile page; and
> (c) all three Profile-page coupling points (Issue #18 cohort tile
> sub-line, Issue #17 transparency-card sub-line, and consumption
> helpers in `utils/profile_estimator.py`) are display-only and have
> been deferred to a follow-up issue without losing any estimator
> coverage. The body-fat module stays available as a read-only
> reference for any future estimator consumer; the consumer just lives
> on a different page.

Add a Body Composition tab at `/body_composition` that accepts tape
measurements, computes Body Fat Percentage (BFP) via the **U.S. Navy
circumference method** (primary) and the **BMI method** (secondary, no
tape required), and saves snapshots over time for progress tracking.
The tab reads `gender` / `age` / `height` / `bodyweight` from the
existing user-profile row (no re-entry) but otherwise lives independently
of `/user_profile`. The latest BFP / Lean Mass / Fat Mass are persisted
to a new table and exposed to any future estimator consumer as
**read-only context** (no automatic adjustment to weight suggestions —
informational only, consistent with the `utils/effective_sets.py:6-7`
invariant). Surfacing those fields back on the Profile page (Issue #17 /
#18 hooks) is out of scope here and is deferred to a follow-up.

Conceptually this is the third lens on *"how the system sees you"*
started in Issue #17, but it is intentionally NOT colocated:

- Issue #17 — *what data drives each suggestion* (transparency,
  Profile page).
- Issues #18–19 — *what the system already knows about you* (visual
  stats + bodymap coverage, Profile page).
- **Issue #21** — *what your body composition actually is* (measured,
  saved, and trended over time, **standalone `/body_composition`
  tab**).

Keeping body composition on its own page protects the Profile page
from feature creep and matches how the rest of the app is organised
(one workflow per top-nav tab).

---

### Inputs (metric units only — single-region scope, simpler UX)

| Field        | Unit | Required             | Notes                                                                                  |
|--------------|------|----------------------|----------------------------------------------------------------------------------------|
| `gender`     | M/F  | Yes (already in profile) | Reused from existing Demographics; not re-entered.                                  |
| `age`        | yrs  | Yes (already in profile) | Reused from Demographics. Required for BMI method + Jackson & Pollock comparison.   |
| `bodyweight` | kg   | Yes (already in profile) | Reused. Required for FM / LM derivation.                                            |
| `height`     | cm   | Yes (already in profile) | Reused. Required for both formulas.                                                 |
| `neck`       | cm   | Yes (new)            | Measured below the larynx, tape sloping downward to the front; subject does not flare. |
| `waist`      | cm   | Yes (new)            | Men: horizontal at navel. Women: at the smallest natural width. Subject does not pull stomach in. |
| `hip`        | cm   | **Female only** (new)| Largest horizontal hip circumference. Hidden / disabled when `gender == M`.            |

Imperial input toggle is **out of scope** for v1 — keep the form
metric-only to match every other measurement in the app.
The original Hodgdon & Beckett SI-units formula is the only one we ship.

---

### Formulas

#### U.S. Navy method (primary)

Source: Hodgdon & Beckett, Naval Health Research Center (1984).
The metric (SI) form is the only variant we implement.

**Male:**

```
BFP = 495 / (1.0324 - 0.19077 * log10(waist - neck) + 0.15456 * log10(height)) - 450
```

**Female:**

```
BFP = 495 / (1.29579 - 0.35004 * log10(waist + hip - neck) + 0.22100 * log10(height)) - 450
```

**Derived metrics:**

```
fat_mass_kg  = (BFP / 100) * bodyweight
lean_mass_kg = bodyweight - fat_mass_kg
```

**Input validation (server-side, in `utils/body_fat.py`):**

- `(waist - neck) > 0` for males (otherwise `log10` is undefined).
- `(waist + hip - neck) > 0` for females.
- All circumferences in `[20, 250]` cm; height in `[100, 250]` cm;
  bodyweight in `[20, 350]` kg.
- Out-of-range / log-domain violations return a structured error and
  the form surfaces the matching tape-measurement guidance (e.g.
  *"Waist circumference must be larger than neck circumference."*).

#### BMI method (secondary, when tape values are blank)

```
BMI = bodyweight_kg / (height_m ^ 2)

Adult male:    BFP = 1.20 * BMI + 0.23 * age - 16.2
Adult female:  BFP = 1.20 * BMI + 0.23 * age - 5.4
Boy (<18):     BFP = 1.51 * BMI - 0.70 * age - 2.2
Girl (<18):    BFP = 1.51 * BMI - 0.70 * age + 1.4
```

**Use:** the BMI form runs whenever Demographics are filled but the
tape inputs are blank. It is shown as a **fallback estimate** with an
explicit *"BMI-based — less accurate than Navy method"* badge so the
user understands the trade-off. Single source of truth: both formulas
live in `utils/body_fat.py`; the JS mirror has the explicit
*"must match Python"* comment, same contract as Issue #17.

---

### Reference categorisations (display only — not gates)

#### ACE Body Fat Categorization

| Description     | Women     | Men       |
|-----------------|-----------|-----------|
| Essential fat   | 10–13 %   | 2–5 %     |
| Athletes        | 14–20 %   | 6–13 %    |
| Fitness         | 21–24 %   | 14–17 %   |
| Average         | 25–31 %   | 18–24 %   |
| Obese           | 32 % +    | 25 % +    |

Render as a horizontal segmented band, with the user's current BFP marked
as a vertical tick. Tooltip on the band cites the source ("American
Council on Exercise"). The band is **informational** — the app **never**
labels the user with a category in copy ("you are obese" is out of
scope); it simply shows where the number lands on the band, and the user
draws their own conclusion. This stays consistent with the Issue #18
*"informational, never prescriptive"* rule.

#### Jackson & Pollock ideal BFP by age

| Age | Women   | Men     |
|-----|---------|---------|
| 20  | 17.7 %  | 8.5 %   |
| 25  | 18.4 %  | 10.5 %  |
| 30  | 19.3 %  | 12.7 %  |
| 35  | 21.5 %  | 13.7 %  |
| 40  | 22.2 %  | 15.3 %  |
| 45  | 22.9 %  | 16.4 %  |
| 50  | 25.2 %  | 18.9 %  |
| 55  | 26.3 %  | 20.9 %  |

For the user's age, **linearly interpolate** between the two bracketing
rows (clamp to the table edges for ages outside 20–55). Render as a
single comparison line:

> *"Jackson & Pollock ideal for your age (34, M): **13.5 %**.
> Your current estimate: **18.2 %**."*

Again — informational. No "you should aim for X" copy; the user reads
the comparison and decides for themselves.

---

### Persistence: longitudinal snapshots

A new table `body_composition_snapshots` (renamed from the original
`user_profile_body_fat_snapshots` to match the standalone tab):

```sql
CREATE TABLE body_composition_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at     TEXT    NOT NULL,            -- ISO 8601 UTC
    bodyweight_kg   REAL    NOT NULL,
    height_cm       REAL    NOT NULL,
    neck_cm         REAL,                        -- nullable: BMI-only snapshot
    waist_cm        REAL,
    hip_cm          REAL,
    age_years       INTEGER NOT NULL,
    gender          TEXT    NOT NULL,            -- 'M' | 'F'
    bfp_navy        REAL,                        -- nullable when tape blank
    bfp_bmi         REAL    NOT NULL,            -- always computable from demographics
    fat_mass_kg     REAL,                        -- derived from bfp_navy when present, else bfp_bmi
    lean_mass_kg    REAL,
    notes           TEXT
);

CREATE INDEX idx_body_composition_snapshots_captured_at
    ON body_composition_snapshots(captured_at DESC);
```

**Migration:** added by a new
`add_body_composition_snapshots_table()` migration in
`utils/database.py`, registered in `app.py` startup sequence next to
`add_user_profile_tables()`. Follow the same pattern documented in
[`.claude/rules/database.md`](../../.claude/rules/database.md).

**No retention cap** in v1 — single user, local DB, no compliance
constraints. The user can manually delete snapshots from the UI.

---

### UI

A new top-level page at `/body_composition` rendered as a standalone
template (`templates/body_composition.html` extending `base.html`),
with a `frame-calm-glass [data-section="body fat calculator"]` panel
as the primary card on the page. A nav link labelled *Body Composition*
sits in `templates/base.html` between *Profile* and *Volume Splitter*
(active-state highlight wired through `static/js/modules/navbar.js`
pathMap, same pattern Issue #12 established). Layout inside the page:

1. **Inputs** — neck / waist / (hip if female) tape-measurement fields
   with inline diagrams sourced from the existing iconography
   (or simple SVG silhouettes — no new vendor assets).
2. **Live result panel** — updates on every `input` event:
   - Big number: `BFP = 18.2 % (Navy method)` with a small badge
     showing the formula used.
   - `Fat mass: 13.6 kg · Lean mass: 61.4 kg`.
   - ACE segmented band with the tick at the user's value.
   - Jackson & Pollock comparison line for the user's age.
3. **Save snapshot button** — writes a row to
   `user_profile_body_fat_snapshots`, then clears the in-memory form to
   the latest saved values.
4. **Trend chart** — lightweight inline SVG line chart (no chart
   library, same approach as Issue #18 cohort bars) showing BFP over
   time from snapshots. Hover/tap surfaces the date + value. Empty
   state: *"Save a snapshot to start tracking progress."*
5. **Snapshot history table** — date · BFP (Navy) · BFP (BMI) · LM ·
   FM, sortable by date, with a *delete* control per row.

Tape-measurement guidance copy is rendered in a collapsible *"How to
measure"* sub-section directly under the inputs, transcribed from the
Hodgdon & Beckett protocol exactly:

- Waist (men): horizontal at navel; do not pull stomach inward.
- Waist (women): at the smallest natural width.
- Neck: below the larynx, tape sloping downward to the front; do not
  flare neck outward.
- Hip (women only): largest horizontal hip circumference.

---

### Read-only consumption by the estimator

Body composition values are **never** used to alter weight / rep / RIR
suggestions in v1. The new table is queryable by any future consumer,
but **no Profile-page integration ships in this issue**. Two display
hooks were considered and explicitly deferred as part of the
2026-04-28 scope change:

- ~~`latest_lean_mass_kg` surfaced on the Issue #18 cohort tile as a
  *"Lean mass: 61 kg"* sub-line on the bodyweight tile.~~
  **Deferred** — filed as a follow-up cross-page-display issue once
  `/body_composition` has shipped and snapshots are routinely
  captured.
- ~~`latest_bfp` surfaced on the Issue #17 *"How the system sees you"*
  card as a one-line context: *"Body fat: 18.2 % · Athletic range
  (ACE)."*~~ **Deferred** — same follow-up.

If a future issue wants to use lean mass to refine cold-start ratios
(today they're scaled by total bodyweight), that is a separate
follow-up. Keeping consumption read-only in v1 protects the existing
test baseline for the estimator and avoids cross-tab coupling between
the new page and the Profile page on day one.

---

### Citations

The user-facing copy must cite both reference tables:

- ACE band: *"American Council on Exercise — Body Fat Categorization."*
- Jackson & Pollock line: *"Jackson, A.S. & Pollock, M.L. — Ideal Body
  Fat Percentages by Age."*
- Formula footer: *"U.S. Navy circumference method (Hodgdon & Beckett,
  1984)."*

These citations render as a small `<footer>` block at the bottom of the
calculator section — no clickable external links from the app
(consistent with the offline-first, no-network posture documented in
the CLAUDE.md non-goals).

---

### Acceptance checklist

- [ ] `utils/body_fat.py` exposes `compute_navy(...)`,
  `compute_bmi(...)`, `ace_category(bfp, gender)`, and
  `jackson_pollock_ideal(age, gender)`. All four are pure functions
  (no DB access) and have the explicit *"must match JS mirror"*
  comment from Issue #17.
- [ ] DB migration `add_body_composition_snapshots_table()` is
  idempotent and ships with a unit test in `tests/test_db_migration.py`
  (or the equivalent existing migration test file).
- [ ] New blueprint `routes/body_composition.py` (registered in
  `app.py` next to the existing 11 blueprints) adds four endpoints:
  `GET /body_composition` (page),
  `POST /api/body_composition/snapshot`,
  `GET /api/body_composition/snapshots`,
  `DELETE /api/body_composition/snapshots/<id>`. All four JSON
  endpoints use the standard `success_response()` / `error_response()`
  envelopes per
  [`.claude/rules/routes.md`](../../.claude/rules/routes.md).
- [ ] Hip field is hidden + not submitted when `gender == M`; server
  rejects a hip value with `gender == M` to enforce the contract
  cleanly.
- [ ] Validation: out-of-range / log-domain inputs return a structured
  4xx error with a per-field message; the form surfaces the message
  inline.
- [ ] Live result updates on every input event (no save round-trip),
  matching the Issue #17 / #18 / #19 JS-mirror contract.
- [ ] ACE band tick + Jackson & Pollock comparison line render with
  citations.
- [ ] Trend chart renders empty state with zero snapshots, then a
  growing line as snapshots are saved.
- [ ] Snapshot history table sorts by date desc and supports
  per-row delete.
- [ ] Pytest: `tests/test_body_fat.py` covers
  `compute_navy()` (male + female + log-domain rejection),
  `compute_bmi()` (adult / boy / girl), `ace_category()` boundary
  rows, `jackson_pollock_ideal()` interpolation including age clamp.
- [ ] Pytest: new `tests/test_body_composition_routes.py` covers each
  new endpoint (success + 4xx + delete-not-found) plus a smoke test
  that the page renders with `gender` / `age` / `height` /
  `bodyweight` pulled from the existing user-profile row.
- [ ] Playwright: new spec `e2e/body-composition.spec.ts` fills the
  tape inputs, asserts the live BFP / FM / LM values match the
  expected formula output, saves a snapshot, and asserts the new row
  appears in the history table + on the trend chart.
- [ ] Navbar: `templates/base.html` renders a *Body Composition* link
  between *Profile* and *Volume Splitter*; `static/js/modules/navbar.js`
  pathMap entry added so the active-state highlight from Issue #12
  fires on `/body_composition`.
- [ ] **Deferred to follow-up (NOT in this issue):**
  Issue #18 bodyweight tile *"Lean mass"* sub-line and Issue #17
  *"Body fat: X % · {ACE band}"* line. Both are filed as a separate
  cross-page-display issue once `/body_composition` is shipped and
  snapshot data is routinely captured.
- [ ] Estimator outputs (weight / rep / RIR / RPE / set count) are
  byte-identical before and after this issue ships — verified by
  running the existing pytest baseline (1080 tests as of 2026-04-28)
  unchanged.

---

## Summary table

| # | Title | Severity | Area | Status |
|---|-------|----------|------|--------|
| 21 | Body Composition tab — BFP / Lean Mass / longitudinal snapshots on a standalone `/body_composition` tab | 🟢 Enhancement | New blueprint + template + `body_fat.py` + DB table | Open — moved here from `docs/user_profile/development_issues.md` on 2026-04-28 |

---

*Last updated: 2026-04-28 — extracted from the Profile-page tracker
into its own folder. Issue body unchanged from the 2026-04-28
scope-change revision.*
