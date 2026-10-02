#!/bin/bash
# day24 打卡门新句屏读 -- three runs, three stores, one bundle, in the order that costs least first.
#
# Separate runs rather than one suite because the two real arms write a stamp and the intercepted arms
# must not be read next to them: a shared store would make "exactly one notice on the screen" a claim
# about whoever pressed last. Every pair was proved before the first click
# (receipts/day24_stack_ownership_r1.json: served entry asset == disk bytes, and each api answers only
# its own marker city).
set -u
FRONT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend
WT=/d/moodle/_qoder_e766b154_ord0472_20260930/wt
LANE=/d/moodle/_qoder_e766b154_ord0528_20261001
READINGS=$WT/frontend/review/checkin-words-day24/readings
HHMM=$(date +%H%M)
cd "$FRONT" || exit 1

run_one() { # mode port locale stem
  local mode=$1 port=$2 locale=$3 stem=$4
  env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY="*" \
    CITYNEXUS_E766_WORDS_BASE="http://127.0.0.1:$port" \
    CITYNEXUS_E766_WORDS_MODE="$mode" \
    CITYNEXUS_E766_WORDS_LOCALE="$locale" \
    CITYNEXUS_E766_WORDS_OUT="$READINGS" \
    cmd //c "node_modules\\.bin\\playwright.CMD test -c playwright.e766-checkin-words-P.config.ts" \
    > "$LANE/run/day24_words_$stem.log" 2>&1
  echo "$stem rc=$? base=$port $(grep -aoE '[0-9]+ passed|[0-9]+ failed|[0-9]+ error' "$LANE/run/day24_words_$stem.log" | tr '\n' ' ')"
}

run_one fake 4992 zh-CN fake
run_one real 4990 zh-CN real_zh
run_one real 4991 en real_en
ls "$READINGS" | wc -l
echo "reading_files_above"
echo DAY24_WORDS_DONE
