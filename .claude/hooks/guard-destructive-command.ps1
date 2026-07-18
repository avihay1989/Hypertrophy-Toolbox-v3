$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$command = [string]$inputJson.tool_input.command

$blockedPatterns = @(
    '(?i)\bgit\s+push\b',
    '(?i)\bgit\s+merge\b',
    '(?i)\bgit\s+reset\s+--hard\b',
    '(?i)\bgit\s+clean\s+-[^\s]*f',
    '(?i)(^|[;&|]\s*)rm\s+-[^\s]*r[^\s]*f',
    '(?i)\bRemove-Item\b[^\r\n]*\s-Recurse\b'
)

foreach ($pattern in $blockedPatterns) {
    if ($command -match $pattern) {
        Write-Error "Blocked destructive command by agent-local guard"
        exit 2
    }
}

exit 0
