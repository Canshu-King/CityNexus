$ErrorActionPreference = 'Stop'
# Lane e766b154: stop EVERY process listening on this lane's ORD-0541 ports. The first version of this
# cleanup used Get-NetTCPConnection and only saw one owner per port, because this lane started the same
# front twice; netstat prints one row per listener, so this reads netstat and checks each pid's own
# command line before terminating anything.
$out = 'D:/moodle/_qoder_e766b154_ord0528_20261001/run/stop_all_lane_listeners_ord0541.txt'
$ports = @('8774', '8775', '8776', '4980', '4981', '4982')
$lines = @()
$rows = & netstat -ano -p TCP | Select-String 'LISTENING'
$targets = @{}
foreach ($row in $rows) {
  # netstat's lines begin with spaces, so splitting on whitespace puts an empty field first:
  # ['', 'TCP', local, remote, state, pid]. Indexing this by hand is what made the first cut of this
  # script find no listeners at all, and it was re-run against netstat's own output before shipping.
  $parts = (@($row.Line -split '\s+') | Where-Object { $_ -ne '' })
  if ($parts.Count -lt 5) { continue }
  $local = $parts[1]
  $owner = $parts[$parts.Count - 1]
  foreach ($port in $ports) {
    if ($local -eq ('127.0.0.1:' + $port)) { $targets[$owner] = $port }
  }
}
$lines += ('LISTENERS_FOUND ' + $targets.Count)
foreach ($pid2 in $targets.Keys) {
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$pid2" -ErrorAction SilentlyContinue
  if ($null -eq $p) { $lines += ('PID {0} NOT_FOUND (already gone)' -f $pid2); continue }
  $cl = [string]$p.CommandLine
  $mine = ($cl -match 'uvicorn app\.main:app') -or ($cl -match 'cmdr_static_api_proxy_r1\.py')
  if (-not $mine) { $lines += ('PID {0} NOT_LANES_TOOL SKIPPED :: {1}' -f $pid2, $cl); continue }
  $lines += ('PID {0} PORT {1} MINE :: {2}' -f $pid2, $targets[$pid2], $cl.Substring(0, [Math]::Min(150, $cl.Length)))
  Stop-Process -Id $pid2 -Force
}
Start-Sleep -Seconds 4
$rows2 = & netstat -ano -p TCP | Select-String 'LISTENING'
foreach ($port in $ports) {
  $hits = @($rows2 | Where-Object { $_.Line -match ('127\.0\.0\.1:' + $port + '\s') })
  $lines += ('AFTER PORT {0} LISTENERS {1}' -f $port, $hits.Count)
}
Set-Content -Path $out -Value $lines -Encoding UTF8
Write-Output ('LINES ' + $lines.Count)
