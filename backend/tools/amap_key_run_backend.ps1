# Start the CityNexus backend with the Amap key taken from the Windows Credential Manager.
#
# The key is put into the environment of the process this script launches. It is not written to a file,
# not put into a user or machine environment variable (those are stored unencrypted in the registry),
# and not printed -- the only thing reported about it is which credential target it came from and its
# length. The variable name matches the interface the backend now reads first.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\tools\amap_key_run_backend.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\tools\amap_key_run_backend.ps1 -CheckOnly
#   ... -Port 8000 -DatabaseUrl "sqlite:///D:/moodle/CityNexus/backend/_dev.db"

[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$Python = 'D:\moodle\CityNexus\backend\.venv\Scripts\python.exe',
    [string]$DatabaseUrl = '',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'amap_credential.ps1')

$secret = Get-AmapKey
if (-not $secret) {
    Write-Host ('NOT_CONFIGURED: no key in ' + $script:AmapCredentialTarget)
    Write-Host ('Enter it once with:  powershell -NoProfile -ExecutionPolicy Bypass -File "' `
        + $PSScriptRoot + '\amap_key_setup.ps1"')
    exit 2
}
Write-Host ('KEY_SOURCE: ' + $script:AmapCredentialTarget + ', length ' + $secret.Length + ' (value not printed)')

if ($CheckOnly) {
    Write-Host 'CHECK_ONLY=credential readable; backend not started'
    exit 0
}

$backend = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host ('REFUSED: the interpreter that runs this suite is missing: ' + $Python)
    Write-Host 'Pass -Python <path\to\python.exe>. Nothing was started, so the key stayed in the store.'
    exit 3
}

# Both names, for one reason: a checkout that has not taken the rename yet reads only the old
# one, and a wizard that silently does nothing there is worse than one that says what it set.
$env:CITYNEXUS_AMAP_WEB_KEY = $secret
$env:AMAP_WEB_KEY = $secret
if ($DatabaseUrl) { $env:CITYNEXUS_DATABASE_URL = $DatabaseUrl }

Write-Host ('STARTING uvicorn app.main:app on 127.0.0.1:' + $Port + ' from ' + $backend)
Write-Host 'A provider that answers with the key will show READY under mobility.amap; without it the'
Write-Host 'screens keep the existing place and route capabilities.'
Push-Location $backend
try {
    & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --log-level info
    exit $LASTEXITCODE
}
finally {
    Pop-Location
    Remove-Item Env:\CITYNEXUS_AMAP_WEB_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\AMAP_WEB_KEY -ErrorAction SilentlyContinue
}
