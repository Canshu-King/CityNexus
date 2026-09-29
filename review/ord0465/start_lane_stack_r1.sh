#!/usr/bin/env bash
# ORD-0465 lane stack - bring up everything the screen arms need, on this lane's own files and ports.
#
# Nothing here touches a shared store: the database is created under the lane directory, the backend
# runs from THIS worktree (so it is the code under review, not the authoritative tree), and the two
# ports are this lane's. The front is the commander's own static+API proxy, started with --log so the
# third ownership witness is obtainable here; on `vite preview` that witness does not exist and has
# to be reported as unobtainable instead.
#
#   bash review/ord0465/start_lane_stack_r1.sh      # backend :8731, front :4931
#   node review/ord0465/screen_arms_r1.js           # 24 arms
#   node review/ord0465/owner_map_regression_r1.js  # the map this order widened
set -euo pipefail
LANE="D:/moodle/_qoder_r_ord0465_20260929"
REPO="$LANE/wt"
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
NO_PROXY="*"; unset HTTP_PROXY HTTPS_PROXY

echo "== ports must be free =="
$PY -c "
import socket, sys
for p in (8731, 4931):
    s = socket.socket(); busy = s.connect_ex(('127.0.0.1', p)) == 0; s.close()
    if busy: print('  BUSY', p); sys.exit(1)
print('  8731 and 4931 free')
"

echo "== backend :8731 on this lane's own database =="
mkdir -p "$LANE/run"
# `</dev/null` and `disown` are not decoration: without them the backgrounded uvicorn keeps this
# script's own stdout open, so the caller's shell never gets control back even though the stack is
# up and serving. Measured on the first run of this file -- the seed completed and the marker probes
# answered 200/404 while the script still looked hung.
(cd "$REPO/backend" && PYTHONPATH="..;../.." \
  CITYNEXUS_DATABASE_URL="sqlite:///$LANE/run/ord0465_lane.db" \
  CITYNEXUS_DEMO_MODE=true nohup $PY -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8731 > "$LANE/run/backend_8731.log" 2>&1 </dev/null &
  disown)

$PY -c "
import time, urllib.request
o = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(90):
    try:
        with o.open('http://127.0.0.1:8731/api/v1/health', timeout=3) as r:
            r.read(); print('  backend up'); break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('backend never came up - see run/backend_8731.log')
"

echo "== seed the five states through the real doors =="
(cd "$REPO" && PYTHONPATH="backend;." \
  CITYNEXUS_DATABASE_URL="sqlite:///$LANE/run/ord0465_lane.db" \
  CITYNEXUS_DEMO_MODE=true $PY "$REPO/review/ord0465/lane_seed_r1.py" \
  | tail -2)
echo "  report: $LANE/run/seed_report.json"

echo "== next: build the bundle, move the front onto it, re-prove ownership, run the arms =="
echo "  bash $REPO/review/ord0465/rebuild_and_verify_r1.sh"
echo "  (that script builds a dist, restarts :4931 against it, re-runs the ownership witnesses"
echo "   and then the 24 screen arms; it exits non-zero if any of them is red.)"
