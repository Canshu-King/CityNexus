param([switch]$Kill)
$ErrorActionPreference = "Stop"
# Match ONLY the console window the launcher opened (its command line names citynexus-play-server.bat).
# Deliberately not matching the serve script by name: the walkthrough's own human stack runs that same
# script, and a tree kill aimed at it would take the running stack down with it.
$targets = @()
$all = Get-CimInstance Win32_Process -Filter "Name='cmd.exe'"
foreach ($p in $all) {
  $cmd = [string]$p.CommandLine
  if ($cmd -match "citynexus-play-server") {
    $targets += $p
    Write-Output ("MATCH pid={0} parent={1} cmd={2}" -f $p.ProcessId, $p.ParentProcessId, $cmd.Substring(0, [Math]::Min(140, $cmd.Length)))
  }
}
Write-Output ("MATCHES {0} of cmd_rows {1}" -f $targets.Count, @($all).Count)
if ($Kill) {
  foreach ($t in $targets) {
    Write-Output ("KILL_TREE pid={0}" -f $t.ProcessId)
    Start-Process -FilePath "taskkill.exe" -ArgumentList @("/PID", $t.ProcessId, "/T", "/F") -Wait -NoNewWindow
  }
} else {
  Write-Output "REPORT ONLY, nothing killed"
}
