@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%deploy_windows.ps1" %*

if errorlevel 1 (
  echo.
  echo [FAILED] 部署失败，请查看上面的错误信息。
) else (
  echo.
  echo [DONE] 部署完成。
)

pause
