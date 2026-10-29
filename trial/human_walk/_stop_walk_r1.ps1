param([string]$Pattern = "departure_full_walk_r21")
$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like ("*" + $Pattern + "*") }
Write-Output ("MATCHED=" + @($procs).Count)
foreach ($p in $procs) {
  Write-Output ("KILL PID=" + $p.ProcessId)
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
$left = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like ("*" + $Pattern + "*") }
Write-Output ("STILL_RUNNING=" + @($left).Count)
