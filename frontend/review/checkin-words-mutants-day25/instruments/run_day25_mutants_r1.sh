#!/bin/bash
# day25 counter-arm run (lane e766b154) -- CMDR 02:45 item 6: mutate the product side so the
# targetRequired / targetAmbiguous sentences disappear, and show the landed screen-read reddens.
#
# Order of work, and why:
#   base bundle (tip bytes) -> arms green
#   M1 (two CHECKIN_REFUSAL_COPY rows removed) built from its own commit -> arms red, control green
#   restore -> arms green again on the base bundle (proves the red was the mutation, not drift)
#   M2 (both rows emptied) built from its own commit -> arms red again, by a different assertion
#   restore -> byte-identical, verified by sha256
#
# Each mutant is committed to a local ref (refs/e766-mut/*) because the bundle builder reads from git,
# not from a dirty tree. Nothing here is pushed, and the commander's :4783/:4787 are never touched.
set -u
WT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
FRONT=$WT/frontend
EVID=$WT/frontend/review/checkin-words-mutants-day25
BC=/d/moodle/_qoder_cmdr_ref_20260921/live_checks
PY=/d/moodle/CityNexus/.venv/Scripts/python.exe
TIP=06ad00b0267c2bef08d4cdcbae2e5a206ded8666
EXPORT=$LANE/export_day25/backend

echo "== step 1: backend export at the tip"
mkdir -p "$LANE/export_day25"
NO_PROXY="*" git -C /d/moodle/CityNexus archive $TIP backend data contracts tools \
  | tar -x -C "$LANE/export_day25"
echo "export_rc=${PIPESTATUS[1]} size=$(du -sk "$LANE/export_day25" 2>/dev/null | cut -f1)KB"

echo "== step 2: one private store (the intercepted arms write nothing)"
rm -f "$LANE/run/day25_mut_fake.db"
env -u HTTP_PROXY -u HTTPS_PROXY python "$LANE/tools/make_lane_db_r3.py" run/day25_mut_fake CNX-DAY25-MUT \
  > "$LANE/run/day25_mut_db.log" 2>&1
mv -f "$LANE/run/day25_mut_fake" "$LANE/run/day25_mut_fake.db" 2>/dev/null
grep -a "marker_rows_in_my_copy\|TARGET" "$LANE/run/day25_mut_db.log"

start_api() { # port db export
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" PYTHONPATH="$2" \
    CITYNEXUS_DATABASE_URL="sqlite:///D:/moodle/_qoder_e766b154_ord0528_20261001/run/$3.db" \
    CITYNEXUS_DEMO_MODE=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$1" \
    > "$LANE/run/day25_mut_api_$1.log" 2>&1 &
}
start_front() { # port dist
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" "$PY" "$BC/cmdr_static_api_proxy_r1.py" \
    --dist "$2" --port "$1" --api 8793 > "$LANE/run/day25_mut_front_$1.log" 2>&1 &
}

echo "== step 3: api 8793 on the tip's backend tree"
start_api 8793 "$EXPORT" day25_mut_fake
sleep 18
echo "api_startup=$(grep -ac 'Application startup complete' $LANE/run/day25_mut_api_8793.log)"

arms() { # generation front
  local gen=$1 port=$2
  mkdir -p "$EVID/readings/$gen"
  for state in targetRequired targetAmbiguous journeyInBin; do
    ( cd "$FRONT" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
        CITYNEXUS_E766_WORDS_BASE="http://127.0.0.1:$port" \
        CITYNEXUS_E766_WORDS_MODE=fake \
        CITYNEXUS_E766_WORDS_LOCALE=both \
        CITYNEXUS_E766_WORDS_OUT="$EVID/readings/$gen" \
        cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.e766-checkin-words-P.config.ts -g $state" \
        > "$LANE/run/day25_mut_${gen}_$state.log" 2>&1 )
    echo "   $gen/$state rc=$? $(grep -aoE '[0-9]+ passed|[0-9]+ failed' "$LANE/run/day25_mut_${gen}_$state.log" | tr '\n' ' ')"
  done
}

echo "== step 4: base generation (tip bundle)"
start_front 4993 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_day25e766\\frontend\\dist"
sleep 8
arms base 4993

echo "== step 5: M1 -- mapping rows removed"
( cd "$EVID" && env -u HTTP_PROXY python mutate_target_sentences_r1.py apply M1 )
( cd "$EVID" && env -u HTTP_PROXY python stage_mutant_commit_r1.py M1 ) | tee -a "$LANE/run/day25_mut_commits.txt"
( cd "$EVID" && env -u HTTP_PROXY python mutate_target_sentences_r1.py restore )
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" python "$BC/cmdr_build_bundle_r1.py" \
  --sha "$(grep -ao 'M1 [0-9a-f]\{40\}' "$LANE/run/day25_mut_commits.txt" | awk '{print $2}')" --tag mut1e766 \
  > "$LANE/run/day25_build_mut1.log" 2>&1
echo "build_mut1_rc=$? $(tail -2 "$LANE/run/day25_build_mut1.log" | head -1)"
start_front 4994 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_mut1e766\\frontend\\dist"
sleep 8
arms m1 4994

echo "== step 6: revert confirmation on the base bundle"
arms m1_revert 4993

echo "== step 7: M2 -- both rows emptied"
( cd "$EVID" && env -u HTTP_PROXY python mutate_target_sentences_r1.py apply M2 )
( cd "$EVID" && env -u HTTP_PROXY python stage_mutant_commit_r1.py M2 ) | tee -a "$LANE/run/day25_mut_commits.txt"
( cd "$EVID" && env -u HTTP_PROXY python mutate_target_sentences_r1.py restore )
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" python "$BC/cmdr_build_bundle_r1.py" \
  --sha "$(grep -ao 'M2 [0-9a-f]\{40\}' "$LANE/run/day25_mut_commits.txt" | awk '{print $2}')" --tag mut2e766 \
  > "$LANE/run/day25_build_mut2.log" 2>&1
echo "build_mut2_rc=$? $(tail -2 "$LANE/run/day25_build_mut2.log" | head -1)"
start_front 4995 "D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_build_mut2e766\\frontend\\dist"
sleep 8
arms m2 4995

echo "== step 8: ownership across the three bundles"
( cd "$EVID" && env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" python mutant_stack_ownership_r1.py )
echo "ownership_rc=$?"

echo "== step 9: worktree back to tip bytes?"
( cd "$EVID" && env -u HTTP_PROXY python mutate_target_sentences_r1.py status )
( cd "$WT" && git status --porcelain -- frontend/src | head -3; echo "src_dirty_lines_above" )
echo DAY25_MUTANTS_DONE
