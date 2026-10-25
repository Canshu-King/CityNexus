@echo off
setlocal
set PY=D:\moodle\CityNexus\.venv\Scripts\python.exe
"%PY%" "D:\moodle\_cmdr_v3_port_1022\prepare_classroom_scene_r1.py"
if errorlevel 1 goto :failed
echo.
echo Open the tablet address printed by the script above (it changes with Wi-Fi).
echo On the phone: My trips - Classroom demo - Enter sample journey
goto :done
:failed
echo.
echo The classroom stack did NOT start. Check the messages above.
:done
if "%DEMO_NO_PAUSE%"=="1" exit /b 0
pause
