#!/usr/bin/env bash
# Re-run the rail-shape instrument. Its spec lives under review/ on purpose: it asserts only that
# the rail is on screen, so inside frontend/e2e/ it would be a permanently-green case in the
# acceptance suite. To run it, it is staged into e2e for the duration and removed again -- including
# on failure -- so the suite never accumulates it.
set -u
REPO=/d/moodle/_qoder_drawer_1008
SRC="$REPO/review/drawer_grouping_r1/rail_shape_probe_r1.spec.ts"
STAGED="$REPO/frontend/e2e/rail-shape-probe-r1.spec.ts"
cleanup() { rm -f "$STAGED"; }
trap cleanup EXIT
cp "$SRC" "$STAGED"
cd "$REPO/frontend" || exit 1
timeout 500 npx playwright test rail-shape-probe-r1 --project=chromium --reporter=line --workers=1 2>&1 \
  | grep -aE 'RAIL_SHAPE|passed|failed'
echo "STAGED_AND_REMOVED spec_now_in_e2e=$( [ -f "$STAGED" ] && echo yes || echo no )"
