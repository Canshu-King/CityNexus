param(
    [string]$ArchivePath = "",
    [switch]$CommitAndPush,
    [switch]$VerifyOnly
)
$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "import_v3_design.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "V3 import script missing: $scriptPath"
}
$arguments = @($scriptPath)
if ($ArchivePath) {
    $arguments += @("--archive", $ArchivePath)
}
if ($VerifyOnly) {
    $arguments += "--verify-only"
}
if ($CommitAndPush) {
    $arguments += "--commit-and-push"
}
& python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "V3 ZIP verification/import failed; code $LASTEXITCODE. No completion may be claimed."
}
