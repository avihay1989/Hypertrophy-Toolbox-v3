param(
    [Parameter(Mandatory = $true)]
    [string]$AllowedCsv
)

$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$skill = [string]$inputJson.tool_input.skill
$allowed = $AllowedCsv.Split(',') | ForEach-Object { $_.Trim().TrimStart('/') }

if (-not $skill -or $allowed -notcontains $skill.TrimStart('/')) {
    Write-Error "Blocked skill invocation: $skill"
    exit 2
}

exit 0
