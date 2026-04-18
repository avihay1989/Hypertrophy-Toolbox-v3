---
description: Full verification gate — runs pytest then the Chromium E2E suite. Use before declaring a refactor done.
---

Step 1: pytest

!`.venv/Scripts/python.exe -m pytest tests/ -q`

Step 2: Playwright (only if pytest passed)

!`npx playwright test --project=chromium --reporter=line`

Report both results. Declare success only if both are green.
