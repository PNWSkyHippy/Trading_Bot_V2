param (
    [Parameter(Mandatory=$true)]
    [string]$FileName1
    [string]$FileName2
    [string]$FileName3
)
Get-Content t$FileName3) -replace $FileName1, $FileName2 | Set-Content $FileName3