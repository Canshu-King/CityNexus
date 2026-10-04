#!/bin/bash
# day31 recycle-bin real-door reading (lane e766b154) -- one store, one api, one front, two arms.
#
# The arms themselves do the only two writes there are, through the product's own doors (withdraw, then
# undelete), on THIS lane's private copy. Ports are new and private: api :8795, front :4997. The
# commander's :4783/:4787/:4789 and the shared :8000/:4781/:4782/:8693 are never bound or queried here.
set -u
WT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
FRONT=$WT/frontend
EVID=$WT/frontend/review/journey-in-bin-real-door
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
EXPORT=$LANE/export_day31/backend
DIST="D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_day31e766\\frontend\\dist"
mkdir -p "$EVID/receipts" "$EVID/readings" "$EVID/instruments" "$EVID/logs"

echo "== 1: one private store"
rm -f "$LANE/run/day31_bin_probe.db"
env -u HTTP_PROXY -u HTTPS_PROXY python "$LANE/tools/make_lane_db_r3.py" run/day31_bin_probe CNX-DAY31-BIN \
  > "$LANE/run/day31_bin_db.log" 2>&1
mv -f "$LANE/run/day31_bin_probe" "$LANE/run/day31_bin_probe.db" 2>/dev/null
grep -a "marker_rows_in_my_copy\|TARGET" "$LANE/run/day31_bin_db.log"

echo "== 2: api :8795 on the tip's backend tree"
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" PYTHONPATH="$EXPORT" \
  CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/day31_bin_probe.db" \
  CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8795 \
  > "$LANE/run/day31_bin_api_8795.log" 2>&1 &
sleep 18
echo "api_startup=$(grep -ac 'Application startup complete' $LANE/run/day31_bin_api_8795.log)"

echo "== 3: front :4997 on the tip's bundle"
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
  --dist "$DIST" --port 4997 --api 8795 > "$LANE/run/day31_bin_front_4997.log" 2>&1 &
sleep 8
netstat -ano -p TCP | grep -aE "127\.0\.0\.1:(8795|4997) " | grep -a LISTENING

echo "== 4: ownership + the journey id straight from the doors"
( cd "$EVID" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" PYTHONIOENCODING=utf-8 \
    python journey_in_bin_ownership_r1.py )
JID=$(python -c "import json,io;print(json.load(io.open('$EVID/receipts/journey_in_bin_ownership_r1.json',encoding='utf-8'))['scene_journey_id'])")
echo "journey_id=$JID"

echo "== 5: the two arms"
( cd "$FRONT" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E766_BIN_BASE="http://127.0.0.1:4997" \
    CITYNEXUS_E766_BIN_OUT="$EVID/readings" \
    CITYNEXUS_E766_BIN_JOURNEY="$JID" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.e766-journey-in-bin-r1-P.config.ts" \
    > "$LANE/run/day31_bin_arms.log" 2>&1 )
echo "arms_rc=$? $(grep -aoE '[0-9]+ passed|[0-9]+ failed|[0-9]+ error' "$LANE/run/day31_bin_arms.log" | tr '\n' ' ')"
ls "$EVID/readings" | wc -l
echo DAY31_JOURNEY_IN_BIN_DONE
