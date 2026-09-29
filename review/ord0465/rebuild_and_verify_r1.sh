#!/usr/bin/env bash
# ORD-0465 lane stack: rebuild the bundle, move the lane's front onto it, re-prove ownership,
# re-run the screen arms. One command because the four steps are only meaningful together -- an arm
# result read off a port that is still serving the previous bytes is not a result.
set -euo pipefail
LANE="D:/moodle/_qoder_r_ord0465_20260929"
REPO="$LANE/wt"
NO_PROXY="*"; unset HTTP_PROXY HTTPS_PROXY

BUILD="dist_$(date +%H%M%S)"
echo "== build -> $BUILD =="
(cd "$LANE/wt/frontend" && node node_modules/vite/bin/vite.js build \
  --outDir "$LANE/$BUILD" --emptyOutDir 2>&1 | tail -2)

echo "== restart front :4931 =="
PID=$(netstat -ano | grep ":4931 " | grep LISTENING | awk '{print $5}' | head -1 || true)
if [ -n "${PID:-}" ]; then taskkill //PID "$PID" //F >/dev/null 2>&1 || true; sleep 1; fi
nohup /d/moodle/CityNexus/.venv/Scripts/python.exe \
  /d/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py \
  --dist "$LANE/$BUILD" --port 4931 --api 8731 \
  --log "$LANE/run/front_4931.log" > "$LANE/run/front_4931.out" 2>&1 &

sed -i "s#dist_[A-Za-z0-9]*#$BUILD#g" "$REPO/review/ord0465/lane_witnesses_r1.py"

/d/moodle/CityNexus/.venv/Scripts/python.exe -c "
import time, urllib.request
o = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for i in range(40):
    try:
        with o.open('http://127.0.0.1:4931/', timeout=3) as r:
            r.read(); print('front ready'); break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('front never came up')
"

echo "== ownership witnesses =="
/d/moodle/CityNexus/.venv/Scripts/python.exe "$REPO/review/ord0465/lane_witnesses_r1.py" 2>&1 | tail -2
echo "== screen arms =="
node "$REPO/review/ord0465/screen_arms_r1.js" 2>&1 | tail -30
echo "== current served dist: $BUILD =="
