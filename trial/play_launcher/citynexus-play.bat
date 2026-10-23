@echo off
rem Double-click to play CityNexus locally. Pure ASCII on purpose; the Chinese text comes from the python helper.
chcp 65001 >nul
setlocal
set "PY=D:\moodle\CityNexus\.venv\Scripts\python.exe"
set "TOOLS=D:\moodle\_cmdr_v3_port_1022"
"%PY%" "%TOOLS%\citynexus_play_preflight_r1.py"
if errorlevel 1 goto fail
start "CityNexus trial server" "%~dp0citynexus-play-server.bat"
"%PY%" "%TOOLS%\citynexus_play_preflight_r1.py" --wait-and-open
goto end
:fail
echo.
echo Not started. Read the lines above.
:end
echo.
pause
