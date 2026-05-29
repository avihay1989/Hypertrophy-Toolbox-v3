<#
.SYNOPSIS
    Create or repair the Fatigue Stage 4 observer Windows Scheduled Task.

.DESCRIPTION
    Idempotent. Registers (or overwrites) the per-user daily task
    HypertrophyToolbox\FatigueStage4Observer pointing at
    scripts\run_fatigue_stage4_observer.bat. Safe to run repeatedly - re-running
    it simply re-creates the task with the same definition.

    It does NOT touch fatigue thresholds, scenarios, boundary tests, the
    calibration CSV, or the database. It only manages the scheduled task. The
    observer it schedules is itself strictly read-only.

    Windows limitations to be aware of (the health-check script reports when
    these bite):
      * Interactive-only: the task runs under your user account and needs a
        usable session at the scheduled time. If you are logged out it may not
        run; if the machine is asleep/off it is skipped (last result 0x800710E0).
      * Stop on battery: the default power settings stop the task on battery and
        do not start it on batteries. On a laptop unplugged at 20:00 it is skipped.
      * A skipped run is NOT a failure of the automation - re-run it any time with
        schtasks /Run /TN "HypertrophyToolbox\FatigueStage4Observer".

.PARAMETER DailyTime
    Daily start time, 24h HH:mm. Default 20:00.

.PARAMETER TaskName
    Full task path. Default: HypertrophyToolbox\FatigueStage4Observer.

.EXAMPLE
    .\scripts\install_fatigue_stage4_observer_task.ps1
    .\scripts\install_fatigue_stage4_observer_task.ps1 -DailyTime 21:30
#>
param(
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string] $DailyTime = "20:00",

    [string] $TaskName = "HypertrophyToolbox\FatigueStage4Observer"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot    = Resolve-Path (Join-Path $PSScriptRoot "..")
$ObserverBat = Join-Path $RepoRoot "scripts\run_fatigue_stage4_observer.bat"

if (-not (Test-Path $ObserverBat)) {
    throw "Wrapper not found: $ObserverBat. Refusing to install a task that points at nothing."
}

Write-Host "Installing scheduled task '$TaskName'" -ForegroundColor Cyan
Write-Host "  action    : $ObserverBat"
Write-Host "  schedule  : daily at $DailyTime"
Write-Host "  run as    : $env:USERNAME (interactive only)"

# schtasks /Create with /F overwrites an existing task, giving idempotency, and
# its default logon mode (interactive, current user) + power settings match the
# task this automation was originally registered with.
$create = schtasks /Create `
    /TN $TaskName `
    /TR "`"$ObserverBat`"" `
    /SC DAILY `
    /ST $DailyTime `
    /F 2>&1
$createExit = $LASTEXITCODE

$create | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }

if ($createExit -ne 0) {
    throw "schtasks /Create failed (exit $createExit). See output above."
}

Write-Host "`nTask registered. Current definition:" -ForegroundColor Green
schtasks /Query /TN $TaskName /FO LIST /V | Where-Object {
    $_ -match 'TaskName|Next Run Time|Status|Logon Mode|Task To Run|Schedule Type|Start Time|Scheduled Task State|Power Management'
} | ForEach-Object { Write-Host "  $_" }

Write-Host "`nVerify health any time with:" -ForegroundColor Cyan
Write-Host "  .\scripts\check_fatigue_stage4_automation.ps1" -ForegroundColor Yellow
Write-Host "Trigger a run now with:" -ForegroundColor Cyan
Write-Host "  schtasks /Run /TN `"$TaskName`"" -ForegroundColor Yellow
