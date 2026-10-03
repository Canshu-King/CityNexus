set -e
PY="D:/moodle/CityNexus/.venv/Scripts/python.exe"
cd /d/moodle/_qoder_phone_ord0485_20260930

# 1. the receipts and tools this hand produced go into the branch, and the branch moves one commit on
$PY tools/stage_readings_r6.py 2>&1 | head -2
cd wt22
git add review/ord0500-checkin   # only this order's own folder: no other lane's path is staged
git commit -q -F ../run/commit_r14b_msg.txt
HEAD_SHA=$(git rev-parse HEAD)
echo "R15_HEAD=$HEAD_SHA"
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" git push -q origin HEAD:refs/heads/review/newlane-ord0500-phone-checkin-entry-r15
cd ..
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" git -C /d/moodle/CityNexus ls-remote --refs origin \
  refs/heads/mirror/integration-frontend-apple-pass1 \
  refs/heads/review/newlane-ord0500-phone-checkin-entry-r15 | cut -c1-64

# 2. every instrument is re-run against that head, so the page cannot cite a reading of an older one
export CITATION_GATE_OUT=citation_gate_r14.json CITATION_GATE_TOOL=citation_gate_r14
export CITATION_MUT_OUT=citation_gate_r14_mutants.json CITATION_MUT_TOOL=citation_gate_r14_mutants
export CITATION_AUDIT_OUT=citation_audit_r14.json CITATION_AUDIT_TOOL=citation_audit_r14
$PY tools/citation_gate_r9.py 2>&1 | head -1
$PY tools/citation_gate_r10_mutants.py 2>&1 | tail -1
$PY tools/citation_audit_r8.py > /tmp/audit_final.txt 2>&1; head -1 /tmp/audit_final.txt
R6_BASE_TIP=$(git -C /d/moodle/CityNexus ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1 | cut -f1) \
  $PY tools/pytest_r6.py > /dev/null 2>&1
$PY tools/recheck_r14.py
$PY tools/landing_r6.py > /dev/null 2>&1
$PY tools/r6_coordinates.py 2>&1 | tail -2

# 3. the refusal door's own arm: force one check red without touching any receipt, and show the page
#    refuses to exist and leaves only the named failure sheet
rm -f run/r15_READINGS_RED.json run/r14_block_page.md
if R10_GEN=r14 R10_REF_GEN=r15 AUD_RECEIPT=citation_audit_r14.json \
   RECHECK_RECEIPT=day25_anchor_recheck_r14.json R10_FORCE_RED=引文闸判语 \
   $PY tools/r10_block.py > /tmp/force_red.txt 2>&1; then
  echo "ABORT_FORCE_RED_DID_NOT_FIRE -- the door let a red generation build a page"
  exit 3
fi
grep -o "ABORT_READINGS_RED.*" /tmp/force_red.txt | head -1
ls -l run/r15_READINGS_RED.json | awk '{print "failure sheet bytes", $5, $6, $7}'
"D:/moodle/CityNexus/.venv/Scripts/python.exe" -c "
import json;d=json.load(open('run/r15_READINGS_RED.json',encoding='utf-8'))
print('sheet verdict',d['verdict'],'failed',[c['check'] for c in d['failed_checks']],'forced',[c.get('forced') for c in d['failed_checks']])
"
test ! -f run/r14_block_page.md || { echo "ABORT_PAGE_BUILT_ON_RED"; exit 4; }

# 4. the real page, on the same instruments with the force removed
R10_GEN=r14 R10_REF_GEN=r15 AUD_RECEIPT=citation_audit_r14.json \
  RECHECK_RECEIPT=day25_anchor_recheck_r14.json $PY tools/r10_block.py 2>&1 | tail -2
$PY "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_block_precheck_r1.py" \
  "D:/moodle/_qoder_phone_ord0485_20260930/run/r14_block_page.md" --expect-clean 2>&1 | tail -5
