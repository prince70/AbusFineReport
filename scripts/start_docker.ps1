param(
    [string]$Service = "web",
    [int]$Port = 5000,
    [switch]$Build
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

Write-Step "检查 Docker 环境"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未检测到 docker 命令，请先安装 Docker Desktop 并确保命令可用。"
}

docker version | Out-Null

Write-Step "检查 Compose 可用性"
$composeSubCommand = $null
try {
    docker compose version | Out-Null
    $composeSubCommand = "compose"
} catch {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $composeSubCommand = "docker-compose"
    } else {
        throw "未检测到 docker compose 或 docker-compose。"
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Step "启动容器服务"
    if ($composeSubCommand -eq "compose") {
        if ($Build) {
            docker compose up -d --build $Service
        } else {
            docker compose up -d $Service
        }
        Write-Step "查看运行状态"
        docker compose ps
    } else {
        if ($Build) {
            docker-compose up -d --build $Service
        } else {
            docker-compose up -d $Service
        }
        Write-Step "查看运行状态"
        docker-compose ps
    }

    Write-Step "执行本地探活"
    $probeUrl = "http://127.0.0.1:$Port/"
    try {
        $response = Invoke-WebRequest -Uri $probeUrl -UseBasicParsing -TimeoutSec 8
        Write-Info "探活成功: $probeUrl -> $($response.StatusCode)"
    } catch {
        Write-WarnText "探活失败: $probeUrl"
        Write-WarnText "可执行以下命令查看日志：docker compose logs --tail=120 $Service"
    }

    Write-Host ""
    Write-Info "Docker 服务已启动。访问地址: $probeUrl"
} finally {
    Pop-Location
}