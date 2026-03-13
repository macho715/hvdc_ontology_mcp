@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows_client.ps1" -SyncClaude -SyncCodexGlobal %*
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo [hvdc-knowledge] Windows full setup failed with exit code %EXITCODE%.
)
exit /b %EXITCODE%
