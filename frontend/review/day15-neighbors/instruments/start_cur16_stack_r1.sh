#!/bin/bash
# 当前线重跑 (lane e766b154) -- one pristine store per neighbour, one front per store, all four fronts
# serving the same bundle built from the authoritative tip.
#
# Why per-spec databases: the reading this lane delivered for day15 was that these instruments poison
# each other through the store -- ORD-0530 withdraws the trip through the product's own DELETE door and
# ORD-0537 leaves a stamp that makes ORD-0497's "empty read" arms red. So a re-run that shares one
# database answers a question nobody asked. Here each neighbour gets a copy that nothing else touches,
# and the copy carries a marker city no other store has, so "which file answered" is a reading too.
set -u
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
EXPORT=$LANE/export_s2/backend
DIST="D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_cur16\\frontend\\dist"

api() { # port db
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=api.github.com \
    PYTHONPATH="$EXPORT" \
    CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/$2.db" \
    CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$1" \
    > "$LANE/run/cur16_api_$1.log" 2>&1 &
}
front() { # port api
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=api.github.com "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
    --dist "$DIST" --port "$1" --api "$2" \
    --log "D:\\moodle\\_qoder_e766b154_ord0528_20261001\\run\\cur16_front_$1.jsonl" \
    > "$LANE/run/cur16_front_$1.log" 2>&1 &
}

api 8780 cur16_ord0502
api 8781 cur16_ord0497
api 8782 cur16_ord0530
api 8783 cur16_ord0537
sleep 16
front 4985 8780
front 4986 8781
front 4987 8782
front 4988 8783
sleep 10
echo "=== listeners ==="
netstat -ano -p TCP | grep -aE "127\.0\.0\.1:(878[0-3]|498[5-8]) " | grep -a LISTENING
echo "=== api startup lines ==="
for p in 8780 8781 8782 8783; do echo "$p complete=$(grep -ac 'Application startup complete' $LANE/run/cur16_api_$p.log)"; done
echo CUR16_STACK_UP
