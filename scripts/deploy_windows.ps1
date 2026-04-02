param(
    [string]$Package = "production-query-web.tar.gz",
    [string]$Image = "production-query-web:latest",
    [string]$Container = "production-query-web",
    [int]$HostPort = 8001,
    [int]$ContainerPort = 8001,
    [string]$DeployDir = ".",
    [string]$DbFile = ""
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

$resolvedDeployDir = (Resolve-Path $DeployDir).Path

if (-not [System.IO.Path]::IsPathRooted($Package)) {
    $packagePath = Join-Path $resolvedDeployDir $Package
} else {
    $packagePath = $Package
}

if (-not (Test-Path $packagePath)) {
    throw "未找到镜像包: $packagePath"
}

Write-Step "准备镜像文件"
$tarPath = $null
$extension = [System.IO.Path]::GetExtension($packagePath).ToLowerInvariant()

if ($extension -eq ".gz") {
    Write-Info "检测到 tar.gz，开始解压"
    tar -xzf $packagePath -C $resolvedDeployDir

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($packagePath)
    $candidate = Join-Path $resolvedDeployDir $baseName
    if (Test-Path $candidate) {
        $tarPath = $candidate
    } else {
        $tarPath = Get-ChildItem -Path $resolvedDeployDir -Filter *.tar |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
} elseif ($extension -eq ".tar") {
    $tarPath = $packagePath
} else {
    throw "仅支持 .tar 或 .tar.gz，当前文件: $packagePath"
}

if (-not $tarPath -or -not (Test-Path $tarPath)) {
    throw "解压后未找到 tar 文件，请检查镜像包是否完整。"
}

Write-Step "导入镜像"
docker load -i $tarPath

Write-Step "清理同名容器"
$existingContainer = docker ps -a --filter "name=^/${Container}$" --format "{{.Names}}"
if ($existingContainer -eq $Container) {
    docker rm -f $Container | Out-Null
    Write-Info "已删除旧容器: $Container"
}

Write-Step "启动新容器"
$runArgs = @(
    "run", "-d",
    "--name", $Container,
    "-p", "${HostPort}:${ContainerPort}",
    "-e", "DB_TYPE=sqlite",
    "-e", "SECRET_KEY=production-query-secret-key-2024"
)

$dbMountPath = $null
if ($DbFile) {
    if ([System.IO.Path]::IsPathRooted($DbFile)) {
        $dbMountPath = $DbFile
    } else {
        $dbMountPath = Join-Path $resolvedDeployDir $DbFile
    }
} else {
    $defaultDb = Join-Path $resolvedDeployDir "production.db"
    if (Test-Path $defaultDb) {
        $dbMountPath = $defaultDb
    }
}

if ($dbMountPath -and (Test-Path $dbMountPath)) {
    $runArgs += @("-v", "${dbMountPath}:/app/production.db")
    Write-Info "已挂载数据库: $dbMountPath"
} else {
    Write-WarnText "未挂载外部数据库文件，将使用容器内数据库。"
}

$runArgs += $Image

$containerId = docker @runArgs
if (-not $containerId) {
    throw "容器启动失败。"
}

Start-Sleep -Seconds 2

Write-Step "验证运行状态"
docker ps --filter "name=^/${Container}$" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

$probeUrl = "http://127.0.0.1:${HostPort}/"
try {
    $response = Invoke-WebRequest -Uri $probeUrl -UseBasicParsing -TimeoutSec 8
    Write-Info "探活成功: $probeUrl -> $($response.StatusCode)"
} catch {
    Write-WarnText "探活失败: $probeUrl"
    Write-WarnText "可执行以下命令查看日志: docker logs -f $Container"
}

Write-Host ""
Write-Info "部署完成。访问地址: $probeUrl"
