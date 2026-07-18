$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$filePath = [string]$inputJson.tool_input.file_path

if (-not $filePath -or $filePath -notmatch '(?i)(^|[\\/])(tests|e2e)[\\/]') {
    Write-Error "Blocked: automation-qa may write only under tests/ or e2e/"
    exit 2
}

exit 0
