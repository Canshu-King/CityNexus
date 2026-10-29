# Restart the project's own automation Edge (the profile under E:/cmdr_chrome_v3_1022) when its CDP
# endpoint stops answering Playwright.  It is not the user's personal browser: a separate user-data-dir.
$ErrorActionPreference = "Stop"
$profile = "E:/cmdr_chrome_v3_1022/profile_edge_third_use"
$procs = Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object { $_.CommandLine -like "*profile_edge_third_use*" }
Write-Output ("edge_processes_found=" + @($procs).Count)
foreach ($proc in $procs) {
  if ([int]$proc.ProcessId -le 4) { continue }
  try { Stop-Process -Id ([int]$proc.ProcessId) -Force -ErrorAction Stop } catch { Write-Output ("stop_failed pid=" + $proc.ProcessId) }
}
Start-Sleep -Seconds 4
$flags = @(
  "--user-data-dir=$profile",
  "--remote-debugging-port=9335",
  "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
  "--disable-gpu", "--renderer-process-limit=2", "--disable-background-networking",
  "--disable-sync", "--window-size=430,932", "--window-position=80,60",
  "http://127.0.0.1:14496/revolution"
)
Start-Process -FilePath "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" -ArgumentList $flags
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 2
  try {
    $probe = Invoke-WebRequest -Uri "http://127.0.0.1:9335/json/version" -TimeoutSec 4 -UseBasicParsing
    if ($probe.StatusCode -eq 200) { $ready = $true; break }
  } catch { }
}
Write-Output ("cdp_ready=" + $ready + " waited_cycles=" + ($i + 1))
$targets = (Invoke-WebRequest -Uri "http://127.0.0.1:9335/json/list" -TimeoutSec 6 -UseBasicParsing).Content
Write-Output ("page_targets=" + ([regex]::Matches($targets, '"type": "page"')).Count)
