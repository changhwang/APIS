param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root "build_venv\Scripts\python.exe"

Write-Host "[APIS] Building with PyInstaller spec..."
& $py -m PyInstaller --noconfirm --clean build\apis.spec
& $py -m PyInstaller --noconfirm --clean build\check_hardware.spec

$releaseDir = Join-Path $root "release"
New-Item -ItemType Directory -Force $releaseDir | Out-Null

$zipName = "APIS-win64-v$Version.zip"
$zipPath = Join-Path $releaseDir $zipName

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "[APIS] Creating release zip: $zipName"
Compress-Archive -Path @(
    "dist\APIS",
    "dist\check_hardware",
    "release\README.txt",
    "release\prereq_checklist.md"
) -DestinationPath $zipPath

Write-Host "[APIS] Done: $zipPath"
