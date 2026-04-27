# User Profile Feature

Personalizes Workout Controls on `/workout_plan` from a saved profile:

- Demographics, reference lifts, and rep-range preferences live in `user_profile`, `user_profile_lifts`, and `user_profile_preferences`.
- Estimation logic lives in `utils/profile_estimator.py`.
- HTTP endpoints and `/user_profile` live in `routes/user_profile.py`.
- Frontend page code lives in `templates/user_profile.html`, `static/js/modules/user-profile.js`, and `static/css/pages-user-profile.css`.

Reference docs:

- [Planning](PLANNING.md)
- [Design constants](DESIGN.md)
- [Execution log](EXECUTION_LOG.md)
