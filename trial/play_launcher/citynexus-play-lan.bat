@echo off
rem Same trial, but the page also listens on the LAN so a tablet on the same WiFi can open it.
rem The API stays on 127.0.0.1; only the page binds outward. Windows Firewall may still block inbound 14461 --
rem the helper prints the exact rule command and leaves that decision to you.
chcp 65001 >nul
setlocal
set "HUMAN_LAN=1"
call "%~dp0citynexus-play.bat"
