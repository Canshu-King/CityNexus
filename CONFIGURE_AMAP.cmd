@echo off
setlocal
pushd "%~dp0"
py -3.13 "%~dp0trial\configure_amap.py" %*
set "exitCode=%ERRORLEVEL%"
popd
if "%~1"=="" pause
exit /b %exitCode%
