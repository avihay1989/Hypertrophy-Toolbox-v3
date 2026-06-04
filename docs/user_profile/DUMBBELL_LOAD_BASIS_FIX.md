# Profile estimator — dumbbell load-basis fix

## What this is

A bugfix in `utils/profile_estimator.py` (`_load_basis_factor`) that reconciles
**per-hand (dumbbell)** vs **total (barbell/machine)** load bases when the
estimator converts a reference lift into a working-weight suggestion.

Dumbbell loads — references in `DUMBBELL_LIFT_KEYS` and dumbbell-equipment
targets — are expressed **per hand**; everything else is a single total/system
load. The estimator math was otherwise unit-agnostic, so a total-load reference
fed into a per-hand target (or vice versa) came out ~2× wrong. The fix applies
the simple "two dumbbells = one barbell" model:

- per-hand reference → total target: **×2**
- total reference → per-hand target: **÷2**
- same-basis pairs: **×1.0** (no conversion)

A `Dumbbell load conversion` step is added to the estimate trace when the factor
is not 1.0. Example regression it fixes: Incline Dumbbell Press suggested
~71 kg/hand instead of ~36 kg/hand when the chain reference was a total-load
barbell/machine lift.

Scope: `utils/profile_estimator.py`, `tests/test_profile_estimator.py` (+4
cases for the conversion), and the test-count note in `CLAUDE.md`. This is
**separate** from the Learned Calibration MVP UI work (committed in
`feat(user-profile): add learned calibration controls and workout controls UI`).

## Verification

- **pytest** `tests/test_profile_estimator.py` → 95 passed.

## Relevant E2E status — the reds are pre-existing/environmental, NOT from this fix

Running the relevant Chromium specs (`e2e/user-profile.spec.ts`,
`e2e/workout-plan.spec.ts`) against the **live, runtime-dirty `data/database.db`**
shows 9 reds. A controlled A/B run (fresh Flask server each time so on-disk code
actually reloads — `PW_REUSE_SERVER` was *not* set) proves this fix introduces
none of them:

| Run | Code on disk | Result |
|---|---|---|
| A | with the dumbbell fix | **9 failed**, 49 passed |
| B | dumbbell fix `git stash`-ed away | **10 failed** (the same 9 + one `workout-plan.spec.ts:841` video-modal flake), 48 passed |

The fix removes zero failures and adds zero failures. Breakdown of the 9:

1. **`workout-plan.spec.ts:237`, `:256`** — `#muscleModeToggle` off-viewport at
   1280/1440 width. Documented pre-existing red (`e2e/CLAUDE.md`,
   `nav-dropdown.spec.ts:117` family). Unrelated to the estimator.
2. **`workout-plan.spec.ts:407`** ("show the math" expects `Cold-start 1RM`) and
   the six `user-profile.spec.ts` insights/coverage tests (`:475 :529 :562 :662
   :741 :812`) — driven by **DB pollution / real saved data** in the live DB.
   The cold-start tests assume *no* saved reference lifts, but the live DB holds
   real reference-lift rows (e.g. a `dumbbell_bench_press` 44 kg × 7), and the
   per-test setup only wipes a couple of named lifts. With saved lifts present,
   the estimator correctly takes the **saved-reference-lift** path instead of the
   cold-start path, so `toContainText('Cold-start 1RM')` and the
   population-only band assertions fail. This source-switch happens with or
   without the dumbbell fix (Run B confirms); the fix only *adds* the
   `Dumbbell load conversion` trace line on top of the already-switched path.

### Conclusion

The dumbbell load-basis fix is safe to commit/PR with respect to relevant E2E:
it changes no E2E outcome. The 9 reds are a pre-existing test-isolation weakness
against the live dirty DB (plus the known `#muscleModeToggle` reds) and should be
addressed separately — e.g. by running these specs against a seeded/clean DB or
by widening the per-test reference-lift reset — not as part of this fix.
