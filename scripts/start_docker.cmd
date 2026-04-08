@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_docker.ps1" %*

if errorlevel 1 (
  echo.
  echo [FAILED] 启动失败，请查看上面的错误信息。
) else (
  echo.
  echo [DONE] 启动完成。
)

pause