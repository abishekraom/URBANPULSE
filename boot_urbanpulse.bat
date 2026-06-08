@echo off
setlocal EnableExtensions
title UrbanPulse Boot Console
cd /d "%~dp0"

echo.
echo ============================================================
echo   UrbanPulse Boot Console
echo ============================================================
echo   Project: %CD%
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo.

set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3.11+ or run this from a terminal where python works.
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% scripts\boot_urbanpulse.py %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo ============================================================
  echo   UrbanPulse boot exited with code %EXIT_CODE%
  echo ============================================================
  echo If this window closed before, the message above is the reason.
  echo Common fixes:
  echo   1. Stop old servers using ports 8001 and 5173.
  echo   2. Install backend deps:  cd backend ^&^& python -m pip install -r requirements.txt
  echo   3. Install frontend deps: cd frontend ^&^& npm install
  echo.
  echo Full boot logs, if created, are under: logs\boot_YYYYMMDD_HHMMSS\
  echo.
  pause
)

endlocal
exit /b %EXIT_CODE%
