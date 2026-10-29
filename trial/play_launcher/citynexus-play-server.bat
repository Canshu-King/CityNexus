@echo off
rem CityNexus trial server. Keep this file pure ASCII: PowerShell/cmd codepages eat CJK in .bat files.
rem All human-readable text lives in citynexus_play_preflight_r1.py (UTF-8).
setlocal
set "PY=D:\moodle\CityNexus\.venv\Scripts\python.exe"
rem The launcher's own copy is the one with CITYNEXUS_REAL_CITY_* set; the copy in
rem _cmdr_v3_port_1022 is older and leaves place research off.
set "TOOLS=%~dp0"
set "HUMAN_TAG=play"
set "HUMAN_DB=citynexus_v3_play_1024.db"
set "HUMAN_BACKEND_PORT=60361"
set "HUMAN_WEB_PORT=14461"
set "HUMAN_KEEP_DB=1"
if "%HUMAN_LAN%"=="1" (set "HUMAN_LAN_NOTE=lan mode") else (set "HUMAN_LAN_NOTE=localhost only")
echo CityNexus trial server (%HUMAN_LAN_NOTE%). Close this window or press Ctrl+C to stop.
"%PY%" "%TOOLS%_cmdr_v3_serve_human_r1.py"
echo Server stopped.
pause
