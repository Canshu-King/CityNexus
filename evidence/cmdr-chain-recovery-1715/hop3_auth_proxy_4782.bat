@echo off
rem CMDR chain hop 3: Basic-auth proxy :4782 -> :4781, /api* -> :8693 (blob 050b64872c0dbdd313bf29604b7fc721b34c99c0)
cd /d D:\moodle\_qoder_recovery_20260919
set PYTHONIOENCODING=utf-8
D:\moodle\CityNexus\.venv\Scripts\python.exe raw\preview_auth_proxy.py
