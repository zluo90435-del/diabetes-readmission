# 一鍵初始化 Git 並準備 push 到 GitHub
# 用法：在 PowerShell 執行 .\setup_github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Git {
    $paths = @(
        "git",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Program Files (x86)\Git\bin\git.exe"
    )
    foreach ($p in $paths) {
        if ($p -eq "git") {
            $cmd = Get-Command git -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
        } elseif (Test-Path $p) {
            return $p
        }
    }
    return $null
}

$git = Find-Git
if (-not $git) {
    Write-Host ""
    Write-Host "尚未安裝 Git。請先安裝：" -ForegroundColor Yellow
    Write-Host "  https://git-scm.com/download/win" -ForegroundColor Cyan
    Write-Host "安裝時選「Git from the command line」後，關閉並重開終端機，再執行本腳本。" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "使用 Git: $git" -ForegroundColor Green

# 必要檔案檢查
$required = @(
    "app.py",
    "requirements.txt",
    "data\diabetic_data.csv",
    "models\diabetes_pipeline.pkl",
    "models\metrics.json"
)
foreach ($f in $required) {
    if (-not (Test-Path $f)) {
        Write-Host "缺少必要檔案: $f" -ForegroundColor Red
        if ($f -like "data\*") { Write-Host "  請執行: python export_data.py" }
        if ($f -like "models\*") { Write-Host "  請執行: python train.py" }
        exit 1
    }
}

if (-not (Test-Path ".git")) {
    & $git init
    & $git branch -M main
}

& $git add .
& $git status

$status = & $git status --porcelain
if (-not $status) {
    Write-Host "沒有新變更需要 commit。" -ForegroundColor Yellow
} else {
    & $git commit -m "Diabetes readmission risk app v2 - LightGBM, CSV deploy ready"
    Write-Host "Commit done." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  下一步：建立 GitHub 並 push" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 到 https://github.com/new 建立新 repository"
Write-Host "   名稱建議: diabetes-readmission"
Write-Host "   不要勾選「Add README」（保持空 repo）"
Write-Host ""
Write-Host "2. 在終端機執行（把 YOUR_USERNAME 改成你的帳號）："
Write-Host ""
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/diabetes-readmission.git" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "3. 到 https://share.streamlit.io 部署"
Write-Host "   Main file: app.py"
Write-Host "   Secrets: DATA_SOURCE = csv" -ForegroundColor White
Write-Host ""
Write-Host "詳細說明見 docs\DEPLOY.md" -ForegroundColor Gray
