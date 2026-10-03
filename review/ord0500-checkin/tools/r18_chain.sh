set -eo pipefail
PY="D:/moodle/CityNexus/.venv/Scripts/python.exe"
cd /d/moodle/_qoder_phone_ord0485_20260930
TIP_REF=refs/heads/mirror/integration-frontend-apple-pass1
SHORT=r18
GEN=r17
MY_REF=refs/heads/review/newlane-ord0500-phone-checkin-entry-$SHORT
GIT="env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=* git"
export CITATION_GATE_OUT=citation_gate_$GEN.json CITATION_GATE_TOOL=citation_gate_$GEN
export CITATION_MUT_OUT=citation_gate_${GEN}_mutants.json CITATION_MUT_TOOL=citation_gate_${GEN}_mutants
export CITATION_AUDIT_OUT=citation_audit_$GEN.json CITATION_AUDIT_TOOL=citation_audit_$GEN
export RECHECK_OUT=day26_anchor_recheck_$GEN.json RECHECK_TOOL=anchor_recheck_$GEN
export RECHECK_RECEIPT=day26_anchor_recheck_$GEN.json
export AUD_RECEIPT=citation_audit_$GEN.json ARM_RECEIPT=branch_emit_arm_$GEN.json
export FMT_RECEIPT=fmt_lint_$GEN.json EXPOSURE_GEN=r17
export BRANCH_EMIT_OUT=branch_emit_arm_$GEN.json BRANCH_EMIT_TOOL=branch_emit_arm_$GEN
export COLLECT_OUT=pytest_collectonly_$GEN.json COLLECT_TOOL=pytest_collectonly_$GEN
export BRANCH_EMIT_EXCLUDE=$SHORT
export FMTLINT_OUT=fmt_lint_$GEN.json FMTLINT_TOOL=fmt_lint_$GEN
LINTFILES="tools/r10_block.py tools/r9_block.py tools/branch_emit_arm_r16.py tools/stage_readings_r6.py tools/r6_coordinates.py tools/recheck_r14.py tools/collect_count_r16.py tools/citation_gate_r9.py tools/citation_gate_r10_mutants.py tools/citation_audit_r8.py tools/landing_r6.py tools/pytest_r6.py tools/sweep_r6.py tools/build_faces_r6.py tools/exposure_pair_r17.py tools/reanchor_r8.py"

# 0. lint, then commit the re-anchored comment together with this hand's tools and receipts
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -2
$PY tools/stage_readings_r6.py 2>&1 | tail -2
cd wt22
git add backend/tests/test_qoder_ord0500_journey_refusal.py review/ord0500-checkin
git commit -q -F ../run/commit_r18_msg.txt
echo "R17D_HEAD=$(git rev-parse HEAD)"
$GIT push -q origin HEAD:$MY_REF
cd ..
$GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF $MY_REF | cut -c1-72

# 1. every instrument re-run against that head
$PY tools/citation_gate_r9.py 2>&1 | head -1
$PY tools/citation_gate_r10_mutants.py 2>&1 | tail -1
$PY tools/citation_audit_r8.py > /tmp/aud17d.txt 2>&1; head -1 /tmp/aud17d.txt
$PY tools/recheck_r14.py
R6_BASE_TIP=$($GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF | cut -f1) \
  $PY tools/pytest_r6.py > run/r17d_pytest.log 2>&1
$PY tools/checkin_copy_rows_r6.py > run/r17d_rows.log 2>&1
$PY tools/checkin_copy_rows_mutants_r6.py > run/r17d_rows_mut.log 2>&1
$PY tools/collect_count_r16.py 2>&1 | tail -1
$PY tools/branch_emit_arm_r16.py 2>&1 | tail -4
$PY tools/landing_r6.py > run/r17d_landing.log 2>&1
$PY tools/r6_coordinates.py 2>&1 | tail -2
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -2

# 2. the door's arm: one forced red, no receipt touched, page must not exist afterwards
rm -f run/${SHORT}_READINGS_RED.json run/${GEN}_block_page.md
if R10_GEN=$GEN R10_REF_GEN=$SHORT R10_FORCE_RED=引文闸判语 \
   $PY tools/r10_block.py > /tmp/red17d.txt 2>&1 < /dev/null; then
  echo "ABORT_FORCE_RED_DID_NOT_FIRE"; exit 3
fi
grep -o "ABORT_READINGS_RED.*" /tmp/red17d.txt | head -1
ls -l run/${SHORT}_READINGS_RED.json | awk '{print "failure sheet bytes", $5}'
test ! -f run/${GEN}_block_page.md || { echo "ABORT_PAGE_BUILT_ON_RED"; exit 4; }

# 3. the real page, then the coordinate gate over it
R10_GEN=$GEN R10_REF_GEN=$SHORT $PY tools/r10_block.py 2>&1 | tail -3
$PY "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_block_precheck_r1.py" \
  "D:/moodle/_qoder_phone_ord0485_20260930/run/${GEN}_block_page.md" --expect-clean 2>&1 | tail -12
