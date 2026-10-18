param(
    [switch]$CheckOnly,
    [switch]$Agent,
    [switch]$NoBrowser,
    [ValidateSet('Ask', 'AI', 'Explore')][string]$Mode = 'Ask'
)

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

function Get-ServiceMode([int]$Port) {
    try {
        $runtime = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/agent/runtime-status" -TimeoutSec 3
        if ($runtime.ai_state -eq 'DISABLED') { return 'Explore' }
        if ($runtime.hermes_compat_configured -eq $true) { return 'AI' }
    }
    catch {}
    return 'Unknown'
}

if ($Agent) { $Mode = 'AI' }
if (-not $CheckOnly -and $Mode -eq 'Ask') {
    Write-Host ''
    Write-Host '1  AI 旅行规划：使用本机 wb2api，提交需求时调用模型，可能计费'
    Write-Host '2  仅探索：查找地点、安排行程和散步路线'
    $choice = Read-Host '选择 1 或 2'
    if ($choice -eq '1') { $Mode = 'AI' }
    elseif ($choice -eq '2') { $Mode = 'Explore' }
    else { throw '请输入 1 或 2 后重新启动。' }
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
$serviceMode = if ($sameBackend) { Get-ServiceMode $backPort } else { 'Unknown' }
$modeMatches = ($Mode -eq 'Ask') -or ($Mode -eq $serviceMode)
if ($sameFrontend -and $sameBackend -and $modeMatches) {
    Write-Host "Using this checkout's healthy local service: $url"
    Write-Host "Mode: $serviceMode"
    if (-not $CheckOnly -and -not $NoBrowser) { Start-Process -FilePath $url }
    return
}

if ($CheckOnly) {
    Write-Host '当前目录没有匹配此模式的运行实例。'
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
Write-Host "Mode: $Mode | 保持这个窗口打开，网页就能持续使用。"
$launchArguments = @('--fresh', '--frontend-port', [string]$frontPort, '--backend-port', [string]$backPort)
$runName = $sha + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$runtimeDirectory = Join-Path $env:LOCALAPPDATA (Join-Path 'CityNexus\Revolution' $runName)
$launchArguments += @('--runtime-dir', $runtimeDirectory)
if ($Mode -eq 'AI') { $launchArguments += '--agent' }
if ($NoBrowser) { $launchArguments += '--no-browser' }
& py -3.13 (Join-Path $PSScriptRoot 'try_revolution.py') @launchArguments
if ($LASTEXITCODE -ne 0) { throw "Revolution launcher exited with code $LASTEXITCODE" }
