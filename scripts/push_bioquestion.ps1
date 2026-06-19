#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) not found. Run: winget install GitHub.cli"
}
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run 'gh auth login' first (browser login)." -ForegroundColor Yellow
    gh auth login
}

if (-not (Test-Path ".git")) { git init -b main }

git add -A
git status

if (-not (git diff --cached --quiet 2>$null) -or (git status --porcelain | Select-String "^??")) {
    git commit -m "Initial commit: BioQuestion literature learning workflow" 2>$null
}

$remote = "https://github.com/EinroyVan/BIOQUESTION.git"
if (-not (git remote | Select-String "^origin$")) {
    git remote add origin $remote
} else {
    git remote set-url origin $remote
}

if (gh repo view EinroyVan/BIOQUESTION 2>$null) {
    Write-Host "Repo exists, pushing..."
} else {
    gh repo create EinroyVan/BIOQUESTION --public --source=. --remote=origin --description "Biomedical literature extract, quiz, and grade (Gemini + Streamlit)"
}

git push -u origin main
Write-Host "Done: https://github.com/EinroyVan/BIOQUESTION" -ForegroundColor Green
