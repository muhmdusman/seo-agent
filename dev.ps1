#Requires -Version 5.1
<#
.SYNOPSIS
    Search Console Agent - full stack development launcher for Windows.

.DESCRIPTION
    Starts PostgreSQL, Redis, Adminer, the Celery worker, the FastAPI API,
    and the Next.js frontend. Ctrl+C stops everything.

    This is the native PowerShell equivalent of dev.sh. Use it on Windows so
    you do not need Git Bash or WSL. Linux and macOS users run ./dev.sh.

.PARAMETER Stop
    Stop any leftover services and exit. Use this if a previous run was
    interrupted before it could clean up.

.EXAMPLE
    .\dev.ps1

.EXAMPLE
    .\dev.ps1 -Stop
#>

[CmdletBinding()]
param(
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Run from the repository root regardless of where the script was invoked.
$RootDir = $PSScriptRoot
Set-Location $RootDir

$ComposeFile = Join-Path $RootDir 'backend\docker-compose.yaml'
$PidFile     = Join-Path $RootDir '.dev-pids'

# Force UTF-8 for Python stdout/stderr. The Windows console defaults to a
# legacy codepage (cp1252), where logging any non-ASCII character raises
# UnicodeEncodeError and can take application startup down with it.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Write-Step { param([string]$Message) Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "    [ok] $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "    [!] $Message" -ForegroundColor Yellow }
function Write-Die  { param([string]$Message) Write-Host "`nERROR: $Message" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# Process teardown
# ---------------------------------------------------------------------------

function Stop-ProcessTree {
    param([int]$ProcessId)

    # taskkill /T walks the whole tree, which matters because uvicorn's
    # reloader and next's compiler both run as child processes.
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
}

function Stop-Everything {
    Write-Step 'Stopping services'

    if (Test-Path $PidFile) {
        foreach ($line in Get-Content $PidFile) {
            if ($line -match '^\d+$') { Stop-ProcessTree -ProcessId ([int]$line) }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $ComposeFile) {
        & docker compose -f $ComposeFile down 2>&1 | Out-Null
    }

    Write-Ok 'all services stopped'
}

if ($Stop) {
    Stop-Everything
    exit 0
}

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

Write-Step 'Checking prerequisites'

$required = @{
    'docker' = 'Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/'
    'uv'     = 'Install uv: https://docs.astral.sh/uv/getting-started/installation/'
    'npm'    = 'Install Node.js 20 or newer: https://nodejs.org/'
}

foreach ($tool in $required.Keys) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Die "'$tool' not found on PATH. $($required[$tool])"
    }
}

& docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Die 'Docker is installed but not running. Start Docker Desktop and retry.'
}

Write-Ok 'docker, uv, npm present'

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
# The backend reads .env relative to its own working directory, so
# backend\.env must exist. A root .env is the shared source of truth when
# present. We copy rather than symlink because symlinks on Windows require
# Developer Mode or an elevated shell.

Write-Step 'Resolving environment file'

$rootEnv    = Join-Path $RootDir '.env'
$backendEnv = Join-Path $RootDir 'backend\.env'

if (Test-Path $rootEnv) {
    Copy-Item $rootEnv $backendEnv -Force
    Write-Ok 'copied root .env to backend\.env'
}
elseif (Test-Path $backendEnv) {
    Write-Ok 'using existing backend\.env'
}
else {
    Write-Die "No .env found. Create one at $rootEnv (see the README for the required keys), or place it directly at backend\.env."
}

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

Write-Step 'Starting PostgreSQL, Redis, and Adminer'

& docker compose -f $ComposeFile up -d
if ($LASTEXITCODE -ne 0) { Write-Die 'docker compose up failed.' }

function Wait-Container {
    param([string]$Name, [int]$TimeoutSeconds = 60)

    Write-Host "    waiting for $Name" -NoNewline
    $format = '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'

    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        $status = (& docker inspect --format $format $Name 2>$null)
        if ($LASTEXITCODE -ne 0) { $status = 'missing' }

        if ($status -in @('healthy', 'running')) {
            Write-Host ' ready' -ForegroundColor Green
            return
        }
        if ($status -eq 'missing') {
            Write-Host ''
            Write-Die "Container '$Name' was not created. Check: docker compose -f `"$ComposeFile`" logs"
        }
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 1
    }

    Write-Host ''
    Write-Die "Container '$Name' never became healthy. Check: docker logs $Name"
}

Wait-Container -Name 'postgres'
Wait-Container -Name 'redis'

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

$BackendDir  = Join-Path $RootDir 'backend'
$FrontendDir = Join-Path $RootDir 'frontend'

Write-Step 'Installing Python dependencies'
Push-Location $BackendDir
try {
    & uv sync
    if ($LASTEXITCODE -ne 0) { Write-Die 'uv sync failed.' }
    Write-Ok 'dependencies synced'

    Write-Step 'Applying database migrations'
    & uv run alembic upgrade head
    if ($LASTEXITCODE -ne 0) { Write-Die 'Migrations failed. Fix the error above before continuing.' }
    Write-Ok 'schema up to date'
}
finally {
    Pop-Location
}

$Started = @()

function Start-Background {
    param(
        [string]$Label,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogFile
    )

    $proc = Start-Process -FilePath $FilePath -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError "$LogFile.err" `
        -NoNewWindow -PassThru

    Write-Ok "$Label (pid $($proc.Id)), logging to $LogFile"
    return $proc
}

Write-Step 'Starting Celery worker'
# The default prefork pool relies on fork(), which Windows does not provide,
# so the worker would crash on startup without --pool=solo.
$celeryLog = Join-Path $BackendDir 'celery.log'
$celery = Start-Background -Label 'celery worker' -WorkingDirectory $BackendDir `
    -FilePath 'uv' `
    -Arguments @('run', 'celery', '-A', 'core.celery_app', 'worker', '--loglevel=info', '--pool=solo') `
    -LogFile $celeryLog
$Started += $celery
Write-Warn 'using --pool=solo (Windows has no fork; concurrency is 1)'

Write-Step 'Starting FastAPI'
$backendLog = Join-Path $BackendDir 'backend.log'
$api = Start-Background -Label 'api' -WorkingDirectory $BackendDir `
    -FilePath 'uv' `
    -Arguments @('run', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000', '--reload') `
    -LogFile $backendLog
$Started += $api

$Started.Id | Set-Content $PidFile

Write-Host '    waiting for api' -NoNewline
$apiReady = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $null = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/openapi.json' -UseBasicParsing -TimeoutSec 2
        $apiReady = $true
        Write-Host ' ready' -ForegroundColor Green
        break
    }
    catch {
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 1
    }
}
if (-not $apiReady) {
    Write-Host ''
    Write-Warn "api did not respond within 45s; see $backendLog"
}

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

Write-Step 'Starting Next.js frontend'

$envLocal = Join-Path $FrontendDir '.env.local'
if (-not (Test-Path $envLocal)) {
    # ASCII, no BOM: Next.js reads this as a plain key=value file.
    [System.IO.File]::WriteAllText(
        $envLocal,
        "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`n",
        (New-Object System.Text.UTF8Encoding $false)
    )
    Write-Ok 'created frontend\.env.local'
}

if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
    Write-Host '    installing npm packages (first run, this takes a minute)'
    Push-Location $FrontendDir
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) { Write-Die 'npm install failed.' }
    }
    finally {
        Pop-Location
    }
}

$frontendLog = Join-Path $RootDir 'frontend.log'
# npm is a .cmd shim on Windows, so it has to be launched through cmd.exe.
$frontend = Start-Background -Label 'frontend' -WorkingDirectory $FrontendDir `
    -FilePath $env:ComSpec `
    -Arguments @('/c', 'npm', 'run', 'dev') `
    -LogFile $frontendLog
$Started += $frontend

$Started.Id | Set-Content $PidFile

# ---------------------------------------------------------------------------
# Ready
# ---------------------------------------------------------------------------

Write-Host @"

===========================================================
  Search Console Agent is running
===========================================================

  Frontend    http://localhost:3000
  API         http://127.0.0.1:8000
  API docs    http://127.0.0.1:8000/docs
  Adminer     http://localhost:8081

  PostgreSQL  localhost:5433
  Redis       localhost:6379

  Logs        backend\backend.log
              backend\celery.log
              frontend.log

  Press Ctrl+C to stop everything.
  If a run is interrupted, clean up with: .\dev.ps1 -Stop
===========================================================

"@

try {
    while ($true) {
        Start-Sleep -Seconds 1

        $dead = $Started | Where-Object { $_.HasExited }
        if ($dead) {
            foreach ($d in $dead) {
                Write-Warn "process $($d.Id) exited with code $($d.ExitCode); check the logs"
            }
            break
        }
    }
}
finally {
    Stop-Everything
}
