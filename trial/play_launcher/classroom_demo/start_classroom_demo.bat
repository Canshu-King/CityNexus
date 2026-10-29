@echo off
setlocal
set PY=D:\moodle\CityNexus\.venv\Scripts\python.exe
"%PY%" "D:\moodle\_cmdr_v3_port_1022\prepare_classroom_scene_r1.py"
if errorlevel 1 goto :failed
echo.
echo Open the tablet address printed above within 2 minutes; the ticket is one-use.
echo If the link expired, run this launcher again to print a fresh address.
echo This launcher resets the demo database every time it starts.
goto :done
:failed
echo.
echo The classroom stack did NOT start. Check the messages above.
:done
if "%DEMO_NO_PAUSE%"=="1" exit /b 0
pause
