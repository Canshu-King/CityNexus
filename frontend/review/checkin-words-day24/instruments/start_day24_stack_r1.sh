#!/bin/bash
# day24 手机打卡门新句屏读 (lane e766b154) -- three private stores, three apis, three fronts, one bundle.
#
# Why three stores when one bundle serves all of them: two of the arms write real stamps through the
# product's own door (the zh duplicate refusal and the en one), and those two must not see each other's
# rows -- the reading "the notice appeared under exactly one stop" is only worth anything if the store
# held no other notice-causing row. The third store carries the arms that answer the door with a forged
# body (page.route), which write nothing at all, so they can share one file safely.
#
# Ports are this lane's own: api :8790-:8792, front :4990-:4992. The commander's :4783/:4787 and the
# forbidden :8000/:4781/:4782/:8693 are never bound or touched here.
set -u
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
EXPORT=$LANE/export_day24/backend
DIST="D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_day24e766\\frontend\\dist"

api() { # port db
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    PYTHONPATH="$EXPORT" \
    CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/$2.db" \
    CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$1" \
    > "$LANE/run/day24_api_$1.log" 2>&1 &
}
front() { # port api
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
    --dist "$DIST" --port "$1" --api "$2" \
    --log "D:\\moodle\\_qoder_e766b154_ord0528_20261001\\run\\day24_front_$1.jsonl" \
    > "$LANE/run/day24_front_$1.log" 2>&1 &
}

api 8790 day24_zh_real
api 8791 day24_en_real
api 8792 day24_words_fake
sleep 18
front 4990 8790
front 4991 8791
front 4992 8792
sleep 10
echo "=== listeners ==="
netstat -ano -p TCP | grep -aE "127\.0\.0\.1:(879[0-2]|499[0-2]) " | grep -a LISTENING
echo "=== api startup lines ==="
for p in 8790 8791 8792; do echo "$p complete=$(grep -ac 'Application startup complete' $LANE/run/day24_api_$p.log)"; done
echo DAY24_STACK_UP
