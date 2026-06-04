@echo off
setlocal
cd /d "%~dp0"
python scripts\boot_urbanpulse.py %*
endlocal
