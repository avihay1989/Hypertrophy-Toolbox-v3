# Council findings — verbatim

*`/council-plan` step 2 for [`PLANNING.md`](PLANNING.md). Three reviewers ran in parallel,
each reading Plan v1 cold, each given only the plan's location and its supporting context
paths. **Nothing below is summarized, trimmed, or paraphrased.** The response matrix in
`PLANNING.md` cites these by ID.*

Split into this sibling file for length only. Dispositions live in `PLANNING.md`.

---

## architecture-reviewer (agent `aea66cdbdf050ef44`)

**Verdict: Needs revision** — 2 blocking, 5 non-blocking, 1 nit.

> ## Scope note — the usual categories are vacuous, and I checked rather than assumed
>
> This packet touches no Python business logic, no `routes/`, no `utils/`, no `app.py`, no `tests/conftest.py`, no blueprint, no table, no JSON response shape, and no logger call site. Charter items 1–7 and 9 (module boundaries, registration triple, schema-creator wiring, `DatabaseHandler`, `success_response`/`error_response`, `get_logger`, `utils/__init__.py` re-exports) are therefore vacuous — no findings, and none invented.
>
> I also checked one adjacent category the plan does not address and found it clean: `static/css/a11y.css` is **hand-authored, not a build output**. The only SCSS sources are `scss/custom-bootstrap.scss`, `scss/_fatigue.scss`, `scss/pages/_workout_plan_volume_panel.scss` — none emits `a11y.css`. Editing it directly is correct and will not be overwritten by `npm run build:css`.
>
> Charter item 8 (shared-state coordination) **is** live, and the plan handles it correctly: `a11y.css` is declared as a shared surface, the packet-owned `tests/test_css_wp4_4_a11y_contracts.py` is explicitly distinguished from the shared `tests/test_css_cascade_contracts.py` (`PLANNING.md:139`, and the test file's own docstring at `tests/test_css_wp4_4_a11y_contracts.py:13-16`), and the `TEST_INVENTORY` overlap with PR #296 is escalated rather than resolved unilaterally (`PLANNING.md:357-364`). That is the discipline done right.
>
> The real risk lives in evidence-harness boundaries and in contract identity. Findings below.
>
> ---
>
> ### Finding 1 — `PLANNING.md:296` + `PLANNING.md:306-308`: the `scripts/css_audit/` boundary is drawn stricter than the owner drew it, and the stricter version makes the packet's central evidence unreproducible — BLOCKING
>
> The plan pins `scripts/css_audit/** — **unchanged** | Packet-a-owned (A11, C8)` and routes the probe to "a scratch driver under gitignored `artifacts/`, reusing `scripts/css_audit/runtime_probe.mjs` primitives."
>
> Three things falsify that as drawn:
>
> - **`runtime_probe.mjs` exports nothing.** It is a top-level script; `main().catch(...)` runs at module scope (`D:/development/Hypertrophy-Toolbox-v3-scale-btn/scripts/css_audit/runtime_probe.mjs:946-949`). An `import` from `artifacts/` would spawn Flask, launch Chromium, and execute the full 11-route × 2-theme matrix as a side effect. "Reusing primitives" can only mean copy-paste — i.e. forking the reviewed harness into uncommitted code.
> - **Its CLI cannot produce this packet's matrix anyway.** `const VIEWPORT = { width: 1440, height: 900 };` is hard-coded at `runtime_probe.mjs:58`, and the only flags are `--out` and `--routes` (`:99-107`). The plan's 10 widths × 8 `data-scale` levels × print × reduced-motion (`PLANNING.md:313-315`) is unreachable through it.
> - **The repo convention is the opposite of what the plan assumes.** Per-packet drivers are *committed* into that directory: `i_diff_computed.mjs`, `i_known_live_mutation.mjs`, `i_five_route_computed.mjs`, `j_shadow_certification.mjs`, `j_theme_differential.mjs`, `n4_regions_abc.mjs`, `p3_ceiling.py`, `visual_helper_band_proof.mjs`. `.claude/rules/verification.md:90-93` scopes the packet-`a` ownership claim to six *shared* tools only (`measure.py`, `specificity.py`, `resolution_check.py`, `runtime_probe.mjs`, `stylelint_surfaces.mjs`, `emit_baseline.py`) — a **new sibling file modifies none of them**.
>
> The owner constraint the plan quotes at `PLANNING.md:46-47` ends "*…using the committed `scripts/css_audit/` tools **and a narrowly scoped extension**.*" That clause is dropped when it is restated as C8 (`PLANNING.md:215`) and again as `unchanged` (`PLANNING.md:296`).
>
> **Risk:** the load-bearing evidence for a whole-family deletion is produced by gitignored code that no reviewer can re-run, that cannot carry a contract, and for which `.claude/rules/verification.md` does not even auto-load (its frontmatter `paths` are `scripts/css_audit/**/*.mjs`, not `artifacts/**`). The precedent for why this matters is in-repo: `tests/test_css_audit_digest_normalization_contracts.py` exists only because `j_known_live_mutation.mjs` shipped a CRLF-digest defect that was catchable *because the driver was committed*.
>
> **Fix:** commit the driver as a new file `scripts/css_audit/scale_btn_census.mjs` (adds nothing to the six packet-`a` tools, matches the `i_`/`j_`/`n4_`/`p3_` precedent, and is exactly the "narrowly scoped extension" the owner authorized), and change the Artifacts row from `unchanged` to `add one file; the six shared tools untouched`.
>
> ---
>
> ### Finding 2 — `PLANNING.md:316-320` vs `PLANNING.md:110-111`: step 5 enumerates nine of the eleven members, and the two it omits are the two the plan itself calls "the trap" — BLOCKING
>
> Step 5 says to "exercise `:hover`, `:focus`, `.active`, `.active:hover` and `[data-scale="1".."5"]`" on a synthetic bearer. That is members 2–10. **Members 1 and 11 — the two bare `.scale-btn` rules — are not in the list**, and they are the only two whose observability is not implied by another member's.
>
> Member 11 is worse than merely omitted. Its reachability carries a second necessary condition that is a property of the *probe*, not the app: the viewport must be ≤ 991.98px. Neither step 5 nor step 6 names a viewport; `runtime_probe.mjs:58` defaults to 1440. Under CDP, `CSS.getMatchedStylesForNode` returns matched rules — a rule inside a non-applying media query is simply not returned. So a synthetic-bearer certification run at 1440 reports member 11 absent **both before and after deletion**, which is precisely "oracle-blind."
>
> Acceptance criterion 6 (`PLANNING.md:110-111`) then fires: *"If any single member is oracle-blind or its flip is unprovable, the entire family is retained."* The plan as written routes itself to a mandatory no-op.
>
> This is d1's **defect #1** in new clothing (`docs/CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:320` — probing media-gated candidates at widths their block cannot apply to "would have manufactured **false deadness**"). The plan cites that defect in step 4 for the *census*; it does not carry it into steps 5–6 for the *certification and flip*.
>
> **Fix:** extend step 5 to name all eleven members with a per-member sentinel property, and require the member-11 apply/read/revert and the step-8 flip to be taken at a viewport ≤ 991px (d1 used 375/576/768/769/820/991).
>
> The sentinels are already unambiguous and the plan should just state them: member 11 uniquely declares `flex` and `max-width` (`static/css/a11y.css:313-314` → computed `flex-grow: 1`, `flex-basis: 0%`, `max-width: 36px`), and member 1 uniquely declares `width: 28px` / `height: 28px` / `border-radius: 6px` (`a11y.css:132-140`). Nothing else in the family declares any of those, so the two byte-identical selectors are separable by computed value alone.
>
> ---
>
> ### Finding 3 — `PLANNING.md:96` (criterion 2): "every one of the **eleven** selectors reports census 0" is not achievable as written — there are only ten distinct selector strings — NON-BLOCKING
>
> Members 1 and 11 share the selector text `.scale-btn`. A `querySelectorAll`-based full-selector census yields **ten** records, not eleven, and the record for `.scale-btn` is jointly owned. Criterion 2 promises an evidence shape the method cannot emit, which will read as a gap in the evidence document.
>
> d1 already solved this: its census table (`CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:114-129`) is keyed by **source line**, not selector, and carries duplicate selector text across rows (`.scale-control` at 126 and 387, `.scale-btn-group` at 142 and 393) with *different denominators* — 164/164 for unrestricted rules, 100/100 for media-gated ones (`:126-127`, explained at `:134-136`).
>
> **Fix:** restate criterion 2 as "each of the eleven **rule identities** reports census 0, keyed by source location; members 1 and 11 share one selector-level record, and member 11's denominator is the width-restricted subset" — and note explicitly that the census alone cannot separate 1 from 11, which is why Finding 2's per-member sentinels are the separating evidence.
>
> ---
>
> ### Finding 4 — `PLANNING.md:92` / `:222` / `:303`: "byte offset" is not the unit any tool in this repo emits, and the plan does not say which CDP range it pins — NON-BLOCKING
>
> The identity scheme (selector + LF-normalized byte offset + enclosing at-rule) is **adequate in principle**: for members 1 and 11 the enclosing at-rule alone already separates them (`—` vs `@media (max-width: 991.98px)`), and offset is a third independent discriminator. No other collision exists inside the family. I have no objection to the scheme.
>
> The objection is to the unit. CDP returns `SourceRange` as `{startLine, startColumn, endLine, endColumn}` — 0-based lines, UTF-16 columns — not byte offsets. d1's proven pin was a **source line range** ("declaration block at source lines **329–331**", `CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:255`), and d1 **defect #7** (`:326`) records the exact way this goes wrong: *"`style.range` is the **declaration-block** range, not the whole rule; the selector list spans lines 328–329 so the block opens at 1-based 329… An assertion of 327 failed spuriously."* A plan that says "byte offset" without naming `selectorList.range` vs `style.range` invites re-deriving that conversion and re-hitting defect #7.
>
> Second, unstated: the offsets are **revision-scoped**. Every member's offset ceases to exist at step 8 and every later rule's offset shifts. The step-8 flip statement must pin pre-deletion identities against the pre-deletion revision, and the contract file cannot use offsets at all. The plan half-implies this (contracts are "occurrence-count or source-shape", `:257`) but never says it.
>
> **Fix:** adopt d1's proven unit — 1-based source **line range** of the declaration block, with the newline-preserving stripper already in `tests/test_css_wp4_4_a11y_contracts.py:39-56` — name which CDP range is being read, and state that offsets/lines are pinned against the pre-deletion revision only.
>
> ---
>
> ### Finding 5 — `tests/test_css_wp4_4_a11y_contracts.py:390-397`: an existing assertion that already protects less than it claims, and that the two `data-scale` families make worse — NON-BLOCKING
>
> This is the "plausible-looking assertion that silently protects nothing" case, and it sits exactly on the `html[data-scale="N"]` vs `.scale-btn[data-scale="N"]` boundary the brief flagged:
>
> ```python
> missing = [n for n in range(1, 9) if f'[data-scale="{n}"]' not in css]
> ```
>
> The substring is unanchored, so it is satisfied by *any* of the three families that carry it: `html[data-scale="4"]` (`a11y.css:53`), `.scale-btn[data-scale="4"]` (`a11y.css:178`), and `html[data-scale="4"] *:focus` (`a11y.css:424`). Today, deleting the `html[data-scale="4"]` token block outright would leave this test **green** via the other two. That is already weaker than its docstring ("a11y.css targets data-scale 1..8").
>
> The packet does not break it — after deleting members 6–10, N=1..5 still resolve via `html[data-scale="N"]` at `a11y.css:24-61` and the focus ladder at `:421-497`, and N=6..8 via `:63-76`. So no existing guarantee is *weakened*. But the packet is the natural moment to fix it, and criterion 7 explicitly permits strengthening.
>
> **Fix:** anchor it to `html[data-scale="{n}"]`, which makes the two families textually non-confusable inside the contract file and removes the last place a reader could mistake the ladder guard for coverage of the deleted buttons.
>
> ---
>
> ### Finding 6 — `tests/test_css_wp4_4_a11y_contracts.py:426-428`: the sibling-surface resurrection guard covers 5 of the 7 audited surfaces — NON-BLOCKING
>
> ```python
> @pytest.mark.parametrize("surface", ["layout.css", "components.css", "navbar.css", "theme-dark.css", "base.css"])
> ```
>
> `scripts/css_audit/stylelint_surfaces.mjs:14-22` defines the seven shared surfaces as `motion, base, layout, components, navbar, theme-dark, a11y`; `docs/ai_workflow/QUALITY_GATE.md:32` names eight including `tokens`. The parametrize list omits **`motion.css`** and `tokens.css`, and all eleven `pages-*.css` bundles.
>
> If `scale-btn` is added to `LEGACY_CLASSES` (the obvious hook), it inherits that hole: a resurrected `.scale-btn` rule in `motion.css` or any page bundle would go undetected. The packet's own structural sweep is repository-wide (`PLANNING.md:261-269`) — I re-ran it and confirm the only other CSS hits are `static/css/navbar.css:1051`, `:1464`, `:1465`, all `.scale-btn-compact`, all correctly excluded by the `(?![\w-])` lookahead. So the *census* is complete and the *contract* is not.
>
> **Fix:** derive the surface list from `sorted((ROOT / "static" / "css").glob("*.css"))` minus `bootstrap.custom.min.css`, instead of a hand-written 5-tuple. Strictly a strengthening.
>
> ---
>
> ### Finding 7 — `PLANNING.md:276-283` / `:328`: the deletion's load-bearing premise has no contract, and the plan never names the contracts it will add — NON-BLOCKING
>
> The whole argument is the chain at `PLANNING.md:280-283`: no template emits the token → `accessibility.js` constructs no DOM → `querySelectorAll` at `:144`/`:202` returns empty → `classList.toggle('active', …)` at `:205` never runs. I verified every link (`static/js/accessibility.js:144`, `:202`, `:205`; no `createElement`/`innerHTML`/`insertAdjacentHTML`/`outerHTML` anywhere in that file; `templates/base.html:190-206` emits only `scale-btn-compact`).
>
> **Nothing in the contract file locks the DOM-construction half.** `test_legacy_classes_are_still_unreachable` (`:96-122`) inspects only `class="…"` attributes and `classList.add|toggle|replace('literal')`. It would not catch `el.className = 'scale-btn'`, `setAttribute('class', …)`, or a new `createElement` path added to `accessibility.js`. This is d1's **defect #5** — *"no contract asserted its two deleted rules stay deleted"* (`CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:324`) — in its premise form.
>
> Note that a contract asserting `accessibility.js` **stays inert** is not a modification of it, so C3 (`PLANNING.md:210`) is not in tension.
>
> Sequence step 9 (`PLANNING.md:328`) says only "Contracts + red paths" with no enumeration, which leaves this to implementation time.
>
> **Fix:** enumerate the new contracts in Plan v2, and include a DOM-construction gate on `static/js/accessibility.js`. One trap to name while you are there: do **not** hang `scale-btn` off `LIVE_GENERATION` — `test_live_compact_generation_is_still_rendered` (`:142-158`) iterates that dict and asserts `base.html` renders each key boundary-anchored, which `scale-btn` cannot satisfy.
>
> ---
>
> ### Finding 8 — `PLANNING.md:291` vs `static/css/a11y.css:309-318`: "the eleven blocks, atomically. Nothing else" leaves an empty at-rule behind — NIT
>
> Member 11 is the **only** rule inside `@media (max-width: 991.98px)`; lines 310-311 and 316-317 are already blank-line residue from d1's earlier deletions in that same block. Deleting member 11 leaves a literally empty `@media (max-width: 991.98px) { }` in a shared bundle.
>
> I checked whether this raises a Stylelint category: it does not. `.stylelintrc.json` enables `color-no-invalid-hex`, `declaration-block-no-duplicate-custom-properties`, `declaration-block-no-duplicate-properties`, `declaration-no-important`, `declaration-property-value-disallowed-list`, `no-descending-specificity`, `no-duplicate-selectors`, `property-no-unknown`, `selector-max-compound-selectors`, `selector-max-id`, `selector-max-specificity` — no `block-no-empty`, no `no-empty-source`. Criterion 8 is safe either way. (For the same reason a pure deletion cannot *raise* `no-descending-specificity` either: removing rules can only remove flagged pairs.)
>
> **Fix:** decide in Plan v2 whether the vestigial wrapper goes with the family, and adjust the "Nothing else" wording — which as written forbids removing it.
>
> ---
>
> ## Positive results in my areas — stated so they are not re-litigated
>
> **The "one family, no partial erosion" coupling argument is sound, and stronger than the plan argues it.** All eleven rules key off the single class token `scale-btn`; nine are compounds of it and member 11 is a media-scoped override of member 1 on the same token. Reachability of every member reduces to one existential fact — does any rendered element carry the class token `scale-btn`? Members 2–5 additionally require an interaction or JS-applied state on such an element and members 6–10 additionally require `data-scale` on it, both strictly narrower. So member 1's bearer is a **necessary condition** for all ten others, and partial deletion is incoherent in both directions: keeping member 1 alone leaves a base rule nothing can reach; deleting member 1 alone leaves overrides of a base that no longer exists. This is a stronger footing than the "matches the `.tbl-*` precedent" appeal at `PLANNING.md:165-168` — use it.
>
> **The rule-identity scheme over-determines the member-1/member-11 distinction.** Enclosing at-rule alone separates them; offset is a second discriminator; and the unique declared properties (`flex`/`max-width` vs `width`/`height`/`border-radius`) are a third that is independent of source-location bookkeeping. My objection is confined to the *unit* (Finding 4) and to the enumeration gap (Finding 2), not to the scheme.
>
> **No existing guarantee in the packet-owned test file is weakened by this deletion — verified by construction, not asserted.** I read `static/css/a11y.css:128-184` and `:312-315` line by line: the eleven blocks contain **zero `!important`**, **zero custom-property declarations**, **zero `@layer` tokens**, and no `-moz-` property. Therefore all eight count-based contracts are provably invariant: `!important == 50` (`:220-239`), custom properties `== 17` (`:410-423`), `.scale-control` occurrences `== 1` (`:165-200`), the `.scale-control, .accessibility-dropdown` mixed rule (`:203-217`), `scale-control-compact: 5` / `scale-btn-compact: 6` / `scale-indicator: 2` (`:125-139` — I recounted all three in the current file and they match), the `@-moz-document` 8-annotation block and the four `-moz-box-shadow` declarations (`:328-354`, all above line 121 and untouched), the `*:focus-visible` premise (`:357-387`), and `@layer` absence (`:400-407`). Criterion 7's "no existing guarantee weakened" is satisfiable — but note the corollary: **there is currently zero contract coverage of the eleven** (`scale-btn` appears in no other test file), so every guarantee this packet produces is net-new and Finding 7 is the whole of it.
>
> **No ordering or coupling hazard with the retained `@media print` rule.** `static/css/a11y.css:328-331` names `.scale-control` and `.accessibility-dropdown`; a class selector matches whole tokens, so no member of the family shares selector text with it. I recounted `\.scale-control(?![\w-])` in the current file: exactly one match, at `:328` — the five `.scale-control-compact` occurrences (`:107`, `:112`, `:117`, `:118`, `:224`) are excluded by the lookahead. Deleting `:128-184` and `:312-315` leaves that count at 1 and leaves the mixed-list regex at `tests/test_css_wp4_4_a11y_contracts.py:214` matching. Both print-rule contracts are unaffected.
>
> **The `html[data-scale="N"]` ladder is kept correctly separate in the plan's prose** — the family table at `PLANNING.md:244-248` names `.scale-btn[data-scale="N"]` unambiguously, and the ladder at `a11y.css:24-76` / `:421-497` is nowhere in scope. The confusion risk is not in the plan; it is in the existing test (Finding 5).
>
> ---
>
> **Verdict: Needs revision.** Two blocking findings (the `scripts/css_audit/` boundary, and the step-5 enumeration gap that routes the plan into its own mandatory-retention trigger); the rest are contract-hardening that the packet is the right owner for.

---

## test-strategist (agent `acedc9f907bb453f8`)

**Verdict: Needs revision** — 5 blocking (B1–B5), 10 non-blocking (N1–N10), 3 nits.

> ## Required gates
>
> **Change type: `static/css/**` → "CSS (static bundles)" → shared surfaces** ([`QUALITY_GATE.md:32`](D:/development/Hypertrophy-Toolbox-v3-scale-btn/docs/ai_workflow/QUALITY_GATE.md)). `a11y` is one of the eight named shared bundles, so the full shared-surface gate applies and the plan stage is Large. Plan v1 §"Expected gates" (PLANNING.md:335-353) reproduces that row correctly. Additions below.
>
> - **pytest**: full suite. `tests/test_css_wp4_4_a11y_contracts.py` (packet-owned, focused + red paths); `tests/test_css_cascade_contracts.py` and `tests/test_visual_selector_contracts.py` run inside the total and must be **explicitly declared unedited** — the plan names "the cascade contracts" generically and never commits to not editing the second file.
> - **e2e (Chromium)**: `smoke-navigation`, `nav-dropdown`, `accessibility`, `dark-mode`, `summary-pages`, `volume-progress`, `fatigue`, `fatigue-stage4-smokes`, `ui-hardening` — plan's list matches `QUALITY_GATE.md:32` exactly. **Add `e2e/visual-field-separator.spec.ts`**: per [`.claude/rules/testing.md:100`](D:/development/Hypertrophy-Toolbox-v3-scale-btn/.claude/rules/testing.md) it runs in the required functional gate and is a computed-style oracle over 7 shared surfaces — the only independent non-pixel check on a shared bundle.
> - **visual**: full `visual.spec.ts` with `PW_VISUAL_SEED=1`, no `--update-snapshots`. Pin the expected size (`QUALITY_GATE.md:32`: 66 tests per platform over 11 pages) so a short run is detectable.
> - **Stylelint**: `node scripts/css_audit/stylelint_surfaces.mjs`, seven surfaces, no category rise.
> - **Linux `visual-linux` deep gate**: plan's handling of the stale ledger is correct and correctly cites `QUALITY_GATE.md:39`.
> - **CI**: `Test Inventory Drift` (required), `pyright` measure-only (blocks net-new).
>
> **Missing from the plan entirely: the known-red register** (`QUALITY_GATE.md:121-126`). Two items must be pre-registered:
> - `nav-dropdown.spec.ts` is **explicitly no longer a known red** — "failures there should block navbar/theme changes." `a11y.css` styles navbar surfaces (`#navbar { zoom }` at a11y.css:85-87, `.scale-control-compact` at :107-120/:224). A nav-dropdown red must block, not be waived.
> - `e2e/program-backup.spec.ts:79` is the one live known flake. It is not in the 9-spec list, but Sequence step 11 (PLANNING.md:330) invokes `/verify-and-polish` = `/verify-suite` = **full** Chromium E2E (`QUALITY_GATE.md:85`), which will surface it. Plan v1 does not say which spec set is authoritative.
>
> ## Existing coverage — and the headline finding
>
> I checked every assertion in the repo that touches `a11y.css`. **Zero of them go red on the planned deletion.** The deletion is currently 100% ungated.
>
> | Existing assertion | Effect of deleting the eleven |
> |---|---|
> | `test_live_compact_generation_is_untouched` (contracts:125-139) | **No change.** Patterns are `\.scale-control-compact(?![\w-])` = 5 (a11y.css:107,112,117,118,224), `\.scale-btn-compact(?![\w-])` = 6 (:248,268,275,280,293,299), `\.scale-indicator(?![\w-])` = 2 (:230,286). The `-` in the lookahead class means no bare `.scale-btn` occurrence can match. Counts stay 5/6/2. Correct behaviour — it is the known-live control. Plan v2 should state this so nobody "adjusts" it. |
> | `test_every_targeted_data_scale_level_still_has_rules` (contracts:390-397) | **Stays green, and should.** `[data-scale="1".."5"]` survives at a11y.css:24-28, :38-61 and the focus ladder :421-497; 6–8 at :63-76. But it gates **nothing** about this change in either direction, and it is weak generally: levels 1–5 have three independent sources, so it stays green even if the `--ui-scale` token blocks were deleted. Do not cite it as coverage. |
> | `test_important_count_...d2_certified_result` (contracts:220-239) | Stays 50 — the eleven blocks (a11y.css:128-184, :309-318) carry zero `!important`. |
> | `test_no_custom_property_was_deleted` (contracts:410-423) | Stays 17 — the eleven only *consume* `var()`; the 17 declarations are a11y.css:11 plus :39-75. |
> | `test_deleted_scale_control_rules_stay_deleted_by_source_shape` (contracts:165-200) | Stays 1 — `\.scale-control(?![\w-])` excludes `-compact`. |
> | `test_focus_visible_contract_premise_is_preserved` (contracts:357-387), `tests/test_css_cascade_contracts.py:906` | Unaffected. |
> | `tests/test_visual_selector_contracts.py` | No `a11y` reference at all. |
> | `e2e/**` | No spec references `.scale-btn`; only `e2e/visual-helpers.ts:167` names `[data-visual-scale-control]`. |
>
> Plan line numbers (PLANNING.md:239-249) verify exactly against this worktree: a11y.css:128, 145, 150, 155, 161, 166, 170, 174, 178, 182, 312 = 11 exact-token occurrences.
>
> ---
>
> ## Blocking findings
>
> **B1 — `.scale-btn:focus` (member 3) cannot satisfy acceptance criterion 5, and criterion 6 then forces a spurious retain.**
> `static/css/a11y.css:340-398` declares `*:focus, *:active:focus, *.active:focus, button:focus, … { outline: none !important; box-shadow: none !important; }`. `!important` beats non-`!important` regardless of specificity, so member 3's `outline: 2px solid var(--nav-accent)` (a11y.css:151) **can never be the computed owner of outline-color/style/width on any focused element, bearer or not**. Only `outline-offset: 1px` (a11y.css:152) survives — and only when the element matches `:focus` but **not** `:focus-visible`, because a11y.css:401-415 declares `*:focus-visible { … outline-offset: 2px !important }`.
> Criterion 5 (PLANNING.md:104-107) requires "each sentinel is asserted to have **taken effect**". With `outline` as the sentinel that assertion is unsatisfiable, and criterion 6 (PLANNING.md:110-111, "if any single member is oracle-blind … the entire family is retained") converts an instrumentation artifact into a retain verdict. Plan v2 must pre-register: (a) `outline-offset` is member 3's **only** sentinel; (b) the observation requires a non-`:focus-visible` focus (mouse click, not bare `.focus()`); (c) member 3's `outline` triad is *already inert on a live bearer* — that is evidence **for** deletion and belongs in EVIDENCE.md, not a cause to abort.
>
> **B2 — `.scale-btn[data-scale="3"]` (member 8) is not discriminable by computed style.**
> Its `font-size: 0.75rem` (a11y.css:175) is byte-identical to member 1's `font-size: 0.75rem` (a11y.css:139). Computed font-size on a synthetic bearer is 12px whether or not member 8 exists, so criterion 5's "took effect" assertion passes **vacuously**. The post-deletion flip is equally unprovable: the family is deleted atomically, so the drop to inherited is attributable to member 1 alone. Sequence step 6 (CDP `CSS.getMatchedStylesForNode`, PLANNING.md:321-323) is the only oracle that separates them, but the plan motivates it by the *visual blind spot* and never binds it to per-member flip proof or to the step-8 post-deletion re-run. Plan v2 must state: member 8 certifies and flips by **CDP matched-rules source range only**, and CDP runs on **both** sides of the deletion. This is d1 §9 defects 4 and 5 recurring — duplicate text masking a distinct claim.
>
> **B3 — member 11's synthetic certification and flip have no declared viewport.**
> Member 11 is the only media-gated member (a11y.css:309-318, `@media (max-width: 991.98px)`, declaring `flex` and `max-width: 36px`). Sequence step 5 (PLANNING.md:316-320) enumerates `:hover`, `:focus`, `.active`, `.active:hover` and `[data-scale="1".."5"]` — **nine** members; members 1 and 11 are never named. Step 8 (PLANNING.md:324-325) states no width either. A synthetic probe at a default 1280/1440 viewport makes member 11 invisible, and "the harness reported nothing" is d1 §9 defect 1 verbatim ("would have manufactured **false deadness**"). Pre-register: bearer certification and post-deletion flip for member 11 run at ≤ 991px, sentinels `flex-grow` / `max-width`.
>
> **B4 — the rest-state differential is dropped, contrary to `verification.md:52-56`.**
> That rule requires "the sweep **and** a rest-state differential, each capable of falsifying the other, with the same-CSS control passing." Constraint M-b (PLANNING.md:218) is right that a differential cannot falsify an *unreachable* rule — but that is an argument for pairing, not for omission, and d1 actually ran it (`CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md` §7a: 64,961 owner records / 340,960 paint records, 0 and 2 differing). The plan's Sequence has no equivalent step; step 8's "re-run the oracle" is the candidate-inventory flip (d1 §7b), a different artifact. Without the differential nothing shows the deletion was **rest-state-neutral for other elements** — the only evidence that a brace-scoping or cascade side effect did not land elsewhere. Add it, or record an owner-approved deviation with the reason.
>
> **B5 — criterion 7 can be fully satisfied without any contract that gates this deletion.**
> PLANNING.md:112-114 requires only (a) new assertions go red and (b) no existing guarantee is weakened. Neither forces an assertion that distinguishes member 1 from member 11 — the trap the plan itself identifies at PLANNING.md:254-258 but never converts into a required contract. Combined with the table above (nothing currently reds), Plan v2 must specify the contract, not just promise "occurrence-count + source-shape contracts". Concretely and verified as mechanically safe here:
> - Add `"scale-btn"` to `LEGACY_CLASSES` (contracts:63-71). `\.scale-btn(?![\w-])` correctly excludes `.scale-btn-compact`; `templates/**` emits zero exact tokens; `accessibility.js` only does `classList.toggle('active', …)`; and none of the five sibling surfaces in `test_legacy_generation_is_not_resurrected_by_a_sibling_surface` (contracts:426-441) contains the token — I re-ran the sweep and `static/css/a11y.css` is the only CSS anywhere. So all three consuming tests stay well-formed.
> - Add an explicit `count(\.scale-btn(?![\w-])) == 0` **plus** a media-scoped assertion, so restoring member 11 alone reds.
>
> ## Non-blocking
>
> **N1 — visual gate: defensible, but justified for the wrong reason, and it *is* a real collateral oracle.** PLANNING.md:172-176 blames the `[data-visual-scale-control]` neutralization at `e2e/visual-helpers.ts:167-171`. That hook is on the **live compact** control. The bare family is invisible to pixels for a more basic reason: **no document emits a `.scale-btn` bearer**, so the matrix is structurally incapable of observing these eleven in either direction. State it that way — the plan's phrasing implies the mask is the obstacle, which invites someone to "fix" it (forbidden by C7). Conversely, the matrix **does** catch collateral damage (a mis-scoped brace swallowing `.accessibility-dropdown` at a11y.css:189, or merging into the media block) — that is pixel-visible on every page. No coverage hole for candidates; do not describe the gate as merely "reported".
>
> **N2 — the empty `@media (max-width: 991.98px)` wrapper.** Member 11 is its *only* rule (a11y.css:309-318; the stray blank lines at :310-311 and :316-317 are d1's residue from deleting the other rules in this block). Deleting member 11 leaves `@media (max-width: 991.98px) { }`. That is a twelfth edit not in the eleven-member table, against a packet whose C2 is "no partial erosion" and whose criterion 1 asserts "the count is exactly 11". Pre-register the ruling. **Verified: this is not a Stylelint risk** — `.stylelintrc.json` enables no `block-no-empty` and no `no-empty-source`; the enabled set is `color-no-invalid-hex`, the two `declaration-block-no-duplicate-*`, `declaration-no-important`, `declaration-property-value-disallowed-list`, `no-descending-specificity`, `no-duplicate-selectors`, `property-no-unknown`, `selector-max-*`. Deleting only removes violations from that set; criterion 8's "no category may rise" is safe either way.
>
> **N3 — `var()` fallbacks in the eleven are dead and must not be sentinel expectations.** `--nav-accent` (`#0066cc`), `--nav-accent-hover` (`#0055aa`), `--nav-surface-hover`, `--nav-text-muted` are all defined on `:root` in `static/css/navbar.css:15-19`, so the a11y.css fallbacks `#4f8cff`/`#6ba3ff`/`#1a202c`/`#a8b2c1` never render. A probe expecting the fallback literal reports "no effect" on a rule that applied perfectly. Also: `navbar.css:64-76` (`[data-theme='dark']`) does **not** redefine `--nav-accent`/`--nav-accent-hover`, so members 4 and 5 remain distinguishable (#0066cc vs #0055aa) in **both** themes — member 5 is certifiable, but only against resolved tokens. Pre-register expected resolved values per theme.
>
> **N4 — root `zoom` vs computed lengths.** a11y.css:36 records "zoom is applied via inline style", and the matrix crosses widths × data-scale 1–8. Chromium's reported computed lengths under root `zoom` are not stable across scale levels, so px sentinels (`width: 28px`, `max-width: 36px`, `font-size`) must be compared **within** a data-scale level, never across.
>
> **N5 — the widths ARE right; two caveats.** a11y.css has exactly two width breakpoints: `max-width: 991.98px` (:309) and `max-width: 768px` (:715). The plan's list (375, 576, 768, 769, 820, 991, 992, 1200, 1440, 1920 — PLANNING.md:314-315, inherited verbatim from d1 §4) brackets both correctly; 991 is the largest integer viewport satisfying 991.98 and 992 the smallest that does not. **No finding on the widths.** Caveats: (a) the 768px block gates **no** `.scale-btn` member — it gates only `.error-page-content h1` and `.global-loading-indicator` (a11y.css:715-728), so 768/769 are same-CSS-control ballast here, not candidate brackets; don't present them as bracketing a candidate. (b) `@-moz-document url-prefix()` (a11y.css:92-121) is never parsed by Chromium — and **four of the five `.scale-control-compact` occurrences live inside it** (:107, :112, :117, :118). As a **DOM census** control (criterion 3) that is fine. If step 6's CDP declaration-owner pass is also applied to the controls, the asymmetry must be pre-registered or a correct run will falsely invalidate. Pre-register which oracle each of the four controls validates — `[data-visual-scale-control]` in particular is a DOM/template hook, not necessarily an author rule in any static bundle.
>
> **N6 — reduced motion is a free cross-check on M-e.** `navbar.css:79-83` sets `--nav-transition-fast: 0ms` under `prefers-reduced-motion: reduce`, and member 1 declares `transition: all var(--nav-transition-fast, 150ms) ease` (a11y.css:142). Under reduced-motion emulation the lag `verification.md:66-73` warns about is 0. Running the sentinel pass under both motion conditions makes any disagreement a genuine instrumentation signal.
>
> **N7 — `Test Inventory Drift`: handling is correct, wording invites the blindspot it cites.** PLANNING.md:141-142/295/331-332/357-364 correctly treats it as required (`QUALITY_GATE.md:114-119`), regenerates after rebase (right order), and escalates the PR #296 overlap. But "regenerate **iff** test-node counts change" invites a hand-count — exactly blindspot B3 that `.claude/rules/testing.md:24` warns about. Decide with `.venv/Scripts/python.exe scripts/generate_test_inventory.py --check` (testing.md:17-20) after the last test edit **and** after the rebase. Note also that `.claude/rules/testing.md:22` still calls the job `Test Inventory Drift (non-required)` — stale; `QUALITY_GATE.md` is canonical, and an implementer following the rule file would skip regeneration.
>
> **N8 — red-path specification is too thin.** "Every new assertion has an executed red path" (PLANNING.md:112-113) needs three additions to match d1's actual standard (`D1 evidence:352`, "15/15 go red under their own violation; tree restores to 16 passed"): (a) the mutation must be the **adversarial** one — for the `.scale-btn == 0` contract, restore **member 11 alone** (the `@media` occurrence); restoring member 1 proves nothing about the assertion's ability to distinguish them; (b) the tree must be restored and the full file re-verified green, recorded — a red-path proof that mutates `static/css/a11y.css` and forgets to restore ships a second unaudited edit in a pure-deletion packet; (c) raw output per path.
>
> **N9 — the pre-council sweep table (PLANNING.md:263-270) omits `tests/**`.** `tests/test_css_wp4_4_a11y_contracts.py:102` carries the exact token in a docstring ("`accessibility.js` queries `.accessibility-dropdown` and `.scale-btn[data-scale]`, and both resolve to empty sets at runtime") — that premise reference goes stale after deletion. My re-run in this worktree also returns docs hits across five files (`ACTIVE_DEVELOPMENT.md`, `CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md`, `LEFTOVERS_BY_PRIORITY.md`, `MASTER_HANDOVER.md`, `REFACTOR_PLAN.md`), not the stated "8". Re-derive at execution rather than carrying the pre-council number.
>
> **N10 — internal inconsistency on the E2E set.** §"Expected gates" names 9 specs; Sequence step 11 runs `/verify-and-polish` = full Chromium E2E. Declare which is authoritative and pre-register known-red dispositions for the larger set.
>
> ## Nits
>
> - Pin the expected visual matrix size (66 / 11 pages) so a short run is detectable.
> - Criterion 7 scopes "no existing guarantee weakened" to the packet-owned file only; extend the commitment to "neither `tests/test_css_cascade_contracts.py` nor `tests/test_visual_selector_contracts.py` is edited" per `QUALITY_GATE.md:32`.
> - PLANNING.md:234's line pins verify exactly against this worktree — no action.
>
> ## Conftest / fixture work
>
> **None.** No blueprint, table, route or response shape is touched (PLANNING.md:124-132 is accurate); `tests/conftest.py` needs no change and `erase_data()` is unaffected. Plan v2 should state this explicitly rather than leave it inferred.
>
> ## Verdict
>
> **Full shared-surface gate required, and Plan v1's derived gate list is correct** — with the additions in §Required gates (known-red register, `visual-field-separator.spec.ts`, explicit no-edit on both shared contract files, explicit "no conftest change", authoritative E2E set).
>
> **Plan v1 is not yet implementable as an evidence design.** Five blocking findings: three members (3, 8, 11) cannot be certified or flipped by the oracle the plan specifies (B1–B3), the rest-state differential `verification.md:52-56` requires is absent (B4), and criterion 7 as written can be fully satisfied while leaving the deletion ungated — because **no existing assertion in the repo goes red on it** (B5). B1 and B3 in particular would drive a *retain* verdict for instrumentation reasons under criterion 6's abort rule, producing a technically-successful no-op that answers nothing.

---

## product-risk-reviewer (agent `ae163873105ea9679`)

**Verdict: Needs revision** — 2 blocking, 4 non-blocking. No product-invariant, non-goal,
terminology or calculation violation found.

> ## Scope check first — the vacuous categories, stated plainly
>
> I verified these rather than assuming them, and all four are genuinely empty for this packet:
>
> - **Calculation semantics — vacuous.** The packet's production write set is one CSS file. No Python, route, response shape, DB table or template logic is touched. `utils/effective_sets.py`, `utils/weekly_summary.py`, `utils/session_summary.py`, `utils/progression_plan.py`, `utils/volume_*.py`, `utils/fatigue*.py` are all untouched, and the `CountingMode` / `ContributionMode` / RIR / RPE surfaces are not read. Plan §"Calculation surface" `none` is correct as written.
> - **Local-first / non-goals — clean.** No auth, no remote endpoint, no sync, no telemetry. The only persistence anywhere in the blast radius is `localStorage['ui-scale-level']` plus a same-origin `ui-scale-level` cookie written at `D:/development/Hypertrophy-Toolbox-v3-scale-btn/static/js/accessibility.js:46` and `:70`, both local-only and both protected by C3.
> - **Terminology — vacuous.** Zero user-facing strings change. The strings in the blast radius (`aria-label="UI Scale Control"`, `"Decrease text size"`, `"Increase text size"` at `D:/development/Hypertrophy-Toolbox-v3-scale-btn/templates/base.html:190-205`) are untouched, and none is in the CLAUDE.md §1 canonical vocabulary.
> - **Workflows / backup — untouched.** No nav change, no page layout change, no schema change, so existing `program_backup` snapshots stay restorable by construction.
>
> **On "could user data ever inject the `scale-btn` token" — no, and this is provable, not assumed.** Every dynamic class token emitted by any template comes from a closed server-side enumeration with a fixed prefix: `utils/volume_classifier.py:9-23` (`_VOLUME_TIERS`), `utils/workout_log.py:62-88` (hardcoded `text-*`), and `fatigue-{band}` from a normalized band. The repository has exactly two `| safe` filters — `templates/workout_log.html:99` (revalidated through `safe_media_path`) and `templates/user_profile.html:394`, whose `card_label` is a template-literal loop constant at `:387-390`, not user data. Neither writes a class attribute. No route, no restored backup, and no logged program can put an arbitrary token on an element. The plan's structural claim is sound; it is just under-argued, since it rests on a template/JS grep rather than on this closed-enumeration argument.
>
> I also re-derived the eleven line numbers against this worktree: `static/css/a11y.css:128,145,150,155,161,166,170,174,178,182` and `:312` inside `@media (max-width: 991.98px)`. Accurate, zero `!important`, zero custom properties. The out-of-scope live generation is at `:224-304`, and `templates/base.html:193,201` emits only `scale-btn-compact`.
>
> ---
>
> ## Findings
>
> **Plan v1 §Sequence step 5 + Acceptance criterion 5 — member 3 (`.scale-btn:focus`) has no observable declared property under the harness as specified, so the plan cannot satisfy its own criterion.**
>   Severity: **blocking** (on plan text, not on product safety).
>   Invariant at risk: CLAUDE.md §1 Refactor invariant (coverage half) + the plan's own criterion 6, "if any single member is oracle-blind or its flip is unprovable, the entire family is retained."
>   The plan says each rule's sentinel must be read from "properties derived from each rule's own declarations." Member 3 declares only `outline` and `outline-offset` (`static/css/a11y.css:150-153`), and both are stolen later **in the same file**: `*:focus { outline: none !important; box-shadow: none !important }` (`:340`, declarations at `:396-397`) and `*:focus-visible { outline: 2px solid rgba(13,110,253,0.5) !important; outline-offset: 2px !important }` (`:401`, `:412-413`). `!important` beats specificity, so on a synthetic bearer `outline` is unreadable in every focus state, and `outline-offset` is readable **only** in a `:focus`-that-is-not-`:focus-visible` state — which is exactly the state Chromium's programmatic-`.focus()` heuristics make non-deterministic. The same trap hits member 4: `.scale-btn.active { box-shadow }` (`:155-159`) is zeroed by `*.active:focus` (`:342`, `:397`) if the bearer is still focused when `.active` is read in the same run.
>   Risk: a genuinely-dead family is recorded as "certification failed" for an instrumentation reason, the packet closes as a no-op, and the durable EVIDENCE doc tells the next owner the family "could not be certified" — freezing it permanently. Direction of error is toward retention, so no user regression; the cost is a wrong durable verdict. This is the same defect class as d1's own defects #1 and #2 (`docs/CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:320-321`, "would have manufactured false deadness"), recurring in mirror image.
>   Fix: pin, in Plan v2, the sentinel property and focus state for each of members 3 and 4 — read member 3 via `outline-offset` with the bearer explicitly asserted to match `:focus` and **not** `:focus-visible`, and read member 4's `box-shadow` with focus explicitly blurred — and record `*:focus` / `*:focus-visible` as the acknowledged later `!important` owners so that "property not observable" is never scored as "possibly reachable."
>   Note this is also the packet's **strongest affirmative safety argument**, and the plan omits it entirely: deleting `.scale-btn:focus` cannot remove a focus indicator from any element under any condition, because the keyboard-focus guarantee in this bundle is owned by the class-agnostic `*:focus-visible` rule at `:401-415` (and the per-scale ladder at `:487-497`), never by the candidate. Put that sentence in EVIDENCE §accessibility.
>
> **Plan v1 §Out of scope (`accessibility.js`) + §Artifacts (contracts) — deleting the styling while retaining the two live JS queries leaves the pressed-state affordance ungated.**
>   Severity: **blocking**.
>   Invariant at risk: CLAUDE.md §1 Refactor invariant, "updated test coverage" for a behavior-affecting deletion; and the a11y guarantees `docs/CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:292-306` obliges this bundle to preserve.
>   `static/js/accessibility.js:202-207` does more than query — it toggles `.active` **and** sets `aria-pressed` on whatever it finds. After deletion, a future re-add of `class="scale-btn" data-scale="N"` markup yields buttons that announce `aria-pressed="true"` to assistive technology with **no visual pressed state at all**: the background, colour and box-shadow that conveyed it live only in members 1/4/5, which this packet removes. Keyboard focus would survive (global `*:focus-visible`), but the state indication would not — a state conveyed to AT and to nobody else. C3 correctly forbids touching the JS; it does not address the coherence gap the retention creates.
>   Risk: a silent, sighted-user-invisible accessibility regression introduced by someone who reasonably assumes the JS handler implies working styling.
>   Fix: add the `scale-btn` token to `LEGACY_CLASSES` in `tests/test_css_wp4_4_a11y_contracts.py:63-71`, which activates the existing reachability guard at `:96-122` unmodified — its `class="..."` token split and `classList.(add|toggle|replace)` matcher will not false-positive on `scale-btn-compact` or on the retained `classList.toggle('active', …)`, and the `(?![\w-])` boundary in `:89` and `:438` protects `.scale-btn-compact` in `a11y.css` and `navbar.css:1051,1464` — and word the failure message to say "the JS handler at accessibility.js:144/202 survives but its styling does not; re-run the census, do not re-add the rules."
>
> **Plan v1 §Expected gates — the Chromium-only oracle's competence over these eleven is never stated, in the one bundle that contains a Firefox-only block.**
>   Severity: non-blocking.
>   Invariant at risk: the precedent already encoded in `tests/test_css_wp4_4_a11y_contracts.py:328-345` — "Chromium cannot see this block, so the oracle can never certify it… unmeasurable is not dead."
>   `static/css/a11y.css:92-121` is `@-moz-document url-prefix()`, and `:107-109` hides `.scale-control-compact` outright, so Firefox users have **no** scale control at all. The eleven candidates sit outside that block (`:128-184`, `:312`), so a Chromium oracle *is* competent for them — but the plan never says so, leaving a reviewer to wonder whether this packet is repeating the situation that test was written to prevent.
>   Fix: add one line to Plan v2 §Expected gates and to EVIDENCE stating that all eleven are outside `@-moz-document`, that Firefox renders no scale control at all, and that deleting non-Firefox-gated dead CSS cannot alter the Firefox path.
>
> **Plan v1 §Out of scope (`@media print`) — the retained print rule is itself inert against current markup; the census will see this, and the packet needs a stated non-action.**
>   Severity: non-blocking (observation, do not act).
>   `static/css/a11y.css:323-332` hides `.scale-control, .accessibility-dropdown` when printing. No template emits either token — `templates/base.html:190` emits `scale-control-compact`, and by the exact token rule the plan itself invokes at §Structural finding, `.scale-control` does not match it. So the live scale buttons currently print. This is pre-existing, correctly out of scope under C1/C7, and pinned by `test_mixed_selector_lists_kept_their_dead_branch` — but step 4 runs print emulation and will observe it.
>   Fix: record it in EVIDENCE as a discovered-adjacent gap with an explicit "not acted on, needs its own packet," mirroring the d1 precedent (`docs/CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md:445`) that created this packet in the first place — and do not let it grow the diff.
>
> **Plan v1 §Acceptance criterion 9 / Assumption 4 — "a no-op retention is success" collapses three very different retention causes into one verdict.**
>   Severity: non-blocking.
>   The framing itself is product-defensible: the asymmetry is real (a wrong deletion breaks an accessibility control; a wrong retention costs ~57 lines of inert CSS in a shared bundle). It does **not** let the packet dodge a real problem, provided the verdict distinguishes: (a) a member is genuinely **reachable** — a real product finding that must be reported loudly and reopens the markup/JS question; (b) a member is unreachable but its declared property is owned by a later `!important` rule — an instrumentation limitation, which is where finding 1 lands; (c) oracle or harness failure — re-run, do not record a verdict. Criterion 9 currently reads "a durable audit recording why the family remains," which permits (b) to be filed as if it were (a).
>   Fix: split criterion 9's retention branch into those three named causes and require the EVIDENCE verdict to name which one applies per member.
>
> **Plan v1 §Sequence step 12 — the rebase onto `main` happens after the full gate, inverting a recorded owner lesson.**
>   Severity: non-blocking.
>   Invariant at risk: user memory `feedback_verify_on_rebased_main` — "two green sibling PRs broke main; verify on a base rebased onto main." Steps 10-11 run the full shared-surface gate and `/verify-and-polish`, and only step 12 rebases. Combined with the `TEST_INVENTORY` overlap against PR #296 that the plan already escalates in §Conflicts, the gate would be certifying a base that no longer exists at merge time.
>   Fix: rebase onto current `main` **before** step 10, and re-run only the inventory regeneration as the final step.
>
> ---
>
> **Verdict: Needs revision** — no product-invariant, non-goal, terminology or calculation violation; two blocking gaps in the plan's own certification and contract design, both fixable in Plan v2 text.
