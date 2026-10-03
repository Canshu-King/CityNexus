#!/bin/bash
# day26 real-door word reads (lane e766b154) -- CMDR 19:46: four sentences whose answer must come from
# the door itself, not from this instrument.
#
# Order matters and is deliberate:
#   fresh store -> targets read out of that store (?mode=ro) -> api + front on that store ->
#   ownership proved -> control arm (a real stamp that must NOT paint a refusal) -> four refusal arms.
# The targets receipt is written before anything listens, so the ids the browser sends are facts about
# the same file the api is answering from.
set -u
WT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
FRONT=$WT/frontend
EVID=$WT/frontend/review/checkin-words-real-door
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
EXPORT=$LANE/export_day26/backend
DIST="D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_day26e766\\frontend\\dist"

echo "== 1: one private store"
rm -f "$LANE/run/day26_real_door.db"
env -u HTTP_PROXY -u HTTPS_PROXY python "$LANE/tools/make_lane_db_r3.py" run/day26_real_door CNX-DAY26-REAL \
  > "$LANE/run/day26_real_db.log" 2>&1
mv -f "$LANE/run/day26_real_door" "$LANE/run/day26_real_door.db" 2>/dev/null
grep -a "marker_rows_in_my_copy\|TARGET" "$LANE/run/day26_real_db.log"

echo "== 2: targets out of that store, read-only"
( cd "$EVID" && env -u HTTP_PROXY -u HTTPS_PROXY python real_door_targets_r1.py )
echo "targets_rc=$?"

echo "== 3: api :8794 and front :4996 on that store"
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" PYTHONPATH="$EXPORT" \
  CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/day26_real_door.db" \
  CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8794 \
  > "$LANE/run/day26_real_api_8794.log" 2>&1 &
sleep 18
echo "api_startup=$(grep -ac 'Application startup complete' $LANE/run/day26_real_api_8794.log)"
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
  --dist "$DIST" --port 4996 --api 8794 > "$LANE/run/day26_real_front_4996.log" 2>&1 &
sleep 8

echo "== 4: ownership"
( cd "$EVID" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" python real_door_stack_ownership_r1.py )
echo "ownership_rc=$?"

echo "== 5: arms (control first, then the four refusals, both locales)"
mkdir -p "$EVID/readings"
( cd "$FRONT" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E766_REAL_BASE="http://127.0.0.1:4996" \
    CITYNEXUS_E766_REAL_OUT="$EVID/readings" \
    CITYNEXUS_E766_REAL_TARGETS="$EVID/receipts/real_door_targets_r1.json" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.e766-checkin-words-real-door-P.config.ts" \
    > "$LANE/run/day26_real_arms.log" 2>&1 )
echo "arms_rc=$? $(grep -aoE '[0-9]+ passed|[0-9]+ failed|[0-9]+ error' "$LANE/run/day26_real_arms.log" | tr '\n' ' ')"
ls "$EVID/readings" | wc -l
echo DAY26_REAL_DOOR_DONE
