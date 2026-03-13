@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

set "PYTHONUTF8=1"
set "HVDC_MCP_TRANSPORT=stdio"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" server.py %*
  set "EXITCODE=%ERRORLEVEL%"
  popd >nul
  exit /b %EXITCODE%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 server.py %*
  set "EXITCODE=%ERRORLEVEL%"
  popd >nul
  exit /b %EXITCODE%
)

where python >nul 2>nul
if not errorlevel 1 (
  python server.py %*
  set "EXITCODE=%ERRORLEVEL%"
  popd >nul
  exit /b %EXITCODE%
)

echo [hvdc-knowledge] Python was not found. Install Python or create .venv in the repository. 1>&2
popd >nul
exit /b 1
