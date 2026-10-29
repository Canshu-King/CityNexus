@echo off
setlocal
set PY=D:\moodle\CityNexus\.venv\Scripts\python.exe
set NODE=C:\Program Files\nodejs\node.exe
set PORT_DIR=D:\moodle\_cmdr_v3_port_1022
set RESCUE=D:\moodle\_cmdr_rescue_v3_1022

echo [1/3] preparing the classroom scene
"%PY%" "%PORT_DIR%\prepare_classroom_scene_r1.py"
if errorlevel 1 goto :failed

echo.
echo [2/3] walking the phone flow (this consumes the prepared proposal)
"%NODE%" "%RESCUE%\trial\human_walk\_classroom_rehearsal_r14.mjs"
if errorlevel 1 goto :failed

echo.
echo [3/3] restoring the opening scene
"%PY%" "%PORT_DIR%\prepare_classroom_scene_r1.py"
if errorlevel 1 goto :failed

echo.
echo Rehearsal passed; the scene is back at 09:00 with one waiting proposal.
echo Open the tablet address printed above.
echo Evidence: trial\results\20261022_v3_human_chrome\classroom-rehearsal-14.txt
goto :done

:failed
echo.
echo The rehearsal did NOT finish. Run start_classroom_demo.bat to reset the scene.
if not "%DEMO_NO_PAUSE%"=="1" pause
exit /b 1

:done
if "%DEMO_NO_PAUSE%"=="1" exit /b 0
pause
