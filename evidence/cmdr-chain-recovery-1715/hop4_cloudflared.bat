@echo off
rem CMDR chain hop 4: cloudflared quick tunnel -> :4782 (URL lands in run/tunnel_new.log)
cd /d D:\moodle\_qoder_preview_20260920
tools\cloudflared.exe tunnel --url http://127.0.0.1:4782 --no-autoupdate
