# Plan Review — bare `.scale-btn` family in `static/css/a11y.css`

*Instantiated from [`docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md`](../ai_workflow/PLAN_REVIEW_TEMPLATE.md).*

**Planning size: Large.** `static/css/a11y.css` is a shared surface, and
[`QUALITY_GATE.md`](../ai_workflow/QUALITY_GATE.md) §"CSS (static bundles)" states
outright that *"a shared-surface change is **Large** at plan stage"*. Large requires
**Gate 0 + Gate 1**.

**Goal statement (verbatim, as commissioned):**

> Independently audit all eleven bare `.scale-btn` rule occurrences and, only if every
> member is mechanically certified as unreachable and safely removable, delete the family
> with complete contracts, verification evidence, and a draft PR. A rigorously
> demonstrated retention/no-op outcome also completes the goal.

---

## Section 0 — Requirements Brief

**Raw request** (verbatim, owner prompt of 2026-08-04)

> You are the sole manager and implementation owner for a standalone refactor packet
> covering the dormant bare `.scale-btn` rules in `static/css/a11y.css`.
>
> […]
>
> OWNER DECISIONS — ALREADY SETTLED
>
> Treat this prompt as owner approval of Gate 0 requirements:
>
> - Scope is exactly the eleven bare `.scale-btn` occurrences: base, hover, focus,
>   active, active-hover, five `[data-scale]` rules, and the media occurrence. The live
>   `.scale-btn-compact` generation is out of scope and protected.
> - Adjudicate the eleven occurrences as one family. No partial erosion.
> - `accessibility.js` is evidence only. Do not delete or redesign its dormant query
>   paths in this packet.
> - Delete the family only if every member is certified. Otherwise retain everything and
>   close with evidence explaining the failed criterion.
> - A no-production-change audit is an acceptable successful outcome.
> - No P3 work is authorized. P3 remains terminated.
> - Do not change `theme-dark.css`, visual tolerances, masks, retries, snapshots,
>   Playwright configuration, visual helpers, workflow files, baseline JSON, or unrelated
>   `!important`/custom-property/focus rules.
> - Do not add a new CSS bundle, debug abstraction, or reusable framework unless the
>   evidence cannot be produced using the committed `scripts/css_audit/` tools and a
>   narrowly scoped extension.
> - Preserve all user-visible behavior, accessibility behavior, scale levels, keyboard
>   focus guarantees, response contracts, database state, and calculations.

### Gate 0 status — APPROVED BY THE COMMISSIONING PROMPT

The owner prompt declares *"Treat this prompt as owner approval of Gate 0
requirements."* The nine settled requirements quoted above are therefore recorded as
**owner-signed**, not as assumptions this packet invented. They are restated as binding
constraints **C1–C9** in Plan v1 §Constraints, and every one is traceable to a quoted
line.

### Problem

`static/css/a11y.css` carries eleven exact-token `.scale-btn` rule occurrences that no
document has ever been shown to render. They are the residue of a superseded scale-control
generation whose container, label and group classes were deleted by **WP4.4-d1**
(PR #197, squash `59e5b10`) — but `d1` explicitly **excluded** these eleven from its
candidate set and recorded the exclusion as a gap for a later packet.

`d1` evidence §3a states the reason precisely, and it is a methodological point rather
than an oversight:

> The static pass had treated `scale-btn` as *reachable* purely because the literal
> string appears in that JS file. That is precisely the "a JavaScript query alone does
> not prove reachability" trap. Consequently the bare `.scale-btn` rules (11 exact-token
> occurrences) were **never audited as d1 candidates**, and they are **retained
> untouched**. The gap is recorded here rather than generalized from; deleting them would
> require its own census and its own packet.

Three canonical documents carry the same gate in identical terms —
[`MASTER_HANDOVER.md:1769`](../MASTER_HANDOVER.md),
[`REFACTOR_PLAN.md:1655`](../REFACTOR_PLAN.md) and
[`ACTIVE_DEVELOPMENT.md:249`](../ACTIVE_DEVELOPMENT.md). This packet is the "own census
and own packet" all three name.

**What is missing is proof, not intent.** The only runtime measurement that exists is
`d1`'s incidental census of `.scale-btn[data-scale]` — a *prefix* of five of the eleven
members. Nothing has ever measured bare `.scale-btn`, `:hover`, `:focus`, `.active`,
`.active:hover`, or the `@media` occurrence.

### Acceptance criteria

1. Given current `origin/main`, when the eleven occurrences are enumerated structurally,
   then each is pinned by **source identity** (selector text + byte offset + line +
   enclosing at-rule), not by substring or ordinal, and the count is exactly **11**.
2. Given a running app, when a **full-selector** natural census runs **before any
   synthetic injection**, across both themes, every `a11y.css` breakpoint edge, all eight
   `data-scale` levels, print emulation and reduced motion, then every one of the eleven
   selectors reports census **0** — or the family is retained.
3. Given the same run, when the **known-live controls** (`.scale-control-compact`,
   `.scale-btn-compact`, `.scale-indicator`, `[data-visual-scale-control]`) are measured
   on the same oracle, then each reports census **> 0**; if any does not, the oracle is
   invalid and **no candidate result from that run counts**.
4. Given a **known-dead** control and a **same-CSS** control run, when both execute, then
   the known-dead control reports dead and the same-CSS control reports **zero** differing
   records. A same-CSS control that differs invalidates the entire run.
5. Given interaction states, when `:hover`, `:focus`, `.active` and `.active:hover` are
   exercised **under their real conditions** on a synthetic bearer, then each rule's own
   declared properties are read with transitions suppressed **before apply, read and
   removal**, and each sentinel is asserted to have **taken effect and reverted**.
6. Given deletion, when the post-deletion oracle re-runs, then the flip is stated **by
   exact source identity** — never as "the rule went blind" — and every one of the eleven
   is demonstrated to have flipped. **If any single member is oracle-blind or its flip is
   unprovable, the entire family is retained.**
7. Given the contract suite, when each new or amended assertion is violated, then it goes
   **red** (red path executed, not asserted in prose), and no existing guarantee in
   `tests/test_css_wp4_4_a11y_contracts.py` is weakened — replacements must be *stronger*
   and structural.
8. Given the full shared-surface gate, when it runs, then pytest, the required Chromium
   functional specs, the seeded `visual.spec.ts` matrix and seven-surface Stylelint all
   pass with **no Stylelint category increase** and **no baseline, tolerance, mask, retry
   or snapshot change**.
9. Given the terminal deliverable, when the packet closes, then it is **either** a draft
   PR containing a fully certified whole-family deletion **or** a durable audit recording
   why the family remains — both are successful outcomes.

### Calculation surface

**`none`.** No Python module, route, response shape, database table or calculation is
read or written. Effective Sets, RIR/RPE, weekly/session summary, progression, fatigue
and volume distribution are untouched. The packet's entire production write set is a
**deletion of CSS declarations** from one file, plus test-only additions.

Accordingly, the root [`CLAUDE.md`](../../CLAUDE.md) §1 *Refactor invariant* is satisfied
vacuously on the calculation half, and by the contract additions on the coverage half.

### In scope

- Adjudicating the eleven bare `.scale-btn` occurrences in `static/css/a11y.css` **as one
  family**.
- Structural + runtime evidence sufficient to certify or refuse the whole family.
- `tests/test_css_wp4_4_a11y_contracts.py` — structural, red-path-proven contracts.
- `docs/css_scale_btn_cleanup/**` — this plan and the evidence document.
- Regenerating `docs/test_inventory/TEST_INVENTORY.{json,md}` **only if** test-node counts
  change (required blocking CI gate) — see the escalation in Plan v1 §Conflicts.

### Out of scope / non-goals

- **The live compact generation** — `.scale-btn-compact` (6 occurrences),
  `.scale-control-compact`, `.scale-indicator`, `[data-visual-scale-control]`. Protected,
  and used as the oracle-validity control.
- **`static/js/accessibility.js`** — read-only evidence. Its two dormant
  `querySelectorAll('.scale-btn[data-scale]')` paths at `:144` and `:202` are **not**
  deleted, redesigned, or "cleaned up" here.
- `theme-dark.css`; visual tolerances, masks, retries, snapshots, `playwright.config.ts`,
  `e2e/visual-helpers.ts`, workflow files, `CSS_PHASE4_WP4_4_A_BASELINE.json`.
- Any **P3** / `theme-dark.css` `:where()` work — terminated at `P3-a0`, unauthorized.
- The other deferred families: `layout.css` `.tbl-show-*`/`.tbl-hide-*` (nine rules),
  the 235 declarations `h` withheld behind the frozen `@layer workout` span, the superset
  dark-tint gap (G4), unlinking `theme-dark.css` (R4).
- The `@media print` `.scale-control, .accessibility-dropdown` rule — a *different*
  class, retained whole by `d1` and pinned by an existing contract.
- Any `!important`, custom-property, or focus-system re-weighting. This packet is
  **pure deletion or nothing**; `d2` already adjudicated all 51 annotations.

### Assumptions made

- ⚠️ **The eleven are treated as a single coupled family**, so the five `[data-scale]`
  rules cannot be deleted while the base rule stays (or vice versa). This is owner-settled
  (*"Adjudicate the eleven occurrences as one family. No partial erosion."*), and it
  matches the precedent that governs `layout.css`'s `.tbl-*` helpers.
- ⚠️ **`d1`'s census is treated as a hypothesis, not as authority.** It measured
  `.scale-btn[data-scale]` — a prefix of five members — at a *different commit*, against a
  *different baseline set*. Criterion 2 re-derives all eleven from current `main`.
- ⚠️ **A green single visual compare is not treated as determinism evidence.** The visual
  gate is run and reported honestly against current baseline state; it is **not** the
  oracle for this packet, because `[data-visual-scale-control]` is a **registered visual
  blind spot** (`d1` §3), which is exactly why computed-style / declaration-owner evidence
  is load-bearing instead.
- ⚠️ **Certification is expected to succeed but is not presumed.** The plan carries a
  fully specified retention path, and a no-op is pre-authorized as success.

### Open questions for the user

`none` **blocking.** One item is *escalated for awareness* at Gate 1 rather than asked as
a question, because it has a correct default: the `TEST_INVENTORY` / PR #296 file overlap
in Plan v1 §Conflicts.

### Section 0 sign-off — GATE 0

- [x] User confirms the acceptance criteria match intent. — *Owner prompt: "Treat this
      prompt as owner approval of Gate 0 requirements."*
- [x] User reviewed the assumptions and corrected or accepted each one. — *The four
      assumptions restate owner-settled decisions; none introduces new scope.*
- [x] Blocking questions are answered. — *None are open; the one awareness item is
      batched into the single Gate 1 message.*

---

## Plan v1

**Goal**: Determine, by independent mechanical evidence, whether all eleven bare
`.scale-btn` occurrences in `static/css/a11y.css` are unreachable — and delete the family
whole if and only if every member is certified, leaving user-visible behavior, scale
levels and keyboard-focus guarantees provably unchanged either way.

### Constraints (owner-settled, binding)

| # | Constraint | Source |
|---|---|---|
| **C1** | Scope is exactly the eleven bare occurrences; `.scale-btn-compact` is protected. | prompt |
| **C2** | One family, no partial erosion. | prompt |
| **C3** | `accessibility.js` is evidence only — not deleted, not redesigned. | prompt |
| **C4** | Delete only if **every** member certifies; else retain all and explain. | prompt |
| **C5** | A no-production-change audit is a **successful** outcome. | prompt |
| **C6** | No P3 work. | prompt + `MASTER_HANDOVER.md` termination |
| **C7** | No change to `theme-dark.css`, tolerances, masks, retries, snapshots, Playwright config, visual helpers, workflows, baseline JSON, or unrelated `!important`/custom-property/focus rules. | prompt |
| **C8** | Reuse committed `scripts/css_audit/`; no new bundle/framework absent necessity. | prompt + `verification.md` §"Reuse the committed harness" |
| **C9** | Preserve user-visible + accessibility behavior, scale levels, keyboard focus, response contracts, DB state, calculations. | prompt |
| **M-a** | Validate the oracle before trusting it — known-live, known-dead, and same-CSS controls. | `.claude/rules/verification.md` |
| **M-b** | A rest-state differential **cannot falsify an unreachable rule**; pair it with a full-selector census taken before injection + a control failing by exactly one compound. | `MASTER_HANDOVER.md` method 1 |
| **M-c** | State the post-deletion flip **by source identity**, never "went blind". | `MASTER_HANDOVER.md` method 3 |
| **M-d** | No substring assertions where duplicate selector text can mask a deletion. | `MASTER_HANDOVER.md` method 4 |
| **M-e** | Suppress transitions before apply, read **and** removal; assert each sentinel took effect. | M6a / `verification.md` |
| **M-f** | Never use `nth-child` position or re-serialized CSS text for rule identity; match selector + source offset. Normalize CRLF before offset math. | `verification.md` §Windows |

### Scope

- **In**: `static/css/a11y.css` (deletion only); `tests/test_css_wp4_4_a11y_contracts.py`
  (contracts); `docs/css_scale_btn_cleanup/{PLANNING.md,EVIDENCE.md}`; conditionally
  `docs/test_inventory/TEST_INVENTORY.{json,md}` (generated, only on node-count change).
- **Out**: everything in Section 0 §Out of scope. In particular the packet writes
  **exactly one production file**, and only by deleting from it.

### The eleven members, pinned

Enumerated from `origin/main` = `ac2923b`. Line numbers are provisional and will be
re-pinned mechanically by byte offset at execution (M-f).

| # | Selector | Line | Enclosing at-rule | Declared properties |
|---|---|---|---|---|
| 1 | `.scale-btn` | 128 | — | `display,align-items,justify-content,width,height,padding,border,background,color,font-size,font-weight,border-radius,cursor,transition` |
| 2 | `.scale-btn:hover` | 145 | — | `background,color` |
| 3 | `.scale-btn:focus` | 150 | — | `outline,outline-offset` |
| 4 | `.scale-btn.active` | 155 | — | `background,color,box-shadow` |
| 5 | `.scale-btn.active:hover` | 161 | — | `background` |
| 6 | `.scale-btn[data-scale="1"]` | 166 | — | `font-size` |
| 7 | `.scale-btn[data-scale="2"]` | 170 | — | `font-size` |
| 8 | `.scale-btn[data-scale="3"]` | 174 | — | `font-size` |
| 9 | `.scale-btn[data-scale="4"]` | 178 | — | `font-size` |
| 10 | `.scale-btn[data-scale="5"]` | 182 | — | `font-size` |
| 11 | `.scale-btn` | 312 | `@media (max-width: 991.98px)` | `flex,max-width` |

**Zero `!important`, zero custom properties, zero `@layer` tokens** across all eleven —
so the d1/d2 boundary and M9 hold by construction, exactly as they did for `d1`.

**Member 11 is the trap.** Its selector text is byte-identical to member 1, so any
presence/absence assertion on `".scale-btn"` cannot distinguish them — the same defect
class that `d1` hit on `.scale-control` (its defect #5) and that `e` hit independently.
Contracts must be **occurrence-count or source-shape** based (M-d).

### Structural finding already in hand (pre-council)

An exact-token PCRE sweep (`scale-btn(?![-\w])`) over the whole repository, excluding
`node_modules/` and `artifacts/`, returns:

| Location | Count | Nature |
|---|---|---|
| `static/css/a11y.css` | **11** | the candidate family — *the only CSS anywhere* |
| `static/js/accessibility.js` `:144`, `:202` | 2 | `querySelectorAll` **queries** (evidence, C3) |
| `docs/**` | 8 | prose describing the gate |
| `templates/**` | **0** | — |

`templates/base.html` emits `class="scale-btn-compact"` at `:193` and `:201`. A CSS class
selector matches whole class **tokens**, so `.scale-btn` does *not* match
`class="scale-btn-compact"`; the two are independent. This is the substring hazard the
census must not be fooled by, in either direction.

`accessibility.js` contains **no** `createElement`, `innerHTML`, `insertAdjacentHTML` or
`outerHTML`, and its only `classList` mutations are `'open'` on the (also absent)
dropdown and `'active'` on the result of the empty `NodeList`. So the chain is:

> no template emits the token → no JS constructs the element → the `querySelectorAll` at
> `:144`/`:202` returns an empty set → the `classList.toggle('active', …)` at `:205`
> **never executes** → `.scale-btn.active` and `.scale-btn.active:hover` are unreachable
> *by construction*, and `:hover`/`:focus` are unreachable because no bearer exists.

This is a **static** hypothesis. Criterion 2 replaces it with measurement.

### Artifacts

| Path | Change | Notes |
|---|---|---|
| `static/css/a11y.css` | modify (delete only) | The eleven blocks, atomically. Nothing else. |
| `tests/test_css_wp4_4_a11y_contracts.py` | modify | Add occurrence-count + source-shape contracts; strengthen, never weaken. |
| `docs/css_scale_btn_cleanup/PLANNING.md` | new | This file. |
| `docs/css_scale_btn_cleanup/EVIDENCE.md` | new | Raw controls, candidate results, before/after metrics, limitations. |
| `docs/test_inventory/TEST_INVENTORY.{json,md}` | regenerate **iff** node count moves | Blocking `Test Inventory Drift` gate. Final branch step. |
| `scripts/css_audit/**` | **unchanged** | Packet-`a`-owned (A11, C8). Reused via a scratch driver under gitignored `artifacts/`. |

**Effort**: L · **Owner**: sole manager + implementer (this session) · **Depends on**:
nothing — `d1`/`d2` are merged; the family is explicitly gated to its own packet.

### Sequence

1. **Pin identity.** Enumerate the eleven by selector + LF-normalized byte offset +
   enclosing at-rule. Assert count == 11 and that members 1 and 11 are distinguished by
   offset, not text (M-f, M-d).
2. **Build the probe** as a scratch driver under gitignored `artifacts/`, reusing
   `scripts/css_audit/runtime_probe.mjs` primitives. Do **not** modify `scripts/css_audit/`
   (C8).
3. **Oracle-validity gate first (M-a).** Measure the four known-live controls, a
   known-dead control, and a same-CSS control run. **Abort and retain** unless all pass.
   Report raw control output.
4. **Natural full-selector census, before any injection (M-b).** Full selector text for
   all eleven, across 2 themes × the `a11y.css` breakpoint-bracketing widths (375, 576,
   768, 769, 820, 991, 992, 1200, 1440, 1920 — note the **decimal** `991.98px` boundary,
   `d1`'s defect #1) × `data-scale` 1–8, plus print emulation and reduced motion.
5. **Interaction-state + synthetic certification (M-e).** Inject a synthetic `.scale-btn`
   bearer plus a control failing by exactly one compound; exercise `:hover`, `:focus`,
   `.active`, `.active:hover` and `[data-scale="1".."5"]` under their real conditions,
   reading **properties derived from each rule's own declarations**. Suppress transitions
   before apply, read and removal; assert every sentinel took effect **and reverted**.
6. **Declaration-owner evidence (CDP `CSS.getMatchedStylesForNode`)**, because
   `[data-visual-scale-control]` is a registered visual blind spot and pixels may not be
   cited (`QUALITY_GATE.md:39`).
7. **Decide.** All eleven certified → proceed. Any member blind or unprovable → **retain
   the whole family**, write the no-op verdict, stop.
8. **Delete atomically**, re-run the oracle, and state each member's flip **by source
   identity** (M-c), attributing any residual selector-text match to its retained owner.
9. **Contracts + red paths.** Execute every red path; record raw output.
10. **Full shared-surface gate** per `QUALITY_GATE.md`.
11. `/verify-and-polish`, `code-reviewer`, `unslop-reviewer`, handover.
12. Rebase onto current `main`, regenerate inventory iff counts moved (final step),
    commit, push, **draft** PR, monitor CI. **Never self-merge.**

### Expected gates

Derived from the `QUALITY_GATE.md` **CSS (static bundles) → shared surfaces** row, since
`a11y.css` is one of the eight shared bundles:

- **pytest**: full suite (the cascade contracts run inside that total), plus focused
  `tests/test_css_wp4_4_a11y_contracts.py` with every red path executed.
- **e2e (Chromium)**: `smoke-navigation`, `nav-dropdown`, `accessibility`, `dark-mode`,
  `summary-pages`, `volume-progress`, `fatigue`, `fatigue-stage4-smokes`, `ui-hardening`.
- **visual**: full seeded `visual.spec.ts` matrix with `PW_VISUAL_SEED=1`. **Reported, not
  used as the certifying oracle** (registered blind spot). No rebaseline, no tolerance
  change, no `--update-snapshots`.
- **Stylelint**: `node scripts/css_audit/stylelint_surfaces.mjs`, seven surfaces, **no
  category may rise**.
- **Linux deep gate**: interpreted honestly against current baseline state, *not* against
  the stale `CSS_PHASE4_WP4_4_LINUX_INHERITED_REDS.json` — `QUALITY_GATE.md:39` records
  that the ledger's `sourceCommit` `46e340e` predates PR #281's owner-accepted
  regeneration, so reconciling against it **mis-attributes**.
- **CI hidden gates**: `pyright` measure-only actually blocks net-new diagnostics, and
  `Test Inventory Drift` is a required context that fails on any node add/remove.

### Conflicts and blockers — stated, not resolved unilaterally

1. **`TEST_INVENTORY` vs PR #296.** `Test Inventory Drift` is a **required**
   branch-protection context and fails on any net test-node change. New contracts will
   almost certainly move the count, so CI *requires* regenerating
   `docs/test_inventory/TEST_INVENTORY.{json,md}`. Those two files are also modified by
   **PR #296**. Regenerating a mechanically generated artifact does not touch #296's
   investigation surface (`e2e/visual-helpers.ts`, `playwright.config.ts`,
   `tests/test_visual_capture_contracts.py`, `docs/visual_determinism/PLANNING.md` — all
   untouched here), but it *will* conflict on merge order. **Escalated at Gate 1.**
2. **The repository-wide visual position.** On current `main`,
   `docs/visual_determinism/PLANNING.md` records **Gate 2 PASSED — 86/86 byte-identical
   across three isolated generations**. PR #296 is a *later, separate* draft investigation
   into workout-table raster nondeterminism that **must not merge**. This packet touches
   none of its files, runs the seeded visual matrix normally, and — per the owner
   instruction — will mark the visual merge gate **blocked** rather than claim a single
   green compare as determinism, if the repository-wide blocker is still open at
   execution time.
3. **Windows vs Linux baseline asymmetry.** The Windows ledger carries two open deferred
   reds (`workout-plan desktop dark`, band 875/882 ∪ 1,039/1,046; and
   `plan-desktop-light-advanced`, band ~6,084–6,262). Both are pre-existing, both are
   bands not constants, and neither may be "fixed" by raising `maxDiffPixels`.

---

## Agent provenance

| Role | Agent ID | Notes |
|---|---|---|
| `product-manager` — Plan v1 | *not delegated* | The commissioning prompt names this session **"sole manager and implementation owner"**, so Section 0 and Plan v1 were authored directly by the owning session rather than delegated to a `product-manager` subagent. No ID was generated, and none is invented. |
| `product-manager` — response matrix + Plan v2 | *not delegated* | Same reason. |
| `architecture-reviewer` | `aea66cdbdf050ef44` | Step 2 reviewer. Verdict: **Needs revision** (2 blocking). |
| `test-strategist` | `acedc9f907bb453f8` | Step 2 reviewer. Verdict: **Needs revision** (5 blocking). |
| `product-risk-reviewer` | `ae163873105ea9679` | Step 2 reviewer. Verdict: **Needs revision** (2 blocking). |

**Same product-manager resumed for the matrix + Plan v2?** `n/a` — no `product-manager`
was spawned in either step; the sole-owner session wrote both.

**Evidence gap**:
> The `product-manager` delegation step of `/council-plan` was **deliberately not run**,
> because the commissioning prompt assigns this session sole manager *and* implementation
> ownership. This is a recorded deviation from the command's ownership note, not an
> unrecoverable ID: no `Agent(product-manager, …)` call was ever made, so no ID exists to
> record, and none was invented. The three **reviewer** IDs are real and are stamped
> verbatim below. Continuity between Plan v1 and Plan v2 is trivially established — the
> same session authored both.

---

## Reviewer findings

*Council step 2 ran three reviewers in parallel, each reading Plan v1 cold. Full verbatim
outputs are preserved in [`COUNCIL_FINDINGS.md`](COUNCIL_FINDINGS.md) — kept in a sibling
file purely for length; nothing is summarized away, and the response matrix below cites
each finding by its ID there.*

**Headline result: all three returned "Needs revision", for nine blocking findings
between them.** The council did real work — it found that Plan v1, as written, would have
routed itself into a *mandatory retention* for instrumentation reasons on **three of the
eleven members** (3, 8 and 11), and that the deletion would have shipped **entirely
ungated**.

### Independently verified before acceptance

Every load-bearing claim was re-checked against this worktree rather than taken on trust:

| Claim | Verification | Result |
|---|---|---|
| `*:focus { outline: none !important }` steals member 3's `outline` | `static/css/a11y.css:340` selector list → `:396-397` declarations | **CONFIRMED** — member 3's `outline: 2px solid var(--nav-accent)` (`:151`) is non-`!important` and can never compute |
| Member 8's `font-size` is byte-identical to member 1's | `a11y.css:139` vs `:175`, both `font-size: 0.75rem` | **CONFIRMED** — computed style cannot separate them |
| Member 11 is media-gated and needs a ≤991px viewport | `a11y.css:309-318` | **CONFIRMED** — declares `flex` + `max-width: 36px` only |
| `runtime_probe.mjs` cannot be imported or driven to this matrix | zero `export` tokens; `const VIEWPORT = {width:1440,…}` at `:58`; `main().catch()` at module scope `:946` | **CONFIRMED** — not reusable as a library |
| Committing a packet driver matches precedent | 11 packet-prefixed `.mjs` drivers already committed (`i_*`, `j_*`, `n4_*`, `visual_helper_band_proof`) | **CONFIRMED** |
| `.scale-btn-compact` is safe from a `\.scale-btn(?![\w-])` pattern | `navbar.css:1051,1464,1465` are all `-compact`; lookahead excludes them | **CONFIRMED** |
| An empty `@media` shell raises no Stylelint category | `.stylelintrc.json` enables no `block-no-empty` / `no-empty-source` | **CONFIRMED** |
| a11y.css `var()` fallbacks never render | `navbar.css:15-19` defines `--nav-accent: #0066cc`, `--nav-accent-hover: #0055aa`, etc. on `:root` | **CONFIRMED** — sentinels must expect *resolved* tokens |
| Empty-shell retention has in-repo precedent | WP4.3j-b kept five empty media shells deliberately (`CSS_PHASE4_WP4_3J_B_DEAD_EVIDENCE.md:238`) | **CONFIRMED** |

---

## Response matrix

Every finding has a disposition. Accepted findings strengthen proof without widening the
production write set; the two rejections are recorded with rationale.

| # | Finding | Reviewer | Disposition | Action in v2 |
|---|---|---|---|---|
| **A1** | `scripts/css_audit/` boundary drawn stricter than the owner drew it; `runtime_probe.mjs` exports nothing and hard-codes a 1440px viewport, so "reuse its primitives from `artifacts/`" means forking reviewed code into gitignored, unreproducible scripts | architecture | **accept** (blocking) | Commit one new sibling driver `scripts/css_audit/scale_btn_census.mjs`. This is precisely the *"narrowly scoped extension"* C8 authorizes, modifies **none** of the six shared packet-`a` tools, and matches the 11-driver precedent. Artifacts row changes `unchanged` → `add one file`. |
| **A2 / B3** | Sequence step 5 enumerates only members 2–10; members **1 and 11** are never certified, and member 11 needs a ≤991px viewport or it reads dead both before *and* after — d1 defect #1 recurring | architecture, test | **accept** (blocking) | Plan v2 adds the **per-member certification table** naming all eleven with an explicit sentinel property and viewport. Member 11 certifies and flips at ≤991px only. |
| **A3** | Criterion 2 promises "eleven selectors report census 0", but members 1 and 11 share one selector string — only **ten** distinct records exist | architecture | **accept** | Criterion 2 restated in terms of **rule identities keyed by source location**, with member 11 carrying a width-restricted denominator (d1's 164/164 vs 100/100 shape). |
| **A4** | "Byte offset" is not the unit any tool emits; CDP returns `{startLine,startColumn,…}`, and d1 defect #7 was exactly a `selectorList.range` vs `style.range` confusion | architecture | **accept** | Identity unit changes to **1-based source line range of the declaration block**, naming which CDP range is read, and stating that line pins are **revision-scoped** (pre-deletion only) so contracts use occurrence-count/source-shape instead. |
| **A5** | Existing `test_every_targeted_data_scale_level_still_has_rules` uses an unanchored `[data-scale="N"]` substring satisfied by three different families — already protects less than it claims | architecture | **accept** | Anchor it to `html[data-scale="{n}"]`. Pure strengthening, permitted by criterion 7. |
| **A6** | Sibling-surface resurrection guard hard-codes 5 surfaces, missing `motion.css`, `tokens.css` and all 11 `pages-*.css` | architecture | **accept** | Derive the surface list from `glob("static/css/*.css")` minus the generated `bootstrap.custom.min.css*`. |
| **A7 / B5 / P2** | **Nothing in the repository goes red on this deletion** — the premise (no DOM ever constructs the token) has no contract at all | architecture, test, product | **accept** (blocking) | Add `"scale-btn"` to `LEGACY_CLASSES`, plus an exact `count == 0` contract **and** a media-scoped assertion so restoring member 11 alone reds. Add a DOM-construction gate over `accessibility.js` (asserting it *stays inert* — reading it is not modifying it, so C3 holds). |
| **A8 / N2** | Deleting member 11 leaves an empty `@media (max-width: 991.98px) { }`; "the eleven blocks, nothing else" forbids removing it | architecture, test | **accept the ruling requirement; RETAIN the shell** | Follows the in-repo precedent: WP4.3j-b **kept** five empty media shells with an explanatory comment because *"collapsing them is structural work, not deletion of dead declarations."* The shell is retained with a one-line comment pointing at the evidence doc. Verified to raise no Stylelint category. |
| **B1 / P1** | Member 3's `outline` is unobservable — stolen by `*:focus{outline:none!important}` — so criterion 5's "sentinel took effect" is unsatisfiable, and criterion 6 then converts an instrumentation artifact into a retain verdict | test, product | **accept** (blocking) | Member 3's sentinel is **`outline-offset` only**, read in a `:focus`-that-is-not-`:focus-visible` state, with CDP matched-rules as the primary oracle. Member 4's `box-shadow` is read **with focus blurred** (else `*.active:focus` zeroes it). Both recorded as *evidence for* deletion, never as an abort trigger. |
| **B2** | Member 8 is not discriminable by computed style (identical `font-size` to member 1), so its "took effect" assertion passes vacuously and its flip is unprovable by computed value | test | **accept** (blocking) | Member 8 certifies and flips by **CDP `CSS.getMatchedStylesForNode` source range only**, and CDP runs on **both** sides of the deletion. |
| **B4** | The rest-state differential is dropped, contrary to `verification.md:52-56` which requires the sweep **and** a differential, each able to falsify the other | test | **accept** (blocking) | Added as an explicit sequence step, matching d1 §7a (declaration-owner + paint records). It is the only evidence that no brace-scoping or cascade side effect landed on *other* elements. |
| **B-gates** | Gate list omits the known-red register, `visual-field-separator.spec.ts`, and an explicit no-edit commitment on both shared contract files | test | **accept** | All three added to §Expected gates, plus an explicit "no `tests/conftest.py` change". |
| **N1** | Visual-gate justification is wrong-headed: the blind-spot mask is on the *live compact* control; the bare family is pixel-invisible simply because no document emits a bearer — and the matrix *is* a real collateral oracle | test | **accept** | Rationale corrected. The matrix is described as a **collateral-damage oracle** (it would catch a mis-scoped brace), not as merely "reported". |
| **N3** | `var()` fallbacks in the eleven are dead — `--nav-accent` etc. are defined on `:root` in `navbar.css` | test | **accept** | Sentinels pre-register **resolved** token values per theme. Members 4/5 stay distinguishable (`#0066cc` vs `#0055aa`) in both themes. |
| **N4** | Root `zoom` destabilizes computed px across scale levels | test | **accept** | Px sentinels compared **within** a `data-scale` level, never across. |
| **N5** | Widths are correct; but the 768px block gates no member, and 4 of 5 `.scale-control-compact` occurrences sit inside `@-moz-document`, which Chromium never parses | test | **accept** | Widths unchanged. Control roles pre-registered per oracle: `[data-visual-scale-control]` and `.scale-btn-compact` are the DOM-census controls; the `@-moz-document` asymmetry is declared so a correct run cannot falsely invalidate. |
| **N6** | Reduced motion sets `--nav-transition-fast: 0ms`, giving a free cross-check on M-e | test | **accept** | Sentinel pass runs under both motion conditions; disagreement is treated as an instrumentation signal. |
| **N7** | "Regenerate iff counts change" invites a hand-count — the exact blindspot B3 | test | **accept** | Decided mechanically with `generate_test_inventory.py --check`, run after the last test edit **and** after the rebase. |
| **N8** | Red-path spec too thin — must be **adversarial** (restore member 11 *alone*), must restore the tree, must record raw output | test | **accept** | All three added. Restoring member 1 would prove nothing about the assertion's ability to distinguish the two. |
| **N9** | Pre-council sweep table omits `tests/**` and its doc count is stale | test | **accept** | Sweep re-derived at execution; the stale premise reference at `tests/test_css_wp4_4_a11y_contracts.py:102` is updated as part of the contract work. |
| **N10** | §Expected gates names 9 specs; step 11's `/verify-and-polish` runs the **full** Chromium suite | test | **accept** | The 9-spec set is the **required** gate; the full suite also runs, with known-red dispositions pre-registered. |
| **P3** | Chromium-oracle competence over the eleven is never stated, in the one bundle containing a Firefox-only block | product | **accept** | Plan v2 and EVIDENCE state that all eleven sit **outside** `@-moz-document`, and that Firefox renders no scale control at all. |
| **P4** | The retained `@media print` `.scale-control` rule is itself inert against current markup; step 4's print emulation will observe it | product | **accept as record-only** | Recorded in EVIDENCE as a discovered-adjacent gap, explicitly **not acted on** — mirroring the d1 precedent that created this packet. Acting on it would be scope expansion. |
| **P5** | "A no-op is success" collapses three different retention causes into one verdict | product | **accept** | Criterion 9's retention branch splits into **(a) genuinely reachable** (real product finding, reopens the markup question), **(b) unreachable but property owned by a later `!important` rule** (instrumentation limit), **(c) harness failure** (re-run, record no verdict). EVIDENCE names which applies per member. |
| **P6** | Rebase happens *after* the full gate, inverting the recorded lesson that two green sibling PRs broke `main` | product | **accept** | Rebase onto current `main` moves to **before** the full gate; only the inventory regeneration stays last. |
| **R1** | *(implicit in A6)* extend the resurrection guard to all `pages-*.css` bundles | architecture | **accept, scoped** | Accepted as a glob over `static/css/*.css`. **Rejected** as a reason to audit those bundles for other dead classes — that is a different packet. |
| **R2** | *(implicit in P4)* fix the inert print rule while we are here | product | **reject — scope expansion** | `.scale-control` is a **different class**, retained whole by d1 and pinned by two existing contracts. Touching it would re-weight a rule this packet has not proved, exactly what d1 refused to do. Recorded, not fixed. |

---

## Plan v2

**Goal**: unchanged from v1 — certify or refuse the eleven bare `.scale-btn` occurrences
in `static/css/a11y.css` as one family, on independent mechanical evidence, deleting them
whole only if **every** member is certified.

**What changed from v1**: the *evidence design*, not the scope. v1's production write set
was already correct; v1's oracle was not capable of certifying three of the eleven
members, and its contract plan gated nothing. v2 fixes both, and adds one committed
driver file.

### Scope

- **In** (unchanged, plus two files under `scripts/css_audit/`):
  `static/css/a11y.css` (deletion only);
  `tests/test_css_wp4_4_a11y_contracts.py`; `docs/css_scale_btn_cleanup/**`;
  **new** `scripts/css_audit/scale_btn_census.mjs`; **one verdict row** in
  `scripts/css_audit/p3_ceiling.py` — required by the coverage gate that reds on
  any unassessed tool, data-only, and reopening no P3 packet; conditionally
  `docs/test_inventory/TEST_INVENTORY.{json,md}`.
- **Out**: unchanged from v1. Explicitly still out: the `.scale-control` print rule (R2),
  the live compact generation, `accessibility.js` source, `theme-dark.css`, P3, tolerances
  / masks / snapshots / Playwright config / visual helpers / workflows / baseline JSON,
  and the six shared packet-`a` tools.

### Per-member certification design — the core v2 addition

Each member is certified by a sentinel **derived from its own declarations**, chosen to be
*unique within the family*, plus CDP `CSS.getMatchedStylesForNode` as the universal
backstop that resolves every member by source range.

| # | Selector | Sentinel property | Expected (resolved) | Viewport | Notes |
|---|---|---|---|---|---|
| 1 | `.scale-btn` | `width`, `height`, `border-radius` | `28px`, `28px`, `6px` | any | unique in family |
| 2 | `.scale-btn:hover` | `background-color`, `color` | `--nav-surface-hover`, `--nav-text` per theme | any | real hover |
| 3 | `.scale-btn:focus` | **`outline-offset` only** | `1px` | any | `outline` is **unobservable** — owned by `*:focus{…!important}` (`a11y.css:340→396`). Requires `:focus` **and not** `:focus-visible`. **CDP is primary.** |
| 4 | `.scale-btn.active` | `box-shadow`, `background-color` | shadow present; `#0066cc` | any | read with focus **blurred**, else `*.active:focus` zeroes the shadow |
| 5 | `.scale-btn.active:hover` | `background-color` | `#0055aa` | any | distinguishable from member 4 in **both** themes |
| 6 | `[data-scale="1"]` | `font-size` | `0.65rem` | any | unique |
| 7 | `[data-scale="2"]` | `font-size` | `0.7rem` | any | unique |
| 8 | `[data-scale="3"]` | `font-size` | `0.75rem` | any | **collides with member 1** → certifies and flips by **CDP source range only** |
| 9 | `[data-scale="4"]` | `font-size` | `0.8rem` | any | unique |
| 10 | `[data-scale="5"]` | `font-size` | `0.85rem` | any | unique |
| 11 | `.scale-btn` (`@media ≤991.98px`) | `flex-grow`, `flex-basis`, `max-width` | `1`, `0%`, `36px` | **≤991px** | unique; invisible at ≥992px by construction |

Px sentinels are compared **within** a `data-scale` level (root `zoom`). Sentinels expect
**resolved** tokens, never the dead a11y.css `var()` fallbacks.

### Sequence (v2)

1. **Pin identity** — eleven rule identities by selector + **1-based declaration-block
   line range** + enclosing at-rule, on LF-normalized text. Assert count == 11 and that
   members 1 and 11 differ by at-rule and line range, never by text.
2. **Commit the driver** `scripts/css_audit/scale_btn_census.mjs`. The six shared
   packet-`a` tools are untouched.
3. **Oracle-validity gate first** — four known-live controls, one known-dead control, one
   same-CSS control run. Pre-register which oracle each control validates (the
   `@-moz-document` asymmetry is declared). **Abort and retain** unless all pass. Raw
   output reported.
4. **Natural full-selector census, before any injection** — 2 themes × 10 widths
   (375/576/768/769/820/991/992/1200/1440/1920) × `data-scale` 1–8, + print + reduced
   motion. Keyed by **rule identity**; member 11 carries the width-restricted denominator.
5. **Per-member synthetic certification** — the table above, all eleven, with a control
   failing the selector by exactly **one compound**. Transitions suppressed before apply,
   read **and** removal; every sentinel asserted to have taken effect **and reverted**.
   Run under both motion conditions.
6. **CDP declaration-owner pass**, both sides of the deletion — the universal backstop and
   the sole oracle for members 3 and 8.
7. **Rest-state differential** (declaration-owner + paint), per `verification.md:52-56`.
8. **Decide.** All eleven certified → proceed. Any member blind or unprovable → retain the
   whole family and record the verdict under cause **(a)**, **(b)** or **(c)**.
9. **Delete atomically.** Retain the now-empty `@media` shell with a one-line comment
   (WP4.3j-b precedent). Re-run the oracle; state each member's flip **by source
   identity**.
10. **Contracts + adversarial red paths** — restore **member 11 alone** for the
    occurrence-count contract; restore the tree; record raw output per path.
11. **Rebase onto current `main`** *(moved earlier, per P6)*.
12. **Full shared-surface gate** — full pytest; the 9 required Chromium specs **plus**
    `visual-field-separator.spec.ts`; full seeded `visual.spec.ts`; seven-surface
    Stylelint; Linux deep gate read against *current* baseline state. Known reds
    pre-registered.
13. `/verify-and-polish`, `code-reviewer`, `unslop-reviewer`, handover.
14. Regenerate the inventory **iff** `--check` reports drift (final step), commit, push,
    **draft** PR, monitor CI. **Never self-merge.**

### Expected gates (v2)

As v1, plus: `e2e/visual-field-separator.spec.ts`; explicit **no edit** to
`tests/test_css_cascade_contracts.py`, `tests/test_visual_selector_contracts.py` or
`tests/conftest.py`; the known-red register (`nav-dropdown` failures **block**;
`program-backup.spec.ts:79` is the one live known flake); and the visual matrix size
checked against the committed baseline count rather than a hardcoded number.

---

## Sign-off

- [x] Gate 0 complete when required by planning size — **approved by the commissioning
      prompt**, requirements quoted verbatim above.
- [x] Every finding has a disposition — 26 rows, 24 accepted, 2 rejected with rationale.
- [x] Agent provenance complete — three real reviewer IDs; the `product-manager`
      deviation is recorded honestly in the Evidence gap, with no invented ID.
- [x] User approved Plan v2. — **GATE 1 approved 2026-08-04**, with the
      `TEST_INVENTORY` overlap resolved as "regenerate normally from the final
      rebased branch state; treat it as a generated artifact".
- [x] Ready to implement. — implemented; see [`EVIDENCE.md`](EVIDENCE.md).
