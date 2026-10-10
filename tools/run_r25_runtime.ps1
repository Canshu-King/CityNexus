$cfgPath = Join-Path $env:USERPROFILE 'WorkBuddy\2026-09-15-15-47-27\wb2api\config.json'
$cfg = Get-Content -LiteralPath $cfgPath | ConvertFrom-Json
$env:CITYNEXUS_DATABASE_URL = 'sqlite:///D:/moodle/CityNexus-Revolution-RealTrip-Recovery/r25-runtime.sqlite3'
$env:CITYNEXUS_HERMES_API_URL = 'http://127.0.0.1:7863/v1/chat/completions'
$env:CITYNEXUS_HERMES_API_KEY = $cfg.api_key
$env:CITYNEXUS_HERMES_MODEL = 'cn:glm-5.3-flash'
$env:CITYNEXUS_AI_ENABLED = 'true'
$env:CITYNEXUS_DEMO_MODE = 'true'
$env:CITYNEXUS_DEMO_RESET_TOKEN = 'r25-lab-reset-20261003'
$env:CITYNEXUS_LAB_ESTIMATE_AUTHORITY = 'false'
$env:CITYNEXUS_REAL_CITY_ENABLED = 'true'
$env:CITYNEXUS_REAL_CITY_MODE = 'live'
$env:CITYNEXUS_LIVE_VALHALLA_URL = 'https://valhalla1.openstreetmap.de'
$env:CITYNEXUS_GUARDIAN_SIGNAL_PROVIDER = 'open-meteo'
$env:CITYNEXUS_IMPACT_TIMEOUT_SECONDS = '120'
Set-Location 'D:\moodle\CityNexus-Revolution-RealTrip-Recovery\backend'
$python313 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
& $python313 -m uvicorn app.main:app --host 127.0.0.1 --port 8014
