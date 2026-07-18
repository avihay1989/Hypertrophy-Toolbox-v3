$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$filePath = [string]$inputJson.tool_input.file_path

if (-not $filePath -or $filePath -notmatch '(?i)(^|[\\/])docs[\\/][^\\/]+[\\/]PLANNING\.md$') {
    Write-Error "Blocked: product-manager may write only docs/<feature>/PLANNING.md"
    exit 2
}

exit 0
