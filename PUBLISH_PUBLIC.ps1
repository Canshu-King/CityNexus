param([string]$PublicRepoName = 'CityNexus-Coursework-2026')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$owner = 'Canshu-King'
$sourceRepo = 'https://github.com/Canshu-King/CityNexus.git'
$branch = 'publication/teacher-public-ready-20261106'
foreach ($command in @('git', 'gh')) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Install $command first." }
}
gh auth status
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI is not signed in. Run gh auth login.' }
gh auth setup-git
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI Git credentials setup failed.' }
$dir = Join-Path ([System.IO.Path]::GetTempPath()) ('citynexus-public-' + [guid]::NewGuid().ToString('N'))
git clone --depth 1 --single-branch --branch $branch $sourceRepo $dir
if ($LASTEXITCODE -ne 0) { throw 'Unable to clone staging branch.' }
Push-Location $dir
try {
  $tracked = @(git ls-files)
  $bad = @($tracked | Where-Object { $_ -match '(?i)(^|/)(\.env($|\.(?!example$))|[^/]+\.(pem|key|p12|sqlite|sqlite3|db)$|[^/]*credentials?[^/]*)' })
  if ($bad.Count -gt 0) { throw ('Sensitive filenames detected: ' + ($bad -join '; ')) }
  $pattern = '(?i)(github_pat_[A-Za-z0-9_]{25,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----)'
  $hits = @()
  foreach ($f in $tracked) {
    if ($f -match '(?i)\.(md|txt|py|js|jsx|ts|tsx|json|yaml|yml|css|html|toml|ps1|sh|svg|xml)$') {
      $item = Get-Item -LiteralPath $f -ErrorAction SilentlyContinue
      if ($item -and $item.Length -lt 2000000) {
        try { if ([IO.File]::ReadAllText($item.FullName) -match $pattern) { $hits += $f } } catch {}
      }
    }
  }
  if ($hits.Count -gt 0) { throw ('Potential secret patterns detected: ' + ($hits -join '; ')) }
  if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    gitleaks dir . --no-banner
    if ($LASTEXITCODE -ne 0) { throw 'Gitleaks scan failed. Review before publishing.' }
  } else { Write-Warning 'Gitleaks is not installed. Automated scanning is incomplete.' }
  Write-Warning 'Manually check binary PDF/Visio/Project metadata, student details, licenses, code literals and test fixtures before publishing.'
  $ok = Read-Host 'After reviewing files, type PUBLIC to publish a NEW public repository'
  if ($ok -cne 'PUBLIC') { throw 'Cancelled. Nothing was made public.' }
  gh repo view "$owner/$PublicRepoName" *> $null
  if ($LASTEXITCODE -eq 0) { throw 'Target repository already exists; refusing to overwrite.' }
  git checkout --orphan public-root
  if ($LASTEXITCODE -ne 0) { throw 'Could not create a history-free commit.' }
  git add -A
  git -c user.name='CityNexus Coursework Team' -c user.email='coursework@users.noreply.github.com' commit -m 'Publish curated CityNexus coursework and implementation evidence'
  if ($LASTEXITCODE -ne 0) { throw 'Root commit failed.' }
  git branch -M main
  gh repo create "$owner/$PublicRepoName" --public --source . --remote public --push --description 'CityNexus Smart City Traveler System coursework and implementation'
  if ($LASTEXITCODE -ne 0) { throw 'GitHub public-repo creation failed. Check remote status before retrying.' }
  Write-Host "https://github.com/$owner/$PublicRepoName"
} finally { Pop-Location }
