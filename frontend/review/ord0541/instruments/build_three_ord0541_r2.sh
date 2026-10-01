#!/bin/bash
# ORD-0541 r2 -- rebuild the three generations from the commits this delivery actually names, serially.
# Serial because each build junctions the repo's shared node_modules and two `npm run build` passes over
# one junction interleave their writes.
set -u
cd /d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
run() {
  env -u HTTP_PROXY -u HTTPS_PROXY "$PY" cmdr_build_bundle_r1.py --sha "$1" --tag "$2" > "_b_$2.log" 2>&1
  echo "$2 rc=$? $(tail -1 "_b_$2.log")"
}
run 9f5bac8c4729b4c87ce9df22429d546fd9ef33d9 ord0541c
run 1c785a2d897888bb4089f7a324a3934f85f5f016 ord0541b
run 2ad3e4be3b4477e171f6ce9aed9e8840e84c7769 ord0541m
echo BUILDS_R2_DONE
