# =============================================================
#  query_trend_filter.ps1
#  Shows every trend_confirm advisory result joined to the
#  actual trade outcome (if the signal was executed).
#
#  Since trend_confirm logs BEFORE execution (no trade_id),
#  the join matches by symbol + nearest entry_time within 90s.
#
#  USAGE:
#    .\Scripts\query_trend_filter.ps1               # all results
#    .\Scripts\query_trend_filter.ps1 -Decision BLOCK   # only blocks
#    .\Scripts\query_trend_filter.ps1 -Symbol BTC/USD
#    .\Scripts\query_trend_filter.ps1 -Days 3
# =============================================================

param(
    [string]$Decision = "",        # BLOCK, APPROVE, or blank for all
    [string]$Symbol   = "",        # filter to one symbol
    [int]$Days        = 7,         # how many days back to look
    [int]$Limit       = 300
)

$dbPath = "C:\users\linda\trading_bot_v2\data\trading_bot.db"

# Build optional WHERE clauses
$filters = @("r.reviewer = 'trend_confirm'",
             "r.timestamp >= datetime('now', '-$Days days')")

if ($Decision -ne "") { $filters += "r.decision = '$Decision'" }
if ($Symbol   -ne "") { $filters += "r.symbol = '$Symbol'"     }

$where = $filters -join " AND "

$sqlQuery = @"
SELECT
  r.timestamp,
  r.symbol,
  r.direction,
  r.decision,
  r.confidence        AS indicators_passed,
  r.reasoning,
  -- nearest trade for this symbol within 90 seconds of the check
  t.trade_id,
  t.entry_price,
  t.pnl,
  t.pnl_pct,
  t.exit_reason,
  CASE
    WHEN t.trade_id IS NULL AND r.decision = 'BLOCK' THEN 'no_trade_blocked'
    WHEN t.trade_id IS NULL AND r.decision = 'APPROVE' THEN 'no_trade_approved'
    WHEN t.pnl > 0  AND r.decision = 'BLOCK'   THEN 'WRONG_block_was_winner'
    WHEN t.pnl <= 0 AND r.decision = 'BLOCK'   THEN 'RIGHT_block_was_loser'
    WHEN t.pnl > 0  AND r.decision = 'APPROVE' THEN 'RIGHT_approved_winner'
    WHEN t.pnl <= 0 AND r.decision = 'APPROVE' THEN 'WRONG_approved_loser'
    ELSE 'unknown'
  END AS verdict
FROM ai_signal_reviews r
LEFT JOIN trades t
  ON  t.symbol    = r.symbol
  AND t.direction = r.direction
  AND ABS(
        strftime('%s', t.entry_time) - strftime('%s', r.timestamp)
      ) <= 90
  AND t.strategy_name = 'breakout_scanner'
WHERE $where
ORDER BY r.timestamp DESC
LIMIT $Limit;
"@

Write-Host ""
Write-Host "  Trend Confirm Filter — last $Days days" -ForegroundColor Cyan
if ($Decision -ne "") { Write-Host "  Filter: decision=$Decision" -ForegroundColor Yellow }
if ($Symbol   -ne "") { Write-Host "  Filter: symbol=$Symbol"     -ForegroundColor Yellow }
Write-Host ""

$jsonOutput = python c:\users\linda\trading_bot_v2\Scripts\query_db.py `
    --db $dbPath --sql $sqlQuery

$results = $jsonOutput | ConvertFrom-Json

if (-not $results -or $results.Count -eq 0) {
    Write-Host "  No results found." -ForegroundColor Yellow
    exit
}

# ── Summary counts ────────────────────────────────────────────────────────────
$total         = $results.Count
$blocks        = ($results | Where-Object { $_.decision -eq 'BLOCK'   }).Count
$approves      = ($results | Where-Object { $_.decision -eq 'APPROVE' }).Count
$wrongBlocks   = ($results | Where-Object { $_.verdict -like 'WRONG_block*'   }).Count
$rightBlocks   = ($results | Where-Object { $_.verdict -like 'RIGHT_block*'   }).Count
$wrongApproves = ($results | Where-Object { $_.verdict -like 'WRONG_approved*' }).Count
$rightApproves = ($results | Where-Object { $_.verdict -like 'RIGHT_approved*' }).Count

Write-Host "  SUMMARY" -ForegroundColor White
Write-Host "  -------"
Write-Host "  Total checks : $total  (BLOCK=$blocks  APPROVE=$approves)"
if ($blocks -gt 0) {
    $blockAcc = [math]::Round($rightBlocks / $blocks * 100, 1)
    Write-Host "  Block accuracy : $rightBlocks right / $wrongBlocks wrong  ($blockAcc% correct)" -ForegroundColor $(if ($blockAcc -ge 55) { 'Green' } else { 'Red' })
}
if ($approves -gt 0) {
    $approveAcc = [math]::Round($rightApproves / $approves * 100, 1)
    Write-Host "  Approve accuracy: $rightApproves right / $wrongApproves wrong  ($approveAcc% correct)" -ForegroundColor $(if ($approveAcc -ge 55) { 'Green' } else { 'Red' })
}
Write-Host ""

# ── Detail table ──────────────────────────────────────────────────────────────
$results | Select-Object `
    @{N="Time";       E={ $_.timestamp -replace 'T',' ' -replace '\.\d+$','' }},
    @{N="Symbol";     E={ $_.symbol }},
    @{N="Dir";        E={ $_.direction }},
    @{N="Decision";   E={ $_.decision }},
    @{N="Indicators"; E={ "$($_.indicators_passed)/4" }},
    @{N="P&L%";       E={ if ($_.pnl_pct) { "$($_.pnl_pct)%" } else { "—" } }},
    @{N="Verdict";    E={ $_.verdict }},
    @{N="Reasoning";  E={ $_.reasoning }}
| Format-Table -AutoSize -Wrap
