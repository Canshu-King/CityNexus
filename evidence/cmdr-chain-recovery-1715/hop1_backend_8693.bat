@echo off
rem CMDR chain hop 1: backend uvicorn :8693 on the authoritative tip tree
cd /d D:\moodle\_qoder_cmdr_land_0349r5\backend
set CITYNEXUS_DATABASE_URL=sqlite:///D:/moodle/_qoder_preview_20260920/_preview.db
set CITYNEXUS_DEMO_MODE=true
set CITYNEXUS_AI_ENABLED=false
set PYTHONIOENCODING=utf-8
D:\moodle\CityNexus\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8693
