@echo off
cd /d D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_serve_day25
set PYTHONPATH=backend
set CITYNEXUS_DATABASE_URL=sqlite:///D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_canary_day25.db
set CITYNEXUS_DEMO_MODE=true
set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=*
D:\moodle\CityNexus\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 4789 > D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_4789_day25.log 2>&1
