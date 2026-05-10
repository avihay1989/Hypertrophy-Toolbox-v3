<#
.SYNOPSIS
    Create a git worktree with isolated SQLite state for parallel agent work.

.DESCRIPTION
    Each worktree gets its own data/database.db so concurrent SQLite WAL writes
    cannot corrupt the main checkout. See docs/ai_workflow/PARALLEL_WORKFLOW.md
    for the full rationale and `.claude/commands/worktree.md` for invocation tips.

.PARAMETER Task
    Short task slug. Becomes the worktree dir suffix and the branch suffix.
    Example: "fatigue-fix" -> ..\Hypertrophy-Toolbox-v3-fatigue-fix
             on branch wt/fatigue-fix.

.PARAMETER Seed
    DB seed mode:
      visual       (default) copy e2e/fixtures/database.visual.seed.db
      empty        leave data/database.db absent; app.py will initialize on launch
      copy-current copy the current checkout's data/database.db if it exists

.PARAMETER BranchPrefix
    Branch name prefix. Default 'wt/'. Pass '' to disable.

.PARAMETER OpenTerminal
    If set, opens a new Windows Terminal tab in the new worktree via wt.exe.

.EXAMPLE
    .\scripts\new-worktree.ps1 -Task fatigue-fix
    .\scripts\new-worktree.ps1 -Task experiment -Seed empty -OpenTerminal
#>
param(
    [Parameter(Mandatory = $true)]
    [string] $Task,

    [ValidateSet("visual", "empty", "copy-current")]
    [string] $Seed = "visual",

    [string] $BranchPrefix = "wt/",

    [switch] $OpenTerminal
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoName = Split-Path -Leaf $RepoRoot

$Slug = ($Task -replace '[^A-Za-z0-9._-]+', '-').Trim('-')
if (-not $Slug) {
    throw "Task slug is empty after sanitization. Pass -Task <something>."
}
if ($Slug -match '\.\.' -or $Slug.StartsWith('.')) {
    throw "Task slug '$Slug' must not contain '..' or start with '.' (path-traversal and invalid-ref safety)."
}

$WorktreePath = Join-Path (Split-Path -Parent $RepoRoot) ("$RepoName-$Slug")
$BranchName   = "$BranchPrefix$Slug"

if (Test-Path $WorktreePath) {
    throw "Worktree path already exists: $WorktreePath"
}

$null = git -C $RepoRoot rev-parse --verify --quiet HEAD 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Cannot resolve HEAD in $RepoRoot."
}

$null = git -C $RepoRoot check-ref-format --branch $BranchName 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Invalid branch name '$BranchName' (rejected by git check-ref-format). Pick a different -Task."
}

$null = git -C $RepoRoot rev-parse --verify --quiet "refs/heads/$BranchName" 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "Branch '$BranchName' already exists. Pass a different -Task or delete it first."
}

Write-Host "Source HEAD:"
git -C $RepoRoot log -1 --oneline
Write-Host ""
Write-Host "Creating worktree at $WorktreePath on new branch $BranchName ..."

git -C $RepoRoot worktree add -b $BranchName $WorktreePath HEAD
if ($LASTEXITCODE -ne 0) {
    throw "git worktree add failed (exit $LASTEXITCODE)."
}

$DataDir   = Join-Path $WorktreePath "data"
$BackupDir = Join-Path $DataDir "auto_backup"
New-Item -ItemType Directory -Force -Path $DataDir, $BackupDir | Out-Null

$TargetDb = Join-Path $DataDir "database.db"

# If data/database.db is tracked in this repo, `git worktree add` already wrote
# HEAD's copy at $TargetDb. Without --skip-worktree, seeding overwrites it and
# leaves the new worktree dirty, which blocks `git worktree remove` and makes
# the binary DB commit-bait. Mark it skip-worktree in the new worktree only.
$DbIsTracked = $false
$null = git -C $WorktreePath ls-files --error-unmatch "data/database.db" 2>$null
if ($LASTEXITCODE -eq 0) {
    $DbIsTracked = $true
    git -C $WorktreePath update-index --skip-worktree "data/database.db" | Out-Null
    Write-Host "data/database.db is tracked in this repo; applied --skip-worktree in the new worktree so seeding stays out of the index."
}

switch ($Seed) {
    "visual" {
        $Fixture = Join-Path $RepoRoot "e2e\fixtures\database.visual.seed.db"
        if (Test-Path $Fixture) {
            Copy-Item -LiteralPath $Fixture -Destination $TargetDb -Force
            Write-Host "Seeded $TargetDb from visual fixture."
        }
        else {
            $Fallback = if ($DbIsTracked) { "leaving the tracked HEAD copy in place" } else { "no DB present; app.py will initialize on first run" }
            Write-Warning "Visual fixture not found at $Fixture. $Fallback."
        }
    }
    "empty" {
        if (Test-Path $TargetDb) {
            Remove-Item -LiteralPath $TargetDb -Force
            Write-Host "Empty seed mode: removed checked-out $TargetDb. app.py will initialize on first run."
        }
        else {
            Write-Host "Empty seed mode: $TargetDb absent. app.py will initialize on first run."
        }
    }
    "copy-current" {
        $Source = Join-Path $RepoRoot "data\database.db"
        if (Test-Path $Source) {
            Copy-Item -LiteralPath $Source -Destination $TargetDb -Force
            Write-Host "Seeded $TargetDb by copying current checkout's data/database.db."
            Write-Warning "WAL/SHM sidecars were NOT copied. Stop the source app before relying on this seed."
        }
        else {
            $Fallback = if ($DbIsTracked) { "leaving the tracked HEAD copy in place" } else { "no DB present; app.py will initialize on first run" }
            Write-Warning "Source data/database.db not found at $Source. $Fallback."
        }
    }
}

Write-Host ""
Write-Host "Worktree ready: $WorktreePath"
Write-Host "  branch: $BranchName"
Write-Host "  seed:   $Seed"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. cd '$WorktreePath'"
Write-Host "  2. Provision a Python env. Either:"
Write-Host "       python -m venv .venv  (then pip install -r requirements.txt)"
Write-Host "     or symlink: New-Item -ItemType SymbolicLink -Path .venv -Target '$RepoRoot\.venv'"
Write-Host "  3. Read docs/ai_workflow/PARALLEL_WORKFLOW.md before parallel work."

if ($OpenTerminal) {
    $Wt = Get-Command wt.exe -ErrorAction SilentlyContinue
    if ($Wt) {
        Start-Process wt.exe -ArgumentList @("-w", "0", "nt", "-d", $WorktreePath) | Out-Null
        Write-Host "Opened new Windows Terminal tab in $WorktreePath."
    }
    else {
        Write-Warning "wt.exe not found on PATH; cannot open new terminal tab."
    }
}
