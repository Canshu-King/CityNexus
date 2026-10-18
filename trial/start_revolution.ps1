param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
$guidePath = Join-Path $repoRoot 'trial\REVOLUTION_USER_ILLUSTRATED_GUIDE_CN.md'
$branch = (& git -C $repoRoot branch --show-current).Trim()
$sha = (& git -C $repoRoot rev-parse --short=12 HEAD).Trim()

function Test-Http200([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    }
    catch { return $false }
}

function Get-ListeningPid([int]$Port) {
    try {
        $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop
        return @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    }
    catch { return @() }
}

function Test-CheckoutProcess([int]$Port, [ValidateSet('frontend', 'backend')][string]$Kind) {
    $ids = Get-ListeningPid $Port
    if ($ids.Count -eq 0) { return $false }
    foreach ($processId in $ids) {
        $processInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if (-not $processInfo -or -not $processInfo.CommandLine) { continue }
        $commandLine = $processInfo.CommandLine
        if ($commandLine.IndexOf($repoRoot, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) { continue }
        if ($Kind -eq 'frontend' -and $commandLine -match 'vite') { return $true }
        if ($Kind -eq 'backend' -and $commandLine -match 'uvicorn' -and $commandLine -match 'agent_preview_app:app') { return $true }
    }
    return $false
}

function Test-FreeLocalPort([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true }
    catch { return $false }
    finally { try { $listener.Stop() } catch {} }
}

$frontPort = 14332
$backPort = 18501
$frontHealth = "http://127.0.0.1:$frontPort/api/v1/health"
$backHealth = "http://127.0.0.1:$backPort/api/v1/health"
$url = "http://127.0.0.1:$frontPort/revolution"

Write-Host "CityNexus Revolution | branch $branch | source $sha"
Write-Host "Guide: $guidePath"

$sameFrontend = (Test-CheckoutProcess $frontPort 'frontend') -and (Test-Http200 $frontHealth)
$sameBackend = (Test-CheckoutProcess $backPort 'backend') -and (Test-Http200 $backHealth)
if ($sameFrontend -and $sameBackend) {
    Write-Host "Using this checkout's healthy local service: $url"
    if (-not $CheckOnly) { Start-Process -FilePath $url }
    return
}

if ($CheckOnly) {
    Write-Host 'No healthy service pair owned by this checkout was found; running services were left untouched.'
    exit 2
}

$foundPair = $false
for ($offset = 0; $offset -lt 40; $offset++) {
    $candidateFront = 14332 + (2 * $offset)
    $candidateBack = 18501 + (2 * $offset)
    if ((Test-FreeLocalPort $candidateFront) -and (Test-FreeLocalPort $candidateBack)) {
        $frontPort = $candidateFront
        $backPort = $candidateBack
        $foundPair = $true
        break
    }
}

if (-not $foundPair) { throw 'No free local Revolution port pair was found in the configured range.' }

Write-Host "Starting isolated services at http://127.0.0.1:$frontPort/revolution"
Write-Host 'The terminal stays open while the services run. This launcher keeps AI disabled.'
& py -3.13 (Join-Path $PSScriptRoot 'try_revolution.py') --fresh --frontend-port $frontPort --backend-port $backPort
if ($LASTEXITCODE -ne 0) { throw "Revolution launcher exited with code $LASTEXITCODE" }
