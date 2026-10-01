#!/bin/bash
# 前置单 control -- re-run the two footprint/map neighbours against MY OWN lane stack, on the same
# bundle bytes day15 serves, but over a private database whose demo trip was never binned.
#
# Why: the ord0530 instrument sends the trip it reads through the product's own DELETE door (its file
# header says the arm order is load-bearing), and that ran on the commander's shared canary at
# 02:51:52. ord0537 ran after it. So ord0537's four reds have two candidate causes -- the generation, or
# the empty store my own previous run produced -- and only a control run over an intact store can tell
# them apart. The front here is `_build_ord0541c`, whose entry asset bytes were measured equal to the
# bytes :4783 serves (run/day15_stack_proof_r1.json), so the generation is the same and only the store
# differs.
set -u
FRONT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
HHMM=$(date +%H%M)
cd "$FRONT" || exit 1

run_one() { # neighbor-key file-stem
  local key=$1 stem=$2
  local evid="$LANE/run/control_$stem"
  mkdir -p "$evid"
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E2E_PORT=4980 \
    CITYNEXUS_BACKEND_PORT=8774 \
    CITYNEXUS_E766_NEIGHBOR=$key \
    CITYNEXUS_E2E_RUN_ID="control-e766b154-$stem-$HHMM" \
    CITYNEXUS_EVIDENCE_DIR="$evid" \
    CITYNEXUS_ORD0502_OUT="$evid" \
    CITYNEXUS_E766_REPORT="$LANE/run/report_control_$stem.json" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.day15-neighbors-P.config.ts" \
    > "$LANE/run/gate_control_$stem.log" 2>&1
  echo "$stem rc=$? $(grep -aoE '[0-9]+ passed|[0-9]+ failed' "$LANE/run/gate_control_$stem.log" | tr '\n' ' ')"
}

run_one ord0537 ord0537
run_one ord0497 ord0497
echo CONTROL_DONE
