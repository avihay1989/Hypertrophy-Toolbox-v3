# Bare `.scale-btn` family — census, certification and deletion

The follow-up packet WP4.4-d1 named but did not run. `d1` deleted a superseded
scale/menu generation from `static/css/a11y.css` and **deliberately excluded** the
eleven bare `.scale-btn` occurrences, because its static pass had read the
`querySelectorAll('.scale-btn[data-scale]')` calls in `static/js/accessibility.js` as
proof of reachability — "precisely the *a JavaScript query alone does not prove
reachability* trap" (d1 evidence §3a). All three canonical documents carried the same
gate: *"deleting them requires its own census, its own oracle-validity control and its
own packet."*

**Result: all eleven rules deleted as one family. −71 lines, +10 (one retained comment).**
`!important` 50 → 50, custom properties 17 → 17, `@layer` 0 → 0. Rest-state differential
**0 differing across 339,120 records**. Seven-surface Stylelint **2,759 → 2,752 (−7)**,
no category increased, the entire delta attributable to `a11y.css`.

Base: `origin/main` = `ac2923b`. Production ownership: `static/css/a11y.css` only.
Plan and council record: [`PLANNING.md`](PLANNING.md), [`COUNCIL_FINDINGS.md`](COUNCIL_FINDINGS.md).

---

## 1. The eleven, pinned by source identity

Enumerated structurally, then re-pinned by the browser's own parse via CDP
`CSS.getMatchedStylesForNode` against a synthetic bearer. The unit is the **1-based
declaration-block line range**, which is d1's proven unit — `style.range` is the
declaration-block range, *not* the whole rule (d1 defect #7).

| # | Selector | Block lines | At-rule | Declared properties |
|---:|---|---|---|---|
| 1 | `.scale-btn` | 128–143 | — | display, align-items, justify-content, width, height, padding, border, background, color, font-size, font-weight, border-radius, cursor, transition |
| 2 | `.scale-btn:hover` | 145–148 | — | background, color |
| 3 | `.scale-btn:focus` | 150–153 | — | outline, outline-offset |
| 4 | `.scale-btn.active` | 155–159 | — | background, color, box-shadow |
| 5 | `.scale-btn.active:hover` | 161–163 | — | background |
| 6 | `.scale-btn[data-scale="1"]` | 166–168 | — | font-size |
| 7 | `.scale-btn[data-scale="2"]` | 170–172 | — | font-size |
| 8 | `.scale-btn[data-scale="3"]` | 174–176 | — | font-size |
| 9 | `.scale-btn[data-scale="4"]` | 178–180 | — | font-size |
| 10 | `.scale-btn[data-scale="5"]` | 182–184 | — | font-size |
| 11 | `.scale-btn` | 312–315 | `@media (max-width: 991.98px)` | flex, max-width |

Zero `!important`, zero custom properties, zero `@layer` tokens across all eleven — so
the d1/d2 boundary and M9 hold by construction.

**Members 1 and 11 have byte-identical selector text.** No substring or presence check
can distinguish them, which is why every contract below is occurrence-count or
source-shape based, and why the census yields **ten** selector records for **eleven**
rule identities.

### Structural sweep (exact class token, repository-wide)

`scale-btn(?![-\w])`, excluding `node_modules/` and `artifacts/`:

| Location | Count | Nature |
|---|---:|---|
| `static/css/a11y.css` | **11** | the candidate family — the only CSS anywhere |
| `static/js/accessibility.js` `:144`, `:202` | 2 | `querySelectorAll` **queries** — evidence only, not modified |
| `tests/`, `docs/` | 9 | prose and one contract docstring |
| **`templates/**`** | **0** | — |

`templates/base.html:193,201` emits `class="scale-btn-compact"`. A CSS class selector
matches whole class **tokens**, so `.scale-btn` does not match `scale-btn-compact`; the
two families are independent in both directions.

---

## 2. Oracle validity gate — run and passed before anything was believed

`.claude/rules/verification.md`: *"A measurement script is not evidence until it has
passed a control."* Raw output, reported alongside the result as that file requires.

| Control | Requirement | Before deletion | After deletion |
|---|---|---|---|
| `.scale-control-compact` | must be LIVE | non-zero **1760/1760** | non-zero **1760/1760** |
| `.scale-btn-compact` | must be LIVE | non-zero **1760/1760** (max 2) | non-zero **1760/1760** (max 2) |
| `.scale-indicator` | must be LIVE | non-zero **1760/1760** | non-zero **1760/1760** |
| `[data-visual-scale-control]` | must be LIVE | non-zero **1760/1760** (max 3) | non-zero **1760/1760** (max 3) |
| known-dead class, natural | must be DEAD | **0** contexts | **0** contexts |
| known-dead class, injected | must become VISIBLE | **1** | **1** |
| same-CSS control | must be **0** differing | **0 / 97,600** | **0 / 97,600** |

**Gate: PASS on both sides.** The live controls passing *after* the deletion is the part
that matters: it distinguishes "the deleted rules went blind" from "the oracle stopped
working".

The injected known-dead control is deliberately two-sided. A probe that only shows a
dead class reporting dead cannot tell a working oracle from a blind one; requiring the
same class to become visible once injected closes that.

---

## 3. Natural full-selector census — taken before any synthetic existed

A rest-state differential **cannot falsify an unreachable rule** (binding method, `e`
and `d1`), so this carries the "nothing matches" half of the claim on its own.

Matrix: **11 routes × 2 themes × 10 widths × 8 `data-scale` levels = 1,760 contexts**,
plus print emulation ×22 and reduced motion ×22 = **1,804 total**. Widths 375, 576, 768,
769, 820, 991, 992, 1200, 1440, 1920 bracket both `a11y.css` breakpoints; `991` is the
largest integer viewport satisfying the **decimal** `max-width: 991.98px` and `992` the
smallest that does not.

| Selector | Census 0 | Non-zero | Max |
|---|---:|---:|---:|
| `.scale-btn` | **1804/1804** | 0 | 0 |
| `.scale-btn:hover` | **1804/1804** | 0 | 0 |
| `.scale-btn:focus` | **1804/1804** | 0 | 0 |
| `.scale-btn.active` | **1804/1804** | 0 | 0 |
| `.scale-btn.active:hover` | **1804/1804** | 0 | 0 |
| `.scale-btn[data-scale="1"]` … `"5"` | **1804/1804** each | 0 | 0 |

`data-scale` was set exactly as `accessibility.js:82`/`:89` set it — attribute plus the
inline `zoom` from the same ladder — not approximated.

**Read this table as one proof, not ten.** `querySelectorAll('.scale-btn:hover')` can only
be non-zero while a real pointer sits over a matching element, and the natural census runs
with no pointer, so the `:hover` and `:focus` rows are 0 partly by construction. The row
that carries the claim is bare **`.scale-btn`** — and since every other member requires a
`.scale-btn` bearer to exist before its own compound can match, that single row is
sufficient. The per-member work in §4 is what separates the members from each other.

---

## 4. Per-member certification

Each member was certified against a synthetic bearer and a control that **fails the
selector by exactly one compound**, reading properties derived from that member's own
declarations, with transitions suppressed before apply, read **and** removal (M6a) and
the Web Animations API settled — the CSS-only suppressor alone is beatable (d2).

Every sentinel was asserted to take effect **and** the page asserted back to zero
bearers afterwards.

| # | Sentinel | Bearer | Control | Took effect |
|---:|---|---|---|---|
| 1 | width / height / border-radius | `28px / 28px / 6px` | `1440px / 26.47px / 0px` | ✅ |
| 2 | background-color / color | hover values | rest values | ✅ |
| 3 | **outline-offset only** | `1px` | `0px` | ✅ |
| 4 | background-color / box-shadow | `rgb(0,102,204)` / shadow present | `rgba(0,0,0,0)` / `none` | ✅ |
| 5 | background-color | `rgb(0,85,170)` | `rgb(0,102,204)` | ✅ |
| 6 | font-size | `10.4px` | `12px` | ✅ |
| 7 | font-size | `11.2px` | `12px` | ✅ |
| 8 | font-size | `12px` | `12px` | ❌ **by design — see below** |
| 9 | font-size | `12.8px` | `12px` | ✅ |
| 10 | font-size | `13.6px` | `12px` | ✅ |
| 11 | flex-grow / flex-basis / max-width | `1 / 0% / 36px` | `0 / auto / none` | ✅ |

### 4a. Three members needed handling that a naive harness would have got wrong

**Member 3 — `outline` is unobservable, and that is evidence *for* deletion.**
`a11y.css:340` declares `*:focus { outline: none !important }` and `:401` declares
`*:focus-visible { outline-offset: 2px !important }`. `!important` beats specificity, so
member 3's non-important `outline: 2px solid var(--nav-accent)` **can never be the
computed owner on any element, bearer or not**. Only `outline-offset` is observable, and
only in a `:focus` that is *not* `:focus-visible` — reached with a real mouse click and
confirmed by reading the element's own `matches()`:

```
m3 .scale-btn:focus   bearer={'outline-offset': '1px'}  control={'outline-offset': '0px'}
   :focus=True  :focus-visible=False
```

Recorded as an instrumentation limit, never scored as "possibly reachable".
**The corollary matters more than the measurement:** deleting `.scale-btn:focus` cannot
remove a focus indicator from anything, because the keyboard-focus guarantee in this
bundle is owned by the class-agnostic `*:focus-visible` rule at `:401-415` and the
per-scale ladder at `:487-497` — never by the candidate.

**Member 4 — read with focus blurred.** `*.active:focus { box-shadow: none !important }`
zeroes the shadow if the bearer is still focused when `.active` is read.

**Member 8 — genuinely computed-blind.** `.scale-btn[data-scale="3"] { font-size: 0.75rem }`
is byte-identical to member 1's `font-size: 0.75rem`, so bearer and control both compute
`12px` and the "took effect" assertion passes **vacuously**. It certifies and flips by
**CDP source range alone** (block 174–176), which is stated rather than hidden.

**Member 11 — measured at ≤991px.** It is invisible at any wider viewport; probing it at
the harness default of 1440 would have reported it absent both before *and* after, which
is d1 defect #1 ("would have manufactured false deadness") in new clothing.

### 4b. Sentinels expect resolved tokens, not the dead fallbacks

`navbar.css:15-19` defines `--nav-accent: #0066cc`, `--nav-accent-hover: #0055aa`,
`--nav-surface-hover` and `--nav-text-muted` on `:root`, so the `var()` fallbacks written
into `a11y.css` (`#4f8cff`, `#6ba3ff`, `#1a202c`, `#a8b2c1`) **never render**. A probe
expecting the fallback literal would report "no effect" on a rule that applied perfectly.
Measured values are the resolved ones, and because `[data-theme="dark"]` does not
redefine either accent, members 4 and 5 stay separable (`#0066cc` vs `#0055aa`) in
**both** themes.

---

## 5. Post-deletion flip — stated by source identity

Not reported as "the rules went blind", which is indistinguishable from "the oracle
stopped working". Each member is named by the exact source range it occupied.

```
member  1 [dark ] .scale-btn                   before=1 @lines 128-143 after=0 FLIPPED
member  1 [light] .scale-btn                   before=1 @lines 128-143 after=0 FLIPPED
member  2 [dark ] .scale-btn:hover             before=1 @lines 145-148 after=0 FLIPPED
member  2 [light] .scale-btn:hover             before=1 @lines 145-148 after=0 FLIPPED
member  3 [dark ] .scale-btn:focus             before=1 @lines 150-153 after=0 FLIPPED
member  3 [light] .scale-btn:focus             before=1 @lines 150-153 after=0 FLIPPED
member  4 [dark ] .scale-btn.active            before=1 @lines 155-159 after=0 FLIPPED
member  4 [light] .scale-btn.active            before=1 @lines 155-159 after=0 FLIPPED
member  5 [dark ] .scale-btn.active:hover      before=1 @lines 161-163 after=0 FLIPPED
member  5 [light] .scale-btn.active:hover      before=1 @lines 161-163 after=0 FLIPPED
member  6 [dark ] .scale-btn[data-scale="1"]   before=1 @lines 166-168 after=0 FLIPPED
member  6 [light] .scale-btn[data-scale="1"]   before=1 @lines 166-168 after=0 FLIPPED
member  7 [dark ] .scale-btn[data-scale="2"]   before=1 @lines 170-172 after=0 FLIPPED
member  7 [light] .scale-btn[data-scale="2"]   before=1 @lines 170-172 after=0 FLIPPED
member  8 [dark ] .scale-btn[data-scale="3"]   before=1 @lines 174-176 after=0 FLIPPED
member  8 [light] .scale-btn[data-scale="3"]   before=1 @lines 174-176 after=0 FLIPPED
member  9 [dark ] .scale-btn[data-scale="4"]   before=1 @lines 178-180 after=0 FLIPPED
member  9 [light] .scale-btn[data-scale="4"]   before=1 @lines 178-180 after=0 FLIPPED
member 10 [dark ] .scale-btn[data-scale="5"]   before=1 @lines 182-184 after=0 FLIPPED
member 10 [light] .scale-btn[data-scale="5"]   before=1 @lines 182-184 after=0 FLIPPED
member 11 [dark ] .scale-btn                   before=1 @lines 312-315 after=0 FLIPPED
member 11 [light] .scale-btn                   before=1 @lines 312-315 after=0 FLIPPED

flipped 22/22 (members × themes)
after-run oracle validity : PASS
```

Reported **per theme**, because an earlier revision of the harness keyed the flip
records by member alone and the dark pass silently overwrote the light one — the verdict
would have proved a single theme while this document claimed both. Caught in code review;
the count is now members × themes and a CDP error can no longer be scored as a flip.

Unlike `d1` — where `.scale-control` legitimately survived inside a retained print rule
and the residual had to be attributed by declaration owner — **no residual exists here**.
After deletion the raw file contains **zero** exact-token `.scale-btn` occurrences and
**six** `.scale-btn-compact` occurrences.

### Rest-state differential

```
compared  : 339,120
differing : 0
```

Every element on 11 routes × 2 themes, 20 computed properties each. This is the evidence
that the deletion was neutral for **other** elements — that no brace-scoping or cascade
side effect landed elsewhere. It is paired with the census rather than substituted for
it, because a zero differential is *consistent with* deadness but cannot prove it.

---

## 6. What was retained

- **The live compact generation** — `.scale-control-compact`, `.scale-btn-compact` (6
  occurrences), `.scale-indicator`, `[data-visual-scale-control]`. Untouched and
  contract-pinned; it is also the oracle-validity control.
- **`static/js/accessibility.js`** — evidence only, not modified. Its two dormant queries
  survive. A new contract now asserts the module **constructs no DOM**, which is the
  premise the deletion rests on.
- **All 50 `!important` declarations, all 17 custom properties, `@layer` 0.**
- **The `@media (max-width: 991.98px)` shell**, retained empty with an explanatory
  comment. Member 11 was its last rule. Collapsing an at-rule is structural work, not
  deletion of dead declarations — the same call WP4.3j-b made for its five empty media
  shells. Verified to raise no Stylelint category: `.stylelintrc.json` enables neither
  `block-no-empty` nor `no-empty-source`.
- **The `@media print` `.scale-control, .accessibility-dropdown` rule**, untouched.

---

## 7. Contracts, with executed adversarial red paths

`tests/test_css_wp4_4_a11y_contracts.py` — **22 → 36 nodes** (the file had 16
*functions* before, two of them parametrized; the node count is the one the generated
inventory tracks, and hand-counting functions is exactly the drift blindspot
`docs/test_inventory/` exists to prevent). Red paths were executed, not asserted in
prose; the tree was restored after each and the whole file re-verified.

| Contract | What it locks | Adversarial red path |
|---|---|---|
| `test_legacy_scale_and_menu_generation_stays_deleted` | `scale-btn` added to `LEGACY_CLASSES`; the token is absent | restore the **`@media` override alone** — not the base rule |
| `test_the_emptied_breakpoint_block_holds_no_style_rule` | the shell exists and stays empty | any rule reappearing inside the 991.98px query |
| `test_accessibility_js_still_constructs_no_dom` | the deletion's premise | add `createElement` to `accessibility.js` |
| `test_legacy_generation_is_not_resurrected_by_a_sibling_surface` | widened from 5 hand-listed surfaces to a glob | add `.scale-btn {}` to **`motion.css`** — a surface the old tuple missed |
| `test_every_targeted_data_scale_level_still_has_rules` | the `--ui-scale` token ladder | rename the `html[data-scale="4"]` token block |

```
[PASS] occurrence count reds on the @media override ALONE (adversarial)
[PASS] emptied breakpoint shell reds when a rule reappears inside it
[PASS] legacy-class guard reds on the restored BASE rule
[PASS] sibling-surface guard reds on motion.css - a surface the old 5-tuple MISSED
[PASS] DOM-construction gate reds when accessibility.js gains a builder
[PASS] data-scale ladder reds when the html[data-scale='6'] block is deleted
whole contract file after restore: 37 passed
all 6 red paths proven
```

### The `data-scale` strengthening is measured, not claimed

The pre-existing assertion used an unanchored `[data-scale="N"]` substring satisfied by
**three** different families. Deleting the level-4 `--ui-scale` token block outright and
evaluating all three candidate forms against the mutated text:

```
original   `[data-scale="N"]`         -> missing=[]   GREEN (blind to it)
interim    `html[data-scale="N"]`     -> missing=[]   GREEN (blind to it)
shipped    `html[data-scale="N"] {`   -> missing=[4]  RED  (catches it)
```

The interim form — the obvious fix, and the one first written here — is **still blind**,
because the per-scale focus ladder also spells `html[data-scale="4"]`. Only requiring the
standalone declaration block separates the token ladder from the focus ladder. No
existing guarantee was weakened; this one was replaced by a strictly stronger structural
form, which is the only permitted direction.

---

## 8. Instrumentation defects found and corrected

Recorded because the packet's credibility rests on its controls, not its result. Both
were caught by a control failing, before any deletion.

| # | Defect | Symptom | Direction of error | Caught by |
|---|---|---|---|---|
| 1 | Same-CSS control compared the **light**-theme capture against the **dark**-theme one | 14,601 differing / 97,600 — reported as `rgb(26,26,46)` → `rgb(233,238,247)` | would have **invalidated a sound run** (or, if ignored, destroyed the run's credibility) | the control itself |
| 2 | The control element failed the selector by **two** compounds — no `scale-btn` token *and* a different `data-scale` — so `[data-scale]` members were read against the **inherited** value instead of against the base rule | member 9 reported `tookEffect=false` because `0.8rem` equals the inherited `12.8px` | would have **manufactured a false retention** for member 9 under criterion 6's abort rule | member 9 disagreeing with its siblings |

Defect 2 is the more instructive: the fix is exactly the method rule `e` paid for — *a
synthetic control must fail the selector by **exactly one** compound*. With the control
corrected to a `.scale-btn` minus only the attribute, member 9 reads `12.8px` against
`12px` and certifies, while member 8 remains genuinely blind. A single wrong control
would have retained the whole family for a reason that was not true.

The errors ran in both directions — one toward rejecting a sound result, one toward
retaining a dead rule — which is the argument that the controls, not the outcome, did the
work.

---

## 9. Gates

| Gate | Result |
|---|---|
| `tests/test_css_wp4_4_a11y_contracts.py` | **36 passed** (22 before) |
| Red-path proof | **6/6** go red under their own violation; tree restores to 36 passed |
| Full `pytest tests/` | **2,538 passed, 2 skipped** (448s) |
| Required Chromium specs + `visual-field-separator` | **174 passed, 1 failed** — pre-existing pollution, see §9b |
| Full seeded `visual.spec.ts` | **58 failed / 8 passed — IDENTICAL to the unmodified-CSS control.** Gate blocked repository-wide, see §9c |
| Seven-surface Stylelint | **2,759 → 2,752 (−7)**, **no category increased** |
| `a11y.css` Stylelint | **128 → 121 (−7)**; every other surface **+0** |
| Rest-state differential | **0 differing / 339,120** |
| Same-CSS control | **0 differing / 97,600**, both sides |
| Oracle validity | **PASS** both sides — live controls 1760/1760 after deletion |

### Stylelint attribution

| Rule | Before | After | Δ |
|---|---:|---:|---:|
| `declaration-property-value-disallowed-list` | 1,051 | 1,044 | **−7** |
| `declaration-no-important` | 1,219 | 1,219 | **0** |
| `no-descending-specificity` | 249 | 249 | 0 |
| `no-duplicate-selectors` | 21 | 21 | 0 |
| `selector-max-id` / `selector-max-specificity` | 115 / 101 | 115 / 101 | 0 |

`declaration-no-important` holding at 1,219 is independent confirmation that **no
re-weighting occurred** — this packet is pure deletion, and `d2`'s certified result of 50
annotations in `a11y.css` is untouched.

### 9a. A pre-existing contract that reds on any uncommitted CSS work

`tests/test_css_theme_dark_p3_audit_contracts.py::test_this_packet_wrote_no_production_css`
runs `git status --porcelain -- static/css` against the **working tree**. It therefore
fails for *any* packet that has edited a shared bundle and not yet committed, including
this one, and goes green once the change is committed. That is a property of the P3-a0
contract rather than a defect in this packet, and it is recorded here so the next CSS
packet does not spend time diagnosing it.

`test_every_committed_css_audit_tool_is_assessed` also reds on a **newly added** tool in
`scripts/css_audit/`, by design: *"a tool added without a verdict has to red rather than
quietly widen the scope."* Its designed remedy is a verdict row, which this packet added
for `scale_btn_census.mjs`. **No P3 packet is reopened; P3 remains terminated at a0.**

### 9b. The one functional failure is pre-existing combined-run pollution

The ten required Chromium specs returned **174 passed, 1 failed** —
`ui-hardening.spec.ts:375 full reload restores all six Workout Controls`. It is not this
packet's:

- it **passes in isolation** (1 passed), and its own spec run whole is **37/37 passed**;
- the same ten specs run against the **unmodified** `a11y.css` returned **170 passed, 5
  failed** — five *different* tests, all in `summary-pages.spec.ts` (Pattern Coverage).

Non-overlapping failure sets across two runs of identical-except-for-CSS trees is the
signature of cross-spec DB-state pollution, which `QUALITY_GATE.md:124` already records
for `program-backup.spec.ts:79`. The control failing **more** than the candidate settles
the direction.

### 9c. The Windows visual gate is blocked repository-wide, and it is not this packet

Run with `PW_VISUAL_SEED=1`, comparing against the committed `e2e/__screenshots__/win32`
baselines. **No snapshot was written; `--update-snapshots` was never passed; no
tolerance, mask or retry was touched.**

| Run | CSS | Result |
|---|---|---|
| control 1 | **unmodified** `a11y.css` | **58 failed / 8 passed** |
| control 2 | **unmodified**, identical rerun | **58 failed / 8 passed** |
| candidate | this packet's deletion | **58 failed / 8 passed** |

The passing sets were compared by name, not merely by count:

```
control passing: 8   mine passing: 8
passed in CONTROL but FAILED in mine: none
passed in MINE  but failed in control: none
```

**The two sets are identical.** The Windows baseline corpus is broadly stale against
current `main` — the same condition already documented for Linux in
`MASTER_HANDOVER.md` §"Known LINUX visual reds", where 84 committed PNGs fell behind 57
CSS/template commits. This packet neither caused it nor can fix it: rebaselining is an
owner action requiring a by-eye review of the regenerated corpus, and
`QUALITY_GATE.md` is explicit that a red is never resolved with `--update-snapshots`.

**One honest correction worth recording:** the packet's *first* visual run reported 60
failed / 6 passed, and it would have been easy to file that 2-test delta as a finding.
It was not reproducible — the control is stable at 58/8 across reruns, and a clean
candidate rerun matched it exactly. The first run of a fresh browser process differs
from every later one, which `scripts/css_audit/runtime_probe.mjs` documents directly
("capture 1 differed from capture 2, and captures 2..6 were byte-identical"). A single
visual run is not evidence in either direction.

The visual **merge** gate is therefore marked **BLOCKED**, with the blocker external to
this packet and its non-attribution demonstrated by control rather than asserted.

---

## 10. Surface accounting

| Metric | Before | After | Δ |
|---|---:|---:|---:|
| lines | 728 | 667 | **−61** |
| style rules | 89 | 78 | **−11** |
| declarations | 240 | 211 | **−29** |
| `!important` | 50 | 50 | **0** |
| custom-property declarations | 17 | 17 | **0** |
| `@layer` tokens | 0 | 0 | **0** |
| exact-token `.scale-btn` rules | 11 | **0** | −11 |
| `.scale-btn-compact` occurrences | 6 | 6 | 0 |

Diff: **10 insertions / 71 deletions**, one production file. The insertions are the single
retained-shell comment.

---

## 11. Preservation invariants

| Invariant | Verdict |
|---|---|
| **V1** no visual difference | Rest-state differential 0 / 339,120; same-CSS control 0 both sides. |
| **V2** no rebaseline | 0 changed paths under `e2e/__screenshots__/`; no tolerance, mask, retry, snapshot, `playwright.config.ts` or `e2e/visual-helpers.ts` change. |
| **V3** no re-weighting | `!important` **50 → 50**; `selector-max-id` +0; `selector-max-specificity` +0. |
| **V4** no duplication increase | `no-duplicate-selectors` 21 → 21. |
| **V5** contribution | −61 lines, −11 rules, −29 declarations. Scope was not widened to improve Stylelint totals — the whole −7 is attributable to the deleted declarations. |
| **V6** no conflict | Single writer, single production file. |
| **V7** accessibility preserved | The 8-level scale ladder, the `*:focus-visible` guarantees, the per-scale focus ladder, print and reduced-motion blocks are untouched and contract-pinned. The deleted family never owned any of them. |

---

## 12. Limitations, stated rather than smoothed over

1. **Member 8 is certified by CDP source range alone.** No computed-style read can
   separate `.scale-btn[data-scale="3"]` from the base rule, because both declare
   `font-size: 0.75rem`. Its census (0/1804), its CDP presence before and its CDP absence
   after are what carry it. Anyone re-deriving this by computed value will find nothing
   and should not read that as a gap.
2. **Member 3's `outline` was never observable**, before or after. Only `outline-offset`
   was. The rule was already inert for two of its three declared longhands while it
   existed.
3. **Chromium-only oracle.** All eleven sit *outside* the `@-moz-document url-prefix()`
   block at `a11y.css:92-121`, so Chromium is competent for them — unlike the eight
   annotations inside that block, which `d2` correctly refused to certify. Firefox is
   additionally moot here: `:107-109` hides `.scale-control-compact` outright, so Firefox
   renders no scale control at all.
4. **The pixel matrix cannot observe these rules in either direction**, and not because
   of the `[data-visual-scale-control]` blind-spot mask — that hook is on the *live*
   compact control. It is because **no document emits a `.scale-btn` bearer**, so there
   is nothing for a screenshot to contain. The visual gate is still meaningful here as a
   **collateral-damage** oracle: a mis-scoped brace swallowing `.accessibility-dropdown`
   or merging into the media block would be pixel-visible on every page.
5. **The census proves the class is unreachable *today*.** It is a statement about the
   current templates and JS, which is why the DOM-construction contract exists — to make
   a future re-introduction red rather than silent.

---

## 13. Discovered adjacent, deliberately not acted on

**The retained `@media print` rule is itself inert against current markup.**
`a11y.css:323-332` hides `.scale-control, .accessibility-dropdown` when printing. No
template emits either token — `base.html:190` emits `scale-control-compact`, and by the
exact-token rule `.scale-control` does not match it. So the live scale buttons currently
print. This is **pre-existing**, out of scope under this packet's constraints, and pinned
by two existing contracts. Recorded here rather than fixed, mirroring the d1 precedent
that created this packet — acting on it would be re-weighting a rule this packet has not
proved.

---

## 14. Reproducing this

```bash
node scripts/css_audit/scale_btn_census.mjs --out artifacts/scale_btn/before
#   … apply the deletion …
node scripts/css_audit/scale_btn_census.mjs --out artifacts/scale_btn/after
node scripts/css_audit/scale_btn_census.mjs --diff artifacts/scale_btn/before artifacts/scale_btn/after

python artifacts/scale_btn/redpath.py
python artifacts/scale_btn/strengthening_proof.py
node scripts/css_audit/stylelint_surfaces.mjs artifacts/scale_btn/stylelint_after.json
```

`scale_btn_census.mjs` is **committed** — the load-bearing evidence for a whole-family
deletion should be re-runnable by a reviewer, and the in-repo precedent
(`tests/test_css_audit_digest_normalization_contracts.py`) exists only because a packet
driver was committed and its CRLF-digest defect could therefore be caught. It adds a
sibling file and modifies none of the six shared packet-`a` tools. Set
`HT_PROBE_PYTHON` when running from a worktree without its own `.venv`.

Analysis output goes to the gitignored `artifacts/` tree.
