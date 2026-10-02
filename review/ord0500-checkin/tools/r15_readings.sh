set -e
PY="D:/moodle/CityNexus/.venv/Scripts/python.exe"
cd /d/moodle/_qoder_phone_ord0485_20260930
export CITATION_GATE_OUT=citation_gate_r14.json CITATION_GATE_TOOL=citation_gate_r14
export CITATION_MUT_OUT=citation_gate_r14_mutants.json CITATION_MUT_TOOL=citation_gate_r14_mutants
export CITATION_AUDIT_OUT=citation_audit_r14.json CITATION_AUDIT_TOOL=citation_audit_r14
export RECHECK_RECEIPT=day25_anchor_recheck_r14.json AUD_RECEIPT=citation_audit_r14.json
export R10_GEN=r14 R10_REF_GEN=r15

$PY tools/citation_gate_r9.py 2>&1 | head -1
$PY tools/citation_gate_r10_mutants.py 2>&1 | tail -1
$PY tools/citation_audit_r8.py > /tmp/audit_f.txt 2>&1; head -1 /tmp/audit_f.txt
$PY tools/recheck_r14.py
R6_BASE_TIP=$(git -C /d/moodle/CityNexus ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1 | cut -f1) \
  $PY tools/pytest_r6.py > /dev/null 2>&1
$PY tools/landing_r6.py > /dev/null 2>&1
$PY tools/r6_coordinates.py 2>&1 | tail -2

# the refusal door's arm, then the real page
rm -f run/r15_READINGS_RED.json run/r14_block_page.md
if R10_FORCE_RED=引文闸判语 $PY tools/r10_block.py > /tmp/force_red.txt 2>&1; then
  echo "ABORT_DOOR_BLIND -- a forced red still built a page"; exit 3
fi
grep -o "ABORT_READINGS_RED[^\"]*" /tmp/force_red.txt | head -1
test -f run/r15_READINGS_RED.json && echo "failure sheet present, $(wc -c < run/r15_READINGS_RED.json) B"
test ! -f run/r14_block_page.md || { echo "ABORT_PAGE_BUILT_ON_RED"; exit 4; }

$PY tools/r10_block.py 2>&1 | tail -1
$PY "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_block_precheck_r1.py" \
  "D:/moodle/_qoder_phone_ord0485_20260930/run/r14_block_page.md" --expect-clean 2>&1 | tail -5
