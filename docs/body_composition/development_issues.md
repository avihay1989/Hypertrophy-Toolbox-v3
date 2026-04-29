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
**styling extends the existing `static/css/components.css` global bundle**
(no new runtime CSS file — the 8-route-bundle cap in
[`.claude/rules/frontend.md`](../../.claude/rules/frontend.md) is preserved),
`utils/database.py` (new table),
`app.py` (register blueprint + run migration on startup),
`tests/conftest.py` (register blueprint in `app` fixture + add new table
to `erase_data` drop list and `clean_db` fixture — three touchpoints,
per the "five places" rule in
[`.claude/rules/database.md`](../../.claude/rules/database.md)),
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

### Empty / NULL demographics — required pre-state

`/user_profile` demographics (`gender`, `age`, `height_cm`, `weight_kg`)
are all stored as nullable columns on `user_profile`
([`utils/database.py:498-502`](../../utils/database.py#L498-L502)) and
the row is created lazily on first save. The `/body_composition` page
must therefore handle the case where the row is missing or any of the
four required fields is NULL:

- If the `user_profile` row does not exist OR `gender` / `age` /
  `height_cm` / `weight_kg` is NULL: render the page in a **demographics-required
  empty state** — the inputs section is hidden and replaced by a single
  card explaining *"Body Composition needs your basic demographics first.
  Fill in gender, age, height, and bodyweight on the Profile page to
  enable this calculator."* with a primary button linking to
  `/user_profile#demographics`.
- The empty state still renders the navbar, page header, citations
  footer, and (if any rows exist) the snapshot history table + trend
  chart — only the live calculator card is gated.
- Both the Navy and BMI compute paths require the four demographics
  fields, so there is no "partial fallback" mode (e.g. show the BMI
  estimate but not the Navy one) — both formulas need `gender` and
  `height_cm` at minimum, and the BMI form needs `age` for the adult /
  juvenile branch.

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

Source: Deurenberg, Weststrate & Seidell (1991), *"Body mass index as a
measure of body fatness: age- and sex-specific prediction formulas"*,
British Journal of Nutrition 65(2):105–114. The published age cut for
the child formula is **≤15 years**, not `<18` — earlier drafts of this
spec used `<18` in error.

```
BMI = weight_kg / (height_m ^ 2)

Adult male   (age >  15):  BFP = 1.20 * BMI + 0.23 * age - 16.2
Adult female (age >  15):  BFP = 1.20 * BMI + 0.23 * age -  5.4
Boy          (age <= 15):  BFP = 1.51 * BMI - 0.70 * age -  2.2
Girl         (age <= 15):  BFP = 1.51 * BMI - 0.70 * age +  1.4
```

**Use:** the BMI form runs whenever Demographics are filled but **all**
tape inputs are blank (see *Partial tape input contract* below for the
mixed case). It is shown as a **fallback estimate** with an explicit
*"BMI-based — less accurate than Navy method"* badge so the user
understands the trade-off. Single source of truth: both formulas live
in `utils/body_fat.py`; the JS mirror has the explicit
*"must match Python"* comment, same contract as Issue #17.

#### Partial tape input contract (all-or-nothing)

To avoid silent BMI substitution masking user data-entry errors, the
calculator follows an **all-or-nothing** tape rule:

- **All tape fields blank** → BMI fallback runs; Navy result is hidden.
- **All gender-specific tape fields filled** (men: neck + waist;
  women: neck + waist + hip) → Navy result is the primary, BMI is also
  computed and shown as a secondary line.
- **Any tape field filled but the gender-specific set is incomplete**
  → return a structured 4xx with per-field validation messages
  (*"Waist is required when Neck is provided"*, etc.). Do **not**
  silently fall back to BMI in this case — that would hide the
  user's intent and produce a misleading number.

Both the live JS preview and the server-side POST validator enforce
the same contract; the JS mirror prevents the round-trip but the
server is authoritative.

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
    weight_kg       REAL    NOT NULL,            -- mirrors user_profile.weight_kg naming
    height_cm       REAL    NOT NULL,
    neck_cm         REAL,                        -- nullable: BMI-only snapshot
    waist_cm        REAL,
    hip_cm          REAL,
    age_years       INTEGER NOT NULL,
    gender          TEXT    NOT NULL CHECK(gender IN ('M', 'F')),
    bfp_navy        REAL,                        -- nullable when tape blank
    bfp_bmi         REAL    NOT NULL,            -- always computable from demographics
    fat_mass_kg     REAL,                        -- derived from bfp_navy when present, else bfp_bmi
    lean_mass_kg    REAL,
    notes           TEXT
);

CREATE INDEX idx_body_composition_snapshots_captured_at
    ON body_composition_snapshots(captured_at DESC);
```

The snapshot column is named `weight_kg` (not `bodyweight_kg`) to match
the source column on
[`user_profile.weight_kg`](../../utils/database.py#L501) — this avoids
a silent rename across the snapshot copy and keeps SQL joins readable.
The `gender` CHECK constraint is defence in depth: routes already
validate `gender ∈ {'M', 'F'}`, but mirroring the precedent set by
[`user_profile_preferences.tier`](../../utils/database.py#L518) keeps
the schema self-documenting.

**Migration:** added by a new
`add_body_composition_snapshots_table()` migration in
`utils/database.py`, registered in `app.py` startup sequence
**immediately after `add_user_profile_tables()`** (logical dependency:
the `/body_composition` page reads from the demographics row that
migration creates). Follow the same pattern documented in
[`.claude/rules/database.md`](../../.claude/rules/database.md), and
remember the **five-places** rule — function in `utils/database.py`,
call from `app.py`, plus three touchpoints in `tests/conftest.py`
(`app` fixture init, `erase_data` drop list, `clean_db` fixture
table list).

**Backup interaction (intentionally out of scope):** the new table is
**not** included in `/api/backups` snapshots and is **not** touched by
restore. This is consistent with the existing precedent —
[`utils/program_backup.py`](../../utils/program_backup.py) only
backs up `user_selection`; `user_profile`, `user_profile_lifts`,
`user_profile_preferences`, `progression_goals`, and the volume tables
are all similarly excluded. Broadening the backup scope to include
profile / preference / snapshot data is a separate follow-up issue
(intentionally not bundled here).

**No retention cap** in v1 — single user, local DB, no compliance
constraints. The user can manually delete snapshots from the UI. The
`GET /api/body_composition/snapshots` endpoint accepts an optional
`?limit=N` query parameter (capped server-side at 1000) so the trend
chart can request only the most recent N rows on a long-lived DB; the
history table omits the param to fetch all rows.

**Latest-row ordering must be deterministic.** Any "latest snapshot"
read (used by the chart's most-recent point and by the Issue #22
follow-up cross-page hooks) must use
`ORDER BY captured_at DESC, id DESC LIMIT 1`. The `id DESC` tiebreak
matters when two snapshots share a `captured_at` second (rapid double-tap
on Save, or restored backup data with truncated timestamps) — without
it, the "latest" can flip between page loads and produce flaky tests.

**Server is the source of truth for demographics.** The
`POST /api/body_composition/snapshot` endpoint reads `gender`, `age`,
`height_cm`, and `weight_kg` from the existing `user_profile` row
**at save time**, not from the client payload. The client submits only
the tape values (`neck_cm`, `waist_cm`, `hip_cm`) and an optional
`notes` string; any client-supplied demographic fields are ignored.
Rationale: snapshots become an audit trail of body composition over
time, and we never want a stale or hand-edited client value to corrupt
that record. If the `user_profile` row is missing or any required
field is NULL, the endpoint returns `400 PREREQUISITE_MISSING` with
the per-field list of what's missing; if `gender` is present but not
in `{'M', 'F'}` (e.g. legacy `"Other"` rows from earlier schema
versions), it returns `400 UNSUPPORTED_GENDER` and points the user
at `/user_profile#demographics` to update.

---

### UI

A new top-level page at `/body_composition` rendered as a standalone
template (`templates/body_composition.html` extending `base.html`),
with a `frame-calm-glass [data-section="body fat calculator"]` panel
as the primary card on the page. A nav link labelled *Body Composition*
is added to the **primary (left) navbar** in
[`templates/base.html`](../../templates/base.html), placed
**immediately after the existing `nav-volume-splitter` `<li>`** (line
~135) — the `Profile` link lives on the right utility navbar
(`<ul class="navbar-nav ms-auto">` at line 152), so the earlier draft's
*"between Profile and Volume Splitter"* phrasing was incorrect; the
two are not in the same `<ul>`. Use:
- `<li>` id: `nav-body-composition` (matches the
  `static/js/modules/navbar.js` pathMap convention).
- Icon: reuse an existing icon asset (e.g. a tape-measure or scale
  glyph already shipped under `static/images/`) — no new vendor
  assets per the offline-first posture.
- Mobile / collapsed navbar: inherits the existing
  `.navbar-collapse` behaviour from `base.html`; no custom dropdown
  is added.

Active-state highlight is wired through
[`static/js/modules/navbar.js`](../../static/js/modules/navbar.js)
pathMap (entry `'/body_composition': 'nav-body-composition'`,
inserted alongside the existing entries at line 16-26), same pattern
Issue #12 established. Layout inside the page:

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
   `body_composition_snapshots`, then clears the in-memory form to
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

The user-facing copy must cite all four reference sources:

- ACE band: *"American Council on Exercise — Body Fat Categorization."*
- Jackson & Pollock line: *"Jackson, A.S. & Pollock, M.L. — Ideal Body
  Fat Percentages by Age."*
- Navy formula footer: *"U.S. Navy circumference method (Hodgdon &
  Beckett, 1984) — field estimate, not a research-grade measurement."*
- BMI fallback footer (rendered next to the *"BMI-based — less
  accurate than Navy method"* badge): *"Deurenberg, Weststrate &
  Seidell (1991), Br. J. Nutr. 65(2)."*

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
  (or the equivalent existing migration test file). The migration is
  invoked from `app.py` startup **immediately after
  `add_user_profile_tables()`**.
- [ ] `tests/conftest.py` updated in three places per the
  [`.claude/rules/database.md`](../../.claude/rules/database.md)
  five-places rule: (a) `body_composition_bp` registered in the `app`
  fixture (else route tests 404); (b) `body_composition_snapshots`
  added to the `erase_data` drop list; (c) `body_composition_snapshots`
  added to the `clean_db` fixture's table list (else `clean_db`-using
  tests leak rows across runs).
- [ ] New blueprint `routes/body_composition.py` (registered in
  `app.py` next to the existing 11 blueprints) adds four endpoints:
  `GET /body_composition` (HTML page — not a JSON envelope),
  `POST /api/body_composition/snapshot`,
  `GET /api/body_composition/snapshots` (accepts optional `?limit=N`,
  capped server-side at 1000),
  `DELETE /api/body_composition/snapshots/<id>`. **The three `/api/...`
  endpoints** use the standard `success_response()` / `error_response()`
  envelopes per
  [`.claude/rules/routes.md`](../../.claude/rules/routes.md);
  `GET /body_composition` returns rendered HTML.
- [ ] Page renders the **demographics-required empty state** (inputs
  card hidden, primary button to `/user_profile#demographics`) when
  the `user_profile` row is missing OR any of `gender` / `age` /
  `height_cm` / `weight_kg` is NULL.
- [ ] Styling extends `static/css/components.css` (no new runtime CSS
  bundle) per the 8-route-bundle cap in
  [`.claude/rules/frontend.md`](../../.claude/rules/frontend.md).
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
- [ ] Pytest: a Python↔JS **mirror lockstep test** asserts the JS
  module's `compute_navy` / `compute_bmi` / `ace_category` /
  `jackson_pollock_ideal` constants and branch logic match the Python
  source, mirroring the precedent in
  [`tests/test_profile_estimator.py:1226`](../../tests/test_profile_estimator.py#L1226)
  (*"one side of the Python ↔ JS mirror without the other"*).
- [ ] Pytest: new `tests/test_body_composition_routes.py` covers each
  new endpoint (success + 4xx + delete-not-found) plus:
  - (a) full demographics → calculator card visible.
  - (b) missing `user_profile` row → empty-state card with link to
    `/user_profile#demographics`.
  - (c) one or more demographic field NULL → same empty-state card.
  - (d) **POST ignores client-supplied demographics** — payload with
    `gender="F"` against a `user_profile` row of `gender="M"` saves
    the snapshot with `gender="M"` (server wins), no validation error.
  - (e) **POST returns `400 PREREQUISITE_MISSING`** when called against
    a `user_profile` row with NULL demographics, with the per-field
    list in the error envelope.
  - (f) **POST returns `400 UNSUPPORTED_GENDER`** when the
    `user_profile.gender` value is outside `{'M', 'F'}`.
  - (g) **Partial-tape rejection** — POST with `neck_cm` set but
    `waist_cm` blank returns `400 VALIDATION_ERROR` with a per-field
    message (does **not** silently fall back to BMI).
  - (h) **Latest-row tiebreak** — insert two snapshots with the same
    `captured_at`, assert the higher-`id` row is returned as latest.
- [ ] Playwright: new spec `e2e/body-composition.spec.ts` fills the
  tape inputs, asserts the live BFP / FM / LM values match the
  expected formula output, saves a snapshot, and asserts the new row
  appears in the history table + on the trend chart. Also covers the
  empty-state path: visit `/body_composition` with no `user_profile`
  row, assert the demographics-required card and its CTA link render.
  Use the existing `e2e/fixtures.ts` `test` fixture (which collects
  console errors) and assert **zero browser console errors** across
  the full flow — same posture as the other Playwright specs.
- [ ] Navbar: `templates/base.html` renders a *Body Composition* link
  in the **primary (left) navbar**, immediately after the existing
  `nav-volume-splitter` `<li>` (id `nav-body-composition`,
  `data-testid="nav-body-composition"`). `Profile` is on the right
  utility navbar, so the new link is **not** placed beside it.
  `static/js/modules/navbar.js` pathMap entry
  `'/body_composition': 'nav-body-composition'` is added so the
  active-state highlight from Issue #12 fires on `/body_composition`.
- [ ] **Deferred to follow-up (NOT in this issue):**
  Issue #18 bodyweight tile *"Lean mass"* sub-line and Issue #17
  *"Body fat: X % · {ACE band}"* line. Both are filed as a separate
  cross-page-display issue once `/body_composition` is shipped and
  snapshot data is routinely captured.
- [ ] Estimator outputs (weight / rep / RIR / RPE / set count) are
  byte-identical before and after this issue ships — verified by
  re-running the **current pytest baseline at implementation time**
  (record the count from CLAUDE.md §5 *"Verified test counts"*
  immediately before starting the work, and assert the same count
  passes after) plus the relevant Chromium Playwright suites
  (`workout-plan`, `workout-log`, `summary-pages`, `progression`,
  `volume-splitter`). Avoid hardcoding a count in the spec — the
  baseline drifts as the suite grows.

---

## Issue #22 — Profile-page cross-page display hooks for body-composition data

**Severity:** 🟢 Enhancement — Small (display-only, no estimator math)
**Area:** `templates/user_profile.html`,
`static/js/modules/user-profile.js`,
`routes/user_profile.py` (read-only consumption of
`body_composition_snapshots`).

**Depends on:** Issue #21 shipped (snapshots being captured routinely).

> **Migrated 2026-04-29** from
> [`docs/user_profile/development_issues.md`](../user_profile/development_issues.md).
> Originally tracked as a deferral note inside Issue #21's body and
> the Profile-page tracker's Issue #21 placeholder. Promoted to its
> own issue here because (a) both hooks read from
> `body_composition_snapshots`, which is owned by `/body_composition`,
> and (b) consolidating the follow-up next to its data source avoids
> the cross-tracker breadcrumb trail.

Once `/body_composition` (Issue #21) is shipped and the user has at
least one snapshot, two display hooks should surface the latest
body-composition values on the Profile page. Both are **display only** —
no estimator math change, no automatic adjustment to weight / rep / RIR
suggestions. Consistent with the
[`utils/effective_sets.py:6-7`](../../utils/effective_sets.py#L6-L7)
informational invariant.

### Hook A — Lean mass sub-line on the bodyweight tile (Issue #18)

The "How the system sees you" card on `/user_profile` (Issue #18)
renders a row of cohort tiles. The bodyweight tile currently shows
the user's bodyweight only. Add a sub-line below the value:

> **Bodyweight: 75 kg**
> *Lean mass: 61 kg*

- Sub-line only renders when the latest `body_composition_snapshots`
  row has a non-NULL `lean_mass_kg`.
- Empty state when no snapshots exist: tile renders unchanged
  (no placeholder text — keep the tile clean).
- Source: latest row by `captured_at DESC` from
  `body_composition_snapshots`.

### Hook B — Body fat line on the "How the system sees you" card (Issue #17)

The transparency card on `/user_profile` (Issue #17) shows a
classification line. Append one new line beneath the existing copy:

> *Body fat: 18.2 % · Athletic range (ACE).*

- Line only renders when the latest snapshot has a non-NULL
  `bfp_navy` or `bfp_bmi` (prefer Navy when present, fall back to
  BMI; mirror the badge convention from Issue #21).
- ACE-band label comes from
  `utils/body_fat.py:ace_category(bfp, gender)` (the same pure
  function used on `/body_composition`).
- Empty state when no snapshots exist: line is omitted entirely.

### Acceptance checklist

- [ ] `routes/user_profile.py` reads the latest
  `body_composition_snapshots` row alongside the existing
  user-profile context (single extra `fetch_one` query).
- [ ] `templates/user_profile.html` renders the bodyweight-tile
  sub-line and the transparency-card line conditionally on
  snapshot presence.
- [ ] `static/js/modules/user-profile.js` re-fetches the
  Profile-page context after a snapshot is saved on
  `/body_composition` is **not** required in v1 — the user reloads
  the page; live cross-tab refresh is out of scope.
- [ ] `utils/body_fat.py:ace_category()` is the single source of
  truth for the ACE label (no duplicate lookup table in the
  Profile-page template / JS).
- [ ] Estimator outputs (weight / rep / RIR / RPE / set count) are
  byte-identical before and after this issue ships — display only.
- [ ] Pytest: extend `tests/test_user_profile_routes.py` with one
  case asserting the snapshot read happens and one case asserting
  the empty-snapshot path renders without the sub-line / fat line.
- [ ] Playwright: extend `e2e/user-profile.spec.ts` with a flow
  that visits `/body_composition`, saves a snapshot, then visits
  `/user_profile` and asserts both new lines render with the
  expected values.

---

## Summary table

| # | Title | Severity | Area | Status |
|---|-------|----------|------|--------|
| 21 | Body Composition tab — BFP / Lean Mass / longitudinal snapshots on a standalone `/body_composition` tab | 🟢 Enhancement | New blueprint + template + `body_fat.py` + DB table | Open — moved here from `docs/user_profile/development_issues.md` on 2026-04-28 |
| 22 | Profile-page cross-page display hooks: Lean mass sub-line (Issue #18 tile) + Body fat ACE band line (Issue #17 card) | 🟢 Enhancement | `templates/user_profile.html` + `routes/user_profile.py` (read `body_composition_snapshots`) | Open — migrated from `docs/user_profile/development_issues.md` on 2026-04-29; depends on #21 shipping |

---

*Last updated: 2026-04-29 — added Issue #22 (cross-page display
hooks) migrated from the Profile-page tracker so the follow-up
lives next to its data source. Issue #21 body revised in the same
pass to address blocking pre-implementation findings: extended
`components.css` instead of adding a new route bundle (preserves the
[frontend.md](../../.claude/rules/frontend.md) cap), made the three
`tests/conftest.py` touchpoints explicit per the
[database.md](../../.claude/rules/database.md) "five-places" rule,
fixed the stale `user_profile_body_fat_snapshots` reference in the
UI section, renamed the snapshot column to `weight_kg` for parity
with `user_profile`, added a `CHECK(gender IN ('M', 'F'))` constraint,
documented the demographics-required empty state, pinned the
migration call site (after `add_user_profile_tables()`), noted
backup integration is intentionally out of scope, added a `?limit=N`
parameter to the snapshots GET endpoint, corrected the route checklist
wording so `GET /body_composition` is not described as a JSON envelope,
and added Python↔JS lockstep + empty-state coverage to the test
checklist. A second editing pass then incorporated the remaining
Codex 5.5 deltas: BMI age threshold corrected from `<18` to `≤15` per
Deurenberg/Weststrate/Seidell (1991) with the citation added to the
user-facing footer; explicit *"all-or-nothing"* partial-tape contract
documented to prevent silent BMI substitution; `POST .../snapshot`
pinned to read demographics from the server-side `user_profile` row
(client demographics ignored), with structured `PREREQUISITE_MISSING`
and `UNSUPPORTED_GENDER` 4xx codes; navbar placement reframed —
*Body Composition* lives in the primary (left) navbar after
`nav-volume-splitter`, not "between Profile and Volume Splitter"
(Profile is on the right utility navbar); `ORDER BY captured_at DESC,
id DESC` mandated for any *latest-row* read; hardcoded *"1080 tests"*
baseline replaced with a *"current pytest baseline at implementation
time"* instruction; and a no-console-errors Playwright assertion
added. The Codex 5.5 second-LLM review section below is preserved
unchanged as historical record.*

---

## Second-LLM Review — Codex 5.5

*** codex 5.5 *** **Final verdict:** not approved to start as-is if the
target is 95% confidence that no existing feature, enhancement, flow, or
UI breaks. The feature direction is sound, but the plan has several
blocking precision gaps that should be corrected before implementation.

*** codex 5.5 *** **Blocking — DB/reset/test wiring is incomplete.**
The plan mentions startup migration only, but this repo also has hardcoded
full-reset and test harness paths. Add explicit checklist items for:
`app.py` startup import/call, production `/erase-data` drop list and
reinitialization, `tests/conftest.py` `_initialize_test_database()`,
test-app blueprint registration, test `/erase-data`, and `clean_db`
cleanup. Missing these can leave stale snapshot rows after reset or cause
route/migration failures in tests.

*** codex 5.5 *** **Blocking — table name contradiction.**
The persistence section defines `body_composition_snapshots`, but the UI
save step still says it writes to `user_profile_body_fat_snapshots`.
Resolve to `body_composition_snapshots` everywhere before implementation.

*** codex 5.5 *** **Blocking — BMI age boundary needs correction.**
The plan currently uses boy/girl formulas for `<18`. The cited
Deurenberg / Weststrate / Seidell BMI equations define the child formula
for children aged 15 years and younger, and the adult formula otherwise.
Either change implementation and tests to `age <= 15`, or cite a different
source that justifies `<18`. Also add Deurenberg / Weststrate / Seidell to
the app citation footer if the BMI fallback is user-visible.

*** codex 5.5 *** **Blocking — partial tape input behavior is
under-specified.** Define this contract explicitly: when all tape fields
are blank, use BMI fallback; when any tape field is present, require the
complete gender-specific tape set and return per-field validation errors.
Do not silently fall back to BMI after partial tape entry.

*** codex 5.5 *** **Blocking — demographic source of truth must be the
server.** Snapshot POST should read `gender`, `age`, `height_cm`, and
`weight_kg` from the existing profile row at save time. Do not trust
client-submitted demographic values. Missing profile fields and historical
unsupported values such as `gender = "Other"` should return structured
4xx prerequisite/validation errors.

*** codex 5.5 *** **Correction — route checklist wording.** The checklist
says "All four JSON endpoints", but `GET /body_composition` is an HTML
page. Only the `/api/...` endpoints should use JSON envelopes.

*** codex 5.5 *** **Correction — CSS bundle rule conflict.** The plan adds
`static/css/pages-body-composition.css`, but `.claude/rules/frontend.md`
currently caps route CSS bundles and says not to add new runtime route
CSS files. Either intentionally update the CSS ownership/rules, or reuse
an existing approved bundle.

*** codex 5.5 *** **Correction — navbar placement is ambiguous.** The
current DOM has `Profile` on the right utility nav and `Volume Splitter`
as `Distribute` on the left primary nav. "Between Profile and Volume
Splitter" does not map cleanly to the actual navbar structure. Specify
the intended DOM location and mobile/dropdown behavior.

*** codex 5.5 *** **Correction — latest snapshot ordering.** Use
`ORDER BY captured_at DESC, id DESC` for "latest" reads so snapshots saved
in the same timestamp interval are deterministic.

*** codex 5.5 *** **Correction — stale test-count baseline.** Do not
hardcode "1080 tests". Require the current full pytest baseline and the
relevant Playwright suites to pass at implementation time.

*** codex 5.5 *** **Recommended acceptance additions before starting.**
Add tests for missing profile prerequisites, partial tape values, male hip
rejection, delete-not-found, reset table recreation, nav smoke, save/delete
flow, empty state, and no browser console errors. Add a drift test that
Python and JS formula outputs match on shared fixtures.

*** codex 5.5 *** **External source notes.** Navy/Hodgdon-Beckett direction
is reasonable, but cite it carefully as a field estimate rather than a
research-grade measurement. A 2022 Frontiers paper summarizes the military
circumference equations and their limitations. Deurenberg BMI formulas and
the child/adult threshold are available via Cambridge Core. ACE ranges were
checked against an ACE-hosted page.

*** codex 5.5 *** **Review sources:**
- https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2022.868627/pdf
- https://www.cambridge.org/core/journals/british-journal-of-nutrition/article/body-mass-index-as-a-measure-of-body-fatness-age-and-sexspecific-prediction-formulas/9C03B18E1A0E4CDB0441644EE64D9AA2
- https://www.acefitness.org/about-ace/press-room/in-the-news/8602/body-fat-percentage-charting-averages-in-men-and-women-very-well-health/
