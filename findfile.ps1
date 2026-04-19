param (
    [Parameter(Mandatory=$true)]
    [string]$FileName
)
Get-ChildItem -Path "." -Filter "*$FileName*" -Recurse -File | Select-Object -ExpandProperty FullName