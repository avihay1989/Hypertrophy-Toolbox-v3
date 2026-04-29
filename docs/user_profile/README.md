# User Profile Feature

Personalizes Workout Controls on `/workout_plan` from a saved profile:

- Demographics, reference lifts, and rep-range preferences live in `user_profile`, `user_profile_lifts`, and `user_profile_preferences`.
- Estimation logic lives in `utils/profile_estimator.py`.
- HTTP endpoints and `/user_profile` live in `routes/user_profile.py`.
- Frontend page code lives in `templates/user_profile.html`, `static/js/modules/user-profile.js`, and `static/css/pages-user-profile.css`.

Reference docs:

- [Design constants](DESIGN.md) — v1 spec; see banner at top for current-state guidance.
- [Development issues](development_issues.md) — live tracker for post-v1 bugs / UX gaps / enhancements (Issues #1–#24).
- Archive: [Planning](archive/PLANNING.md) and [Execution log](archive/EXECUTION_LOG.md) — frozen historical artefacts from the v1 build (2026-04-26).
