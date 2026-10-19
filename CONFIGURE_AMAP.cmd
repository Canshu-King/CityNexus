@echo off
setlocal
pushd "%~dp0"
py -3.13 "%~dp0trial\configure_amap.py" %*
set "exitCode=%ERRORLEVEL%"
popd
exit /b %exitCode%
