#!/bin/bash
# 当前线重跑 -- the four shared-testid neighbours, one per pristine store, against the bundle built from
# the authoritative tip the 包工头 named (00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9).
#
# Each neighbour gets its own front + api + database pair (see start_cur16_stack_r1.sh for why), so a red
# can be read as "this instrument on this generation" rather than "whatever the previous run left in the
# store". Every pair was proved before the first click: receipts/cur16_stack_ownership_r1.json.
set -u
FRONT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
HHMM=$(date +%H%M)
cd "$FRONT" || exit 1

run_one() { # key stem front api
  local key=$1 stem=$2 fport=$3 aport=$4
  local evid="$LANE/run/cur16_$stem"
  mkdir -p "$evid"
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E2E_PORT=$fport \
    CITYNEXUS_BACKEND_PORT=$aport \
    CITYNEXUS_E766_NEIGHBOR=$key \
    CITYNEXUS_E2E_RUN_ID="cur16-e766b154-$stem-$HHMM" \
    CITYNEXUS_EVIDENCE_DIR="$evid" \
    CITYNEXUS_ORD0502_OUT="$evid" \
    CITYNEXUS_E766_REPORT="$LANE/run/report_cur16_$stem.json" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.day15-neighbors-P.config.ts" \
    > "$LANE/run/gate_cur16_$stem.log" 2>&1
  echo "$stem rc=$? front=$fport api=$aport $(grep -aoE '[0-9]+ passed|[0-9]+ failed' "$LANE/run/gate_cur16_$stem.log" | tr '\n' ' ')"
}

# Cheapest-first is deliberate: the three footprint/map arms finish in minutes, the mainline burns its
# arm ceilings, and the readings that arrive early are the ones worth having first.
run_one ord0497 ord0497 4986 8781
run_one ord0530 ord0530 4987 8782
run_one ord0537 ord0537 4988 8783
run_one ord0502 ord0502 4985 8780
echo CUR16_NEIGHBORS_DONE
