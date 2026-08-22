
Get-CimInstance Win32_Process |
 Where-Object { $_.Name -like *tunnel* } | 
 Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine |
 Format-List
