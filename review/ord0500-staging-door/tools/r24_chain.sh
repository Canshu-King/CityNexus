# ORD-0500 r24 chain: same steps as r19c, but the staging leg runs through stage_readings_r7.py --
# the writer that carries the refusal door inside it (r6 landed before the door existed and its path
# is an instrument file, so it is not rewritten; the family's chain moves to r7 instead).
set -eo pipefail
# ORD-0500 r19 recut: the line moved after this hand's page was emitted, so every tip-dependent
# instrument is re-run and the page re-emitted through the refusal door.  No product byte is touched
# here (main.py and the five other paths this order speaks about were checked per path with
# `git rev-parse <tip>:<path>` before starting), and no slow instrument is re-taken: the two build
# faces, the four 390x844 screen reads and the Q64 pair stay carried, each with its own staleness arm
# inside the emitter (ABORT_FACES_STALE / ABORT_PAIR_STALE).
PY="D:/moodle/CityNexus/.venv/Scripts/python.exe"
cd /d/moodle/_qoder_phone_ord0485_20260930
TIP_REF=refs/heads/mirror/integration-frontend-apple-pass1
SHORT=r24
GEN=r24
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
export REFDISC_RECEIPT=ref_discovery_arm_$GEN.json REFDISC_OUT=ref_discovery_arm_$GEN.json REFDISC_TOOL=ref_discovery_arm_$GEN
LINTFILES="tools/r10_block.py tools/r9_block.py tools/branch_emit_arm_r16.py tools/stage_readings_r7.py tools/r6_coordinates.py tools/recheck_r14.py tools/collect_count_r16.py tools/citation_gate_r9.py tools/citation_gate_r10_mutants.py tools/citation_audit_r8.py tools/landing_r6.py tools/pytest_r6.py tools/sweep_r6.py tools/build_faces_r6.py tools/exposure_pair_r17.py tools/reanchor_r8.py tools/ref_discovery_arm_r18.py"

# 1. tool bytes first: the door compares the emitter inside the ref against the program that writes the
#    page, so a tool edit has to be behind the readings, never after them.
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -2
$PY tools/stage_readings_r7.py 2>&1 | tail -2
cd wt22
git add review/ord0500-checkin
git commit -q -F ../run/commit_r24_tools_msg.txt
echo "R19C_TOOLS_HEAD=$(git rev-parse HEAD)"
$GIT push -q origin HEAD:$MY_REF
cd ..
$GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF $MY_REF | cut -c1-72

# 2. every tip-dependent instrument, re-run against the line as it now stands
$PY tools/citation_gate_r9.py 2>&1 | head -1
$PY tools/citation_gate_r10_mutants.py 2>&1 | tail -1
$PY tools/citation_audit_r8.py > /tmp/aud19c.txt 2>&1; head -1 /tmp/aud19c.txt
$PY tools/recheck_r14.py 2>&1 | tail -1
$PY tools/ref_discovery_arm_r18.py > run/r19c_refdisc.log 2>&1
tail -1 run/r19c_refdisc.log
R6_BASE_TIP=$($GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF | cut -f1) \
  $PY tools/pytest_r6.py > run/r19c_pytest.log 2>&1
tail -1 run/r19c_pytest.log
$PY tools/checkin_copy_rows_r6.py > run/r19c_rows.log 2>&1
tail -1 run/r19c_rows.log
$PY tools/checkin_copy_rows_mutants_r6.py > run/r19c_rows_mut.log 2>&1
tail -1 run/r19c_rows_mut.log
$PY tools/collect_count_r16.py 2>&1 | tail -1
$PY tools/branch_emit_arm_r16.py 2>&1 | tail -4

# 3. the readings go into the ref, then the read-only landing ruler and the coordinate list run on that head
$PY tools/stage_readings_r7.py 2>&1 | tail -2
cd wt22
git add review/ord0500-checkin
git commit -q -F ../run/commit_r24_readings_msg.txt
echo "R19C_HEAD=$(git rev-parse HEAD)"
$GIT push -q origin HEAD:$MY_REF
cd ..
$GIT -C /d/moodle/CityNexus ls-remote --refs origin $TIP_REF $MY_REF | cut -c1-72
$PY tools/landing_r6.py > run/r19c_landing.log 2>&1
$PY tools/r6_coordinates.py 2>&1 | tail -2
$PY tools/fmt_lint_r16.py $LINTFILES 2>&1 | tail -2

# 4. the door's arm: one forced red, no receipt touched, the page must not exist afterwards
rm -f run/${SHORT}_READINGS_RED.json run/${GEN}_block_page.md
if R10_GEN=$GEN R10_REF_GEN=$SHORT R10_FORCE_RED=引文闸判语 \
   $PY tools/r10_block.py > /tmp/red19c.txt 2>&1 < /dev/null; then
  echo "ABORT_FORCE_RED_DID_NOT_FIRE"; exit 3
fi
grep -o "ABORT_READINGS_RED.*" /tmp/red19c.txt | head -1
ls -l run/${SHORT}_READINGS_RED.json | awk '{print "failure sheet bytes", $5}'
test ! -f run/${GEN}_block_page.md || { echo "ABORT_PAGE_BUILT_ON_RED"; exit 4; }

# 5. the real page, then the coordinate gate over it
R10_GEN=$GEN R10_REF_GEN=$SHORT $PY tools/r10_block.py 2>&1 | tail -3
$PY "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_block_precheck_r1.py" \
  "D:/moodle/_qoder_phone_ord0485_20260930/run/${GEN}_block_page.md" --expect-clean 2>&1 | tail -12
