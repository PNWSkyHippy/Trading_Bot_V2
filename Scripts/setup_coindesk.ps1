# setup_coindesk.ps1
# Sets COINDESK_API_KEY in Windows system environment and wires the
# CoinDesk MCP server into Claude Code settings.json

# Plaintext key — needed for OS env var and MCP server (they don't use Fernet)
# The encrypted version lives in config.py for the bot itself
$KEY = "b3a5e3849f8c96a01574bdb85c2daca50e7bb0c0c97a73d7fc7a9676fe6f23f8"
$SETTINGS = "$env:USERPROFILE\.claude\settings.json"

# 1. Set OS environment variable (persists across reboots)
[System.Environment]::SetEnvironmentVariable("COINDESK_API_KEY", $KEY, "User")
$env:COINDESK_API_KEY = $KEY
Write-Host "✓ COINDESK_API_KEY set in User environment"

# 2. Add MCP server to Claude Code settings.json
$settings = Get-Content $SETTINGS -Raw | ConvertFrom-Json

if (-not $settings.mcpServers) {
    $settings | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{}) -Force
}

$coindeskMcp = [PSCustomObject]@{
    command = "npx"
    args    = @("-y", "@coindesk/mcp-server")
    env     = [PSCustomObject]@{
        COINDESK_API_KEY = "`${COINDESK_API_KEY}"
    }
}

$settings.mcpServers | Add-Member -NotePropertyName "coindesk" -NotePropertyValue $coindeskMcp -Force

$settings | ConvertTo-Json -Depth 10 | Set-Content $SETTINGS -Encoding UTF8
Write-Host "✓ CoinDesk MCP added to Claude Code settings.json"
Write-Host ""
Write-Host "Done. Restart Claude Code for MCP to activate."
