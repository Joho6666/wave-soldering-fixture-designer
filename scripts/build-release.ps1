<#
.SYNOPSIS
    Build a release package for the Wave Soldering Fixture Designer.

.DESCRIPTION
    1. Builds the frontend (npm run build)
    2. Copies required files to a release directory
    3. Excludes dev artifacts (.venv, node_modules, __pycache__, tests, uploads, outputs, .env, etc.)

.EXAMPLE
    .\scripts\build-release.ps1
    .\scripts\build-release.ps1 -OutputDir "C:\release\fixture-designer"
#>
param(
    [string]$OutputDir = ".\release\wave-fixture-designer"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$ProjectRoot\backend")) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
if (-not (Test-Path "$ProjectRoot\backend")) {
    Write-Error "Cannot find project root. Run from project directory."
    exit 1
}

Write-Host "=== Wave Soldering Fixture Designer — Release Build ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Output dir:   $OutputDir"
Write-Host ""

# Step 1: Build frontend
Write-Host "[1/4] Building frontend..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
    Pop-Location
}

# Step 2: Clean output dir
Write-Host "[2/4] Preparing release directory..." -ForegroundColor Yellow
if (Test-Path $OutputDir) {
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Step 3: Copy files
Write-Host "[3/4] Copying files..." -ForegroundColor Yellow

# Backend app code
$backendDest = Join-Path $OutputDir "backend"
Copy-Item -LiteralPath "$ProjectRoot\backend\app" -Destination "$backendDest\app" -Recurse
Copy-Item -LiteralPath "$ProjectRoot\backend\requirements.txt" -Destination "$backendDest\requirements.txt"
Copy-Item -LiteralPath "$ProjectRoot\backend\README.md" -Destination "$backendDest\README.md" -ErrorAction SilentlyContinue
Copy-Item -LiteralPath "$ProjectRoot\backend\.env.example" -Destination "$backendDest\.env.example" -ErrorAction SilentlyContinue
Copy-Item -LiteralPath "$ProjectRoot\backend\pytest.ini" -Destination "$backendDest\pytest.ini" -ErrorAction SilentlyContinue

# Remove __pycache__
Get-ChildItem -Path "$backendDest" -Filter "__pycache__" -Directory -Recurse | Remove-Item -Recurse -Force

# Frontend dist
if (Test-Path "$ProjectRoot\dist") {
    Copy-Item -LiteralPath "$ProjectRoot\dist" -Destination (Join-Path $OutputDir "dist") -Recurse
}

# Launcher
Copy-Item -LiteralPath "$ProjectRoot\launcher" -Destination (Join-Path $OutputDir "launcher") -Recurse

# Validation framework (without generated outputs)
if (Test-Path "$ProjectRoot\validation") {
    $valDest = Join-Path $OutputDir "validation"
    Copy-Item -LiteralPath "$ProjectRoot\validation" -Destination $valDest -Recurse
    Get-ChildItem -Path "$valDest" -Filter "__pycache__" -Directory -Recurse | Remove-Item -Recurse -Force
    Get-ChildItem -Path "$valDest\cases" -Filter "generated" -Directory -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path "$valDest\cases" -Filter "report" -Directory -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# Root docs
@("ENGINEERING_STATUS.md", "ENGINEERING_AUDIT.md", "PRODUCTION_READINESS.md", "README.md") | ForEach-Object {
    $src = Join-Path $ProjectRoot $_
    if (Test-Path $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $OutputDir $_)
    }
}

# Step 4: Summary
Write-Host "[4/4] Release build complete!" -ForegroundColor Green
$totalFiles = (Get-ChildItem -Path $OutputDir -Recurse -File).Count
$totalSize = (Get-ChildItem -Path $OutputDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "  Output: $OutputDir"
Write-Host "  Files:  $totalFiles"
Write-Host "  Size:   $([math]::Round($totalSize, 1)) MB"
Write-Host ""
Write-Host "To run:"
Write-Host "  cd $OutputDir"
Write-Host "  python launcher\launcher.py"
