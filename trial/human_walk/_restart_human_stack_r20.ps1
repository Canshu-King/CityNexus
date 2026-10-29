# Restart the human canary stack so the running backend picks up new code (it serves without --reload).
# It stops only the two PIDs that LISTEN on the canary ports, then re-runs the same boot script.
$ErrorActionPreference = "Stop"
$ports = @(60296, 14496)
$killed = @()
foreach ($port in $ports) {
  $lines = (netstat -ano | Select-String "LISTENING" | Select-String (":" + $port + "\s"))
  foreach ($line in $lines) {
    $pid2 = ($line.ToString() -split "\s+")[-1]
    if ($pid2 -match "^\d+$" -and [int]$pid2 -gt 4) {
      try { Stop-Process -Id ([int]$pid2) -Force -ErrorAction Stop; $killed += "$port=$pid2" }
      catch { Write-Output ("STOP_FAILED port=" + $port + " pid=" + $pid2 + " " + $_.Exception.GetType().Name) }
    }
  }
}
Write-Output ("killed=" + ($killed -join ","))
# The boot script deletes its canary database on every start (_cmdr_v3_serve_human_r1.py:34), so a restart
# erases the provider receipts the previous walk left behind.  Copy the file aside first; nothing reads it back.
$db = "D:\moodle\_cmdr_v3_live_1022\citynexus_v3_human21_1022.db"
if (Test-Path $db) {
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item -LiteralPath $db -Destination ($db + ".before_" + $stamp) -Force
  Write-Output ("db_saved=" + $db + ".before_" + $stamp)
} else { Write-Output "db_absent_nothing_to_save" }
Start-Sleep -Seconds 2
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\moodle\_cmdr_v3_port_1022\_boot_human_stack_r19.ps1"
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 3
  try {
    $probe = Invoke-WebRequest -Uri "http://127.0.0.1:14496/revolution" -TimeoutSec 5 -UseBasicParsing
    if ($probe.StatusCode -eq 200) { $ready = $true; break }
  } catch { }
}
Write-Output ("web_ready=" + $ready + " waited_cycles=" + ($i + 1))
