# Amap Web-service key: enter it once, locally. ASCII only on purpose (see amap_credential.ps1).
#
# The value is typed into a SecureString prompt, so it never appears on screen, never enters a command
# line, and never lands in any history file or log. It is stored in the Windows Credential Manager and
# read back to prove the round trip. The only thing printed about it is its length.
#
#   enter or rotate:  powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\tools\amap_key_setup.ps1
#   delete it again:  powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\tools\amap_key_setup.ps1 -Remove
#   keep what is stored: press Enter at the prompt
#
# Acceptance tiers this script can distinguish, because the order asked for them:
#   NOT_CONFIGURED          nothing stored and nothing pasted, or the pasted shape was refused
#   KEY_ENTERED_LOCALLY     stored and read back equal, provider not reached
#   REAL_PROVIDER_SUCCESS   Amap answered status=1 to one request made with that key

[CmdletBinding()]
param(
    [switch]$SkipProviderCheck,
    [switch]$Remove,
    [string]$TargetOverride = '',
    [string]$SecretOverride = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'amap_credential.ps1')
if ($TargetOverride) { $script:AmapCredentialTarget = $TargetOverride }

if ($Remove) {
    $gone = Remove-AmapKey
    Write-Host ('DELETED: ' + $script:AmapCredentialTarget + ' -> ' + $gone)
    Write-Host 'STATUS=NOT_CONFIGURED'
    return
}

Write-Host 'CityNexus / Amap Web-service key -- local configuration'
Write-Host 'Paste the Web-service key. Press Enter alone to keep whatever is already stored.'

if ($SecretOverride) {
    # Used only by the self-test; a test run supplies the value on its own command line, which is not a
    # path any real key takes.
    $secret = $SecretOverride.Trim()
}
else {
    $secure = Read-Host -Prompt 'Amap Web-service key' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($secure)
    try { $secret = [Runtime.InteropServices.Marshal]::PtrToStringUni($pointer) }
    finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($pointer) }
    $secret = $secret.Trim()
}

if ($secret.Length -eq 0) {
    $existing = Get-AmapKey
    if ($existing) {
        Write-Host ('KEEP_EXISTING: a key is already stored, length ' + $existing.Length)
        Write-Host 'STATUS=KEY_ENTERED_LOCALLY'
        return
    }
    Write-Host 'REFUSED: nothing was pasted and nothing is stored.'
    Write-Host 'STATUS=NOT_CONFIGURED'
    exit 2
}

# Shape, not content: a Web-service key is 32 hex characters. This is what refuses a SHA1, an Android
# certificate fingerprint or a package name without echoing what was pasted.
if ($secret -notmatch '^[0-9a-fA-F]{32}$') {
    Write-Host ('REFUSED: the pasted value is ' + $secret.Length + ' characters, not the 32 hex characters' `
        + ' a Web-service key has. A SHA1, a package name or an Android key is not what this expects.' `
        + ' Nothing was stored.')
    Write-Host 'STATUS=NOT_CONFIGURED'
    exit 3
}

Set-AmapKey -Secret $secret
$round = Get-AmapKey
if (-not $round -or $round -ne $secret) {
    Write-Host 'REFUSED: the value read back from the credential store does not match what was written.'
    Write-Host 'STATUS=NOT_CONFIGURED'
    exit 4
}
Write-Host ('STORED: ' + $script:AmapCredentialTarget + ', length ' + $round.Length + ' (the value itself is never printed)')

if ($SkipProviderCheck) {
    Write-Host 'PROVIDER_CHECK=SKIPPED_BY_SWITCH'
    Write-Host 'STATUS=KEY_ENTERED_LOCALLY'
    return
}

# One request, one public endpoint, and the answer is reported by field name and count only. If the
# exception text ever carried the key, it is masked before it is printed.
try {
    $uri = 'https://restapi.amap.com/v3/config/district?keywords=' + [uri]::EscapeDataString('Beijing') `
        + '&subdistrict=0&key=' + $secret
    $answer = Invoke-RestMethod -Uri $uri -TimeoutSec 15
    if ([string]$answer.status -eq '1') {
        Write-Host ('PROVIDER_CHECK=success, infocode=' + [string]$answer.infocode + ', districts=' `
            + @($answer.districts).Count)
        Write-Host 'STATUS=REAL_PROVIDER_SUCCESS'
    }
    else {
        Write-Host ('PROVIDER_CHECK=answered-but-refused, info=' + [string]$answer.info `
            + ', infocode=' + [string]$answer.infocode)
        Write-Host 'STATUS=KEY_ENTERED_LOCALLY'
        Write-Host 'The key is stored and readable, but Amap refused this request. Check that it is a'
        Write-Host 'Web-service key and that its own restrictions (IP whitelist, domain) allow this machine.'
    }
}
catch {
    $message = [string]$_.Exception.Message
    if ($message.Contains($secret)) { $message = $message.Replace($secret, 'key=***') }
    Write-Host ('PROVIDER_CHECK=network_or_http_failure: ' + $message)
    Write-Host 'STATUS=KEY_ENTERED_LOCALLY'
    Write-Host 'Stored fine; the provider call could not be completed from this network.'
}

Write-Host ''
Write-Host 'Next step, one command (the backend takes the key from the credential store, not from a file):'
Write-Host ('  powershell -NoProfile -ExecutionPolicy Bypass -File "' + $PSScriptRoot + '\amap_key_run_backend.ps1"')
