@echo off
rem CMDR scratch probe: a private backend on its own port with its own sqlite file, used only to read
rem what ORD-0359 reports for the AI state when the flag says "on" but no credential exists.
rem It never touches the phone chain's ports or its database.
cd /d D:\moodle\_qoder_cmdr_backend_live_1813\backend
set HTTPS_PROXY=
set HTTP_PROXY=
set NO_PROXY=*
set CITYNEXUS_DATABASE_URL=sqlite:///D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_scratch_ai.db
set CITYNEXUS_DEMO_MODE=true
set CITYNEXUS_AI_ENABLED=true
set DEEPSEEK_API_KEY=sk-bogus-not-a-real-key-cmdr-probe
set OPENAI_API_KEY=
set PYTHONIOENCODING=utf-8
D:\moodle\CityNexus\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8721
