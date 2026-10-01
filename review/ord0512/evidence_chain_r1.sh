#!/bin/sh
# ORD-0512 r1 evidence chain, one process at a time: this lane's stack owns one port pair and one
# SQLite file per run id, and the map gates are state-sensitive (a shared DB under parallel workers
# manufactures reds that belong to nobody). Each step prints its own rc; nothing here continues on a
# reverted file that failed to restore -- the reports say so.
RUN=/d/moodle/_qoder_b_ord0417_20260928/run
PROG=$RUN/ord0512_chain_r1.progress
: > "$PROG"
cd "$RUN" || exit 9

echo "== step 1: candidate, this order's own gate" >> "$PROG"
python ord0512_run_gate_r1.py ord0512a4 e2e/qoder-0512-stop-names-on-the-glass.spec.ts --reporter=line > ord0512_chain_step1.out 2>&1
echo "step1 rc=$?" >> "$PROG"

echo "== step 2: counter-examples M0..M4" >> "$PROG"
python ord0512_mutant_r1.py base_paints_no_names labels_never_paint no_crowding_rule name_replaced_by_id name_moved_into_the_pin > ord0512_chain_step2.out 2>&1
echo "step2 rc=$?" >> "$PROG"

echo "== step 3: map family on the tip's bytes" >> "$PROG"
python ord0512_family_r1.py base --revert > ord0512_chain_step3.out 2>&1
echo "step3 rc=$?" >> "$PROG"

echo "== step 4: map family on this candidate" >> "$PROG"
python ord0512_family_r1.py cand > ord0512_chain_step4.out 2>&1
echo "step4 rc=$?" >> "$PROG"

echo "CHAIN_DONE" >> "$PROG"
