#!/bin/bash
# ORD-0541 lane -- start one stack per generation: its own database behind its own uvicorn, its own
# static front in front of it. Nothing here reuses another generation's store, because "the roster is
# the size the first press left it" is only a reading if the file behind the door is mine.
#
# Serialised with sleeps so the netstat read-back at the end sees every listener, and every command
# line names its own --port and its own CITYNEXUS_DATABASE_URL, which is what the ownership probe
# reads.
set -u
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
EXPORT=$LANE/export_s2/backend

api() { # port db marker-city-unused-here
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=api.github.com \
    PYTHONPATH="$EXPORT" \
    CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/$2" \
    CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$1" \
    > "$LANE/run/o541_api_$1.log" 2>&1 &
}
front() { # port dist api
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=api.github.com "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
    --dist "$2" --port "$1" --api "$3" --log "D:\\moodle\\_qoder_e766b154_ord0528_20261001\\run\\o541_front_$1.jsonl" \
    > "$LANE/run/o541_front_$1.log" 2>&1 &
}

api 8774 o541_candidate.db
api 8775 o541_base.db
api 8776 o541_mutant.db
sleep 14
front 4980 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_ord0541c\\frontend\\dist" 8774
front 4981 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_ord0541b\\frontend\\dist" 8775
front 4982 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_ord0541m\\frontend\\dist" 8776
sleep 10
echo "=== listeners ==="
netstat -ano -p TCP | grep -aE "127\.0\.0\.1:(8774|8775|8776|4980|4981|4982) " | grep -a LISTENING
echo STACK_UP
