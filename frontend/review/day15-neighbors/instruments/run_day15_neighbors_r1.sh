#!/bin/bash
# 前置单 (lane e766b154) -- re-run the four shared-testid neighbours against the day15 stack,
# one spec per run, serially, and print the counts of each trip.
#
# The stack is the commander's (01:45 block): front :4783, api :4787. This script starts nothing and
# stops nothing -- it only points a config at those two listeners. Before and after every spec it reads
# the journey roster, because these specs seed through the product's own create doors and a run that
# writes to a shared store has to say how much it wrote.
set -u
FRONT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
HHMM=$(date +%H%M)
cd "$FRONT" || exit 1

roster() {
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" "$PY" -c "
import json,urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:4787/api/v1/journeys', timeout=20) as r:
        rows = json.loads(r.read())
    print(len(rows) if isinstance(rows, list) else 'NOT_A_LIST')
except Exception as e:
    print('UNREADABLE %r' % (e,))
"
}

run_one() { # key file-stem
  local key=$1 stem=$2
  local evid="$LANE/run/neighbors_$stem"
  mkdir -p "$evid"
  local before after
  before=$(roster)
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E2E_PORT=4783 \
    CITYNEXUS_BACKEND_PORT=4787 \
    CITYNEXUS_E766_NEIGHBOR=$key \
    CITYNEXUS_E2E_RUN_ID="day15-e766b154-$stem-$HHMM" \
    CITYNEXUS_EVIDENCE_DIR="$LANE/run/neighbors_$stem" \
    CITYNEXUS_ORD0502_OUT="$LANE/run/neighbors_$stem" \
    CITYNEXUS_E766_REPORT="$LANE/run/report_neighbors_$stem.json" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.day15-neighbors-P.config.ts" \
    > "$LANE/run/gate_neighbors_$stem.log" 2>&1
  local rc=$?
  after=$(roster)
  echo "$stem rc=$rc journeys_before=$before journeys_after=$after $(grep -aoE '[0-9]+ passed|[0-9]+ failed|[0-9]+ skipped' "$LANE/run/gate_neighbors_$stem.log" | tr '\n' ' ')"
}

run_one ord0502 ord0502
run_one ord0497 ord0497
run_one ord0530 ord0530
run_one ord0537 ord0537
echo NEIGHBORS_DONE
