@echo off
setlocal
set PY=D:\moodle\CityNexus\.venv\Scripts\python.exe
"%PY%" "D:\moodle\_cmdr_v3_port_1022\prepare_classroom_scene_r1.py"
echo.
echo Open on the tablet (same Wi-Fi): http://10.15.5.23:14492/revolution
echo On the phone: My trips - Classroom demo - Enter sample journey
pause
