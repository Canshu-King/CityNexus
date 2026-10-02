set -e
PY="D:/moodle/CityNexus/.venv/Scripts/python.exe"
cd /d/moodle/_qoder_phone_ord0485_20260930
TIP_REF=refs/heads/mirror/integration-frontend-apple-pass1
MY_REF=refs/heads/review/newlane-ord0500-phone-checkin-entry-r16
SHORT=r16
GEN=r14
GIT="env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=* git"

# every instrument writes the same generation names this family already uses, so a re-cut never requires
# renaming anything downstream; only the ref number moves
export CITATION_GATE_OUT=citation_gate_$GEN.json CITATION_GATE_TOOL=citation_gate_$GEN
export CITATION_MUT_OUT=citation_gate_${GEN}_mutants.json CITATION_MUT_TOOL=citation_gate_${GEN}_mutants
export CITATION_AUDIT_OUT=citation_audit_$GEN.json CITATION_AUDIT_TOOL=citation_audit_$GEN
export RECHECK_OUT=day25_anchor_recheck_$GEN.json RECHECK_TOOL=anchor_recheck_$GEN
export BRANCH_EMIT_OUT=branch_emit_arm_$GEN.json BRANCH_EMIT_TOOL=branch_emit_arm_$GEN
export COLLECT_OUT=pytest_collectonly_$GEN.json COLLECT_TOOL=pytest_collectonly_$GEN
export BRANCH_EMIT_EXCLUDE=$SHORT

# 0. the format-arity lint runs first: it writes its own receipt (which gets staged and cited by blob)
#    and refuses to pass when the emitter has a slot with no argument -- which is how a page that was
#    already pushed dies mid-sentence.  Then the two instruments whose output the page cites by blob run
#    once BEFORE the commit, so the branch carries a copy; the fresh copies are taken again in step 2.
export FMTLINT_OUT=fmt_lint_$GEN.json FMTLINT_TOOL=fmt_lint_$GEN
LINTFILES="tools/r10_block.py tools/r9_block.py tools/branch_emit_arm_r16.py tools/stage_readings_r6.py tools/r6_coordinates.py tools/recheck_r14.py tools/collect_count_r16.py tools/citation_gate_r9.py tools/citation_gate_r10_mutants.py tools/citation_audit_r8.py tools/landing_r6.py tools/pytest_r6.py tools/sweep_r6.py tools/build_faces_r6.py"
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -3
$PY tools/collect_count_r16.py 2>&1 | tail -1
$PY tools/branch_emit_arm_r16.py 2>&1 | tail -4

# 1. this hand's tools, receipts and the refusal door's sheet go into the branch; the ref moves one on
$PY tools/stage_readings_r6.py 2>&1 | tail -2
cd wt22
git add review/ord0500-checkin          # only this order's own folder
git commit -q -F ../run/commit_r16_msg.txt
R16=$(git rev-parse HEAD)
echo "R16_HEAD=$R16"
$GIT push -q origin HEAD:$MY_REF
cd ..
$GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF $MY_REF | cut -c1-72

# 2. every instrument re-run against that head, so no sentence in the page is a reading of an older one
$PY tools/citation_gate_r9.py 2>&1 | head -1
$PY tools/citation_gate_r10_mutants.py 2>&1 | tail -1
$PY tools/citation_audit_r8.py > /tmp/aud16.txt 2>&1; head -1 /tmp/aud16.txt
$PY tools/recheck_r14.py
$PY tools/branch_emit_arm_r16.py 2>&1 | tail -4
R6_BASE_TIP=$($GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF | cut -f1) \
  $PY tools/pytest_r6.py > /dev/null 2>&1
$PY tools/checkin_copy_rows_r6.py > /dev/null 2>&1
$PY tools/checkin_copy_rows_mutants_r6.py > /dev/null 2>&1
$PY tools/collect_count_r16.py 2>&1 | tail -1
$PY tools/landing_r6.py > /dev/null 2>&1
$PY tools/r6_coordinates.py 2>&1 | tail -2
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -2

# 3. the door's own arm on this head: force one check red without touching any receipt
rm -f run/${SHORT}_READINGS_RED.json run/${GEN}_block_page.md
if R10_GEN=$GEN R10_REF_GEN=$SHORT R10_FORCE_RED=引文闸判语 $PY tools/r10_block.py > /tmp/red16.txt 2>&1 < /dev/null; then
  echo "ABORT_FORCE_RED_DID_NOT_FIRE -- the door let a red generation build a page"
  exit 3
fi
grep -o "ABORT_READINGS_RED.*" /tmp/red16.txt | head -1
ls -l run/${SHORT}_READINGS_RED.json | awk '{print "failure sheet bytes", $5}'
test ! -f run/${GEN}_block_page.md || { echo "ABORT_PAGE_BUILT_ON_RED"; exit 4; }

# 4. the real page, same instruments, force removed; then the coordinate gate over it
R10_GEN=$GEN R10_REF_GEN=$SHORT $PY tools/r10_block.py 2>&1 | tail -3
$PY "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_block_precheck_r1.py" \
  "D:/moodle/_qoder_phone_ord0485_20260930/run/${GEN}_block_page.md" --expect-clean 2>&1 | tail -8
