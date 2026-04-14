param(
    [string]$Service = "web",
    [int]$Port = 8001,
    [switch]$NoBuild,
    [switch]$SkipFrontendBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-WarnText {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

Write-Step "Check Docker environment"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker command not found. Install Docker Desktop and ensure it is available."
}

try {
    docker info | Out-Null
} catch {
    throw "Docker Desktop is not running. Start Docker Desktop."
}

docker version | Out-Null

Write-Step "Check Compose availability"
$composeSubCommand = $null
try {
    docker compose version | Out-Null
    $composeSubCommand = "compose"
} catch {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $composeSubCommand = "docker-compose"
    } else {
        throw "docker compose or docker-compose is not available."
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not $SkipFrontendBuild) {
        Write-Step "Build frontend assets"
        $packageJsonPath = Join-Path $projectRoot "package.json"
        if (-not (Test-Path $packageJsonPath)) {
            throw "package.json not found; cannot build frontend."
        }
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "npm not found. Install Node.js or use -SkipFrontendBuild."
        }
        npm run build
    } else {
        Write-Step "Skip frontend build"
    }

    $shouldBuild = -not $NoBuild
    if ($shouldBuild) {
        Write-Step "Starting service with rebuild"
    } else {
        Write-Step "Starting service without rebuild"
    }

    if ($composeSubCommand -eq "compose") {
        if ($shouldBuild) {
            docker compose up -d --build $Service
        } else {
            docker compose up -d $Service
        }
        Write-Step "Inspecting service status"
        docker compose ps
    } else {
        if ($shouldBuild) {
            docker-compose up -d --build $Service
        } else {
            docker-compose up -d $Service
        }
        Write-Step "Inspecting service status"
        docker-compose ps
    }

    Write-Step "Probe service health"
    $probeUrl = "http://127.0.0.1:$Port/"
    try {
        $response = Invoke-WebRequest -Uri $probeUrl -UseBasicParsing -TimeoutSec 8
        Write-Info "Probe success: $probeUrl -> $($response.StatusCode)"
    } catch {
        Write-WarnText "Probe failed: $probeUrl"
        if ($composeSubCommand -eq "compose") {
            Write-WarnText "Run: docker compose logs --tail=120 $Service"
        } else {
            Write-WarnText "Run: docker-compose logs --tail=120 $Service"
        }
    }

    Write-Info "Docker service started at: $probeUrl"
} finally {
    Pop-Location
}
