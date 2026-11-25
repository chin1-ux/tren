$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "C:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\venv\Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "local_india_$Timestamp.log"

$env:SCRAPER_MODE = "india"
$env:PYTHONIOENCODING = "utf-8"

Set-Location $RepoRoot
Write-Host "Starting Trendrop India Scraper locally on residential IP..."
Write-Host "Log file: $LogFile"
& $PythonExe backend\cron_job.py 2>&1 | Tee-Object -FilePath $LogFile
