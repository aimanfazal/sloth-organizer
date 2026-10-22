# build.ps1 — Build frontend and copy dist into the Python static folder
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install

Write-Host "==> Building frontend..." -ForegroundColor Cyan
npm run build

Set-Location ..

$src  = "frontend\dist"
$dest = "backend\sloth_organizer\static"

Write-Host "==> Syncing $src -> $dest ..." -ForegroundColor Cyan
if (Test-Path $dest) {
    Remove-Item $dest -Recurse -Force
}
Copy-Item $src $dest -Recurse

Write-Host "==> Done." -ForegroundColor Green
