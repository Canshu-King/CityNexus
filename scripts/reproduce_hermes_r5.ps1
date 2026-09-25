param(
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][string]$PythonExe
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$target = [System.IO.Path]::GetFullPath($OutputDir)
if ($target.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Evidence output must be outside the Git worktree.'
}
Push-Location $repoRoot
try {
    $status = & git status --porcelain=v1 --untracked-files=all
    if ($LASTEXITCODE -ne 0 -or $status) { throw 'Refusing to run from a dirty source worktree.' }
    & $PythonExe 'scripts/run_hermes_r5_captured.py' '--output-dir' $target
    exit $LASTEXITCODE
}
finally { Pop-Location }
