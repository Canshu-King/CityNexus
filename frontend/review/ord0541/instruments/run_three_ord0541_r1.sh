#!/bin/bash
# ORD-0541 lane -- run the same ruler against the three generations, in order, and print the counts.
# One ruler, three bundles: the base generation shows what the line does when it writes before it
# asks, the candidate shows the delivered behaviour, and the mutant shows the tier arm going red on a
# bundle that reuses any standing row. Nothing here is a mock: each front serves its own built bundle
# over its own database, and the ownership readings in stack_ord0541.json name which is which.
set -u
cd /d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
REPO=/d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/ord0541
# PASS names which trip this is: the same ruler over the same three bundles is run twice on purpose, and
# a state-sensitive arm that answers differently on the two trips has to be reported as two readings.
PASS=${PASS:-r1}

run() { # port gen evidence-dir
  local port=$1 gen=$2 evid=$3
  mkdir -p "$evid"
  env -u HTTP_PROXY -u HTTPS_PROXY \
    CITYNEXUS_ORD0541_FRONT=$port \
    CITYNEXUS_ORD0541_GEN=$gen \
    CITYNEXUS_ORD0541_EVIDENCE="$evid" \
    CITYNEXUS_ORD0541_REPORT="$LANE/run/report_ord0541_${gen}_${PASS}.json" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.ord0541-P.config.ts" \
    > "$LANE/run/gate_${gen}_${PASS}.log" 2>&1
  echo "$gen $PASS rc=$? $(grep -aoE '[0-9]+ passed|[0-9]+ failed' "$LANE/run/gate_${gen}_${PASS}.log" | tr '\n' ' ')"
}

run 4980 candidate "$REPO/run/candidate_$PASS"
run 4981 base "$REPO/run/base_$PASS"
run 4982 mutant "$REPO/run/mutant_$PASS"
echo ALL_RUNS_DONE
