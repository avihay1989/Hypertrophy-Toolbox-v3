---
name: run-hypertrophy-toolbox
description: Launch and stop the Hypertrophy Toolbox Flask app safely for runtime verification from the current checkout, with debug and the reloader forced off.
argument-hint: [optional flow to verify]
---

Run Hypertrophy Toolbox from the repository root.

1. Confirm port 5000 is free. Do not stop an unknown listener.
2. Record `git status --short` before launch. Treat `data/database.db`,
   `data/auto_backup/`, and `logs/**` as expected runtime-write surfaces; never
   stage or commit them.
3. Start this exact command with the Bash tool's `run_in_background: true`:

   ```text
   env FLASK_DEBUG=0 FLASK_USE_RELOADER=0 .venv/Scripts/python.exe app.py
   ```

   Do not wrap, redirect, or chain the command. The app uses this checkout's
   `data/database.db` through `utils.config.DB_FILE`.
4. Wait for `Running on http://127.0.0.1:5000` in task output. **Record the launched
   PID now** — the Flask process that owns port 5000 — and keep it for shutdown.
   Get it from the port itself, immediately after the server binds:

   ```powershell
   (Get-NetTCPConnection -LocalPort 5000 -State Listen).OwningProcess
   ```

   Drive the requested flow through Playwright MCP; do not substitute pytest, curl,
   or imports.
5. Use the agent-scoped Playwright server configured with `--output-mode stdout`.
   Capture evidence with accessibility snapshots, console/network output, or
   transcript-native screenshots without filenames. Do not save artifacts into
   the checkout.
6. Shut down. Stop the background task with `TaskStop`, then **verify the port
   regardless of what `TaskStop` reported**:

   ```powershell
   Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
   ```

   **`TaskStop` reporting "No task found with ID: ..." does NOT mean the server
   stopped.** The background-task handle can be reaped across a standby turn while
   the Flask process stays alive and bound to `127.0.0.1:5000`. Taking that error at
   face value leaves a stray listener that collides with the next Playwright
   `webServer` on port 5000. If no task is found, or the port is still LISTENING:

   - Confirm the listener's `OwningProcess` **is the PID you recorded at launch (step 4)**.
   - Terminate **only that PID**: `Stop-Process -Id <recorded-pid>`.
   - Re-check the port and confirm it is free.

   Never sweep port 5000, never kill a listener you did not launch, and never kill by
   image name (`python.exe`) — a PID you did not record is someone else's process, and
   the correct move is to report it, not to kill it. If the recorded PID is gone but
   the port is still held, stop and report the unknown listener as a finding.
7. Compare `git status --short` with the baseline. Report unexpected writes as
   findings.
