#!/usr/bin/env bash
# ORD-0384 -- re-run the gate and the compile arm on the delivered head, in one place so a quoting
# mistake in an ad-hoc command cannot silently skip a step. Each step prints its own exit code.
set -u
HEAD_SHA="$1"
cd /d/moodle/_qoder_n3_ord0357 || exit 2

echo "=== GATE on ${HEAD_SHA} ==="
python review/n3_e2e_r1.py --wt D:/moodle/_qoder_n3_ord0357 \
  --target e2e/qoder-ord0384-pretrip-checklist.spec.ts --tag n3 2>&1 \
  | grep -E '"run_id"|"exit_code"|"verdict"|"passed"|"failed"|"log"|"duration_s"'
GATE_RC=${PIPESTATUS[0]}
echo "GATE_RC=${GATE_RC}"

echo "=== COMPILE ARM on ${HEAD_SHA} ==="
python review/n3_0384_snap_build_r1.py "${HEAD_SHA}" 2>&1 | tail -9
SNAP_RC=${PIPESTATUS[0]}
echo "SNAP_RC=${SNAP_RC}"

if [ "${GATE_RC}" = "0" ] && [ "${SNAP_RC}" = "0" ]; then
  echo "ALL_STEPS_GREEN"
  exit 0
fi
echo "SOME_STEP_RED gate=${GATE_RC} snap=${SNAP_RC}"
exit 3
