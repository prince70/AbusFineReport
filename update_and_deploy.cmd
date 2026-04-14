@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"

echo [STEP] Move to project root
cd /d "%PROJECT_ROOT%" || (
  echo [ERROR] Failed to enter project root: %PROJECT_ROOT%
  exit /b 1
)

where git >nul 2>nul || (
  echo [ERROR] git is not installed or not in PATH.
  exit /b 1
)

echo [STEP] Check git repository
git rev-parse --is-inside-work-tree >nul 2>nul || (
  echo [ERROR] Current folder is not a git repository.
  exit /b 1
)

echo [STEP] Check working tree status
for /f %%S in ('git status --porcelain') do (
  echo [ERROR] Working tree is not clean. Commit or stash changes first.
  exit /b 1
)

for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%B"
if not defined CURRENT_BRANCH (
  echo [ERROR] Failed to detect current git branch.
  exit /b 1
)

echo [STEP] Pull latest code from origin/%CURRENT_BRANCH%
git fetch --all --prune || (
  echo [ERROR] git fetch failed.
  exit /b 1
)

git pull --ff-only origin %CURRENT_BRANCH% || (
  echo [ERROR] git pull failed. Please resolve manually.
  exit /b 1
)

echo [STEP] Build and restart Docker service
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start_docker.ps1" -Service web -Port 8001 || (
  echo [ERROR] Docker deploy failed.
  exit /b 1
)

echo.
echo [DONE] Update and deploy completed successfully.
exit /b 0
