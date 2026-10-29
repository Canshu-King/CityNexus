# Boot sixteen: the walk that must show a public-transport hop on the traveller's screen.
# walk-77's story puts Badaling (the Great Wall pass north of the city) in the morning and a downtown
# stop in the afternoon, and that hop refuses as walking
# while the transport door answers it at 78,050 m / 180 min
# (trial/results/20261022_v3_human_chrome/amap-transit-within-city-1.txt:3 and :6).  On r14 that plan hit
# the 500 fixed in edcca35e83dae4d196dc9c068bc7bd5ec2306f6f; on r15 the freeze completed but every hop in
# that draft was walkable, so the band's transit count (N hops verified as public transport) still has no
# screen reading.  This stack is that one reading: new db name, two new free ports, nothing earlier touched.
# refused plan, which is the BEFORE half of this slice.
$ErrorActionPreference = "Stop"
$env:HUMAN_BACKEND_PORT = "60296"
$env:HUMAN_WEB_PORT = "14496"
$env:HUMAN_DB = "citynexus_v3_human21_1022.db"
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:http_proxy -ErrorAction SilentlyContinue
Remove-Item Env:all_proxy -ErrorAction SilentlyContinue
$env:HTTPS_PROXY = "http://127.0.0.1:7892"
$env:https_proxy = "http://127.0.0.1:7892"
$env:NO_PROXY = "localhost,127.0.0.1,::1,restapi.amap.com,photon.komoot.io,nominatim.openstreetmap.org,overpass-api.de"
$env:no_proxy = $env:NO_PROXY
$env:CITYNEXUS_REAL_CITY_ENABLED = "true"
$env:CITYNEXUS_REAL_CITY_MODE = "live"
# The AMap key lives in the user environment scope only (never in a file, never printed).
$amap = [Environment]::GetEnvironmentVariable("CITYNEXUS_AMAP_WEB_KEY", "User")
if ($amap) { $env:CITYNEXUS_AMAP_WEB_KEY = $amap }
Write-Output ("amap_key_present=" + [bool]$env:CITYNEXUS_AMAP_WEB_KEY)
$py = "D:\moodle\CityNexus\.venv\Scripts\python.exe"
$script = "D:\moodle\_cmdr_v3_port_1022\_cmdr_v3_serve_human_r1.py"
Start-Process -FilePath $py -ArgumentList $script -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Output "booted_r19_backend_60296_web_14496_db_human21"
