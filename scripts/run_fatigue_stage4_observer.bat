@echo off
REM Fatigue Meter Stage 4 calibration observer - scheduled wrapper.
REM Read-only; writes the latest human-readable digest (observe + analyze) to
REM logs\fatigue_stage4_latest.txt and appends logged-side pending rows to
REM docs\fatigue_meter\stage4_calibration_log.csv (gitignored - personal labels).
REM Registered as a per-user Windows Scheduled Task (see scripts header / handover).
cd /d "%~dp0.."
".venv\Scripts\python.exe" "scripts\fatigue_stage4_observer.py" > "logs\fatigue_stage4_latest.txt" 2>&1
".venv\Scripts\python.exe" "scripts\fatigue_stage4_observer.py" --analyze >> "logs\fatigue_stage4_latest.txt" 2>&1
