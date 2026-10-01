#!/bin/sh
# ORD-0512 evidence chain r2 -- the two-sided placement rule, re-measured end to end.
# One process at a time: this lane's stack owns one port pair and one SQLite file per run id, and the
# map gates are state-sensitive, so parallel workers on a shared DB would manufacture reds that belong
# to nobody.
RUN=/d/moodle/_qoder_b_ord0417_20260928/run
PROG=$RUN/ord0512_chain_r2.progress
: > "$PROG"
cd "$RUN" || exit 9

echo "== step 1: typecheck the patched tree" >> "$PROG"
(cd /d/moodle/_qoder_b_ord0417_20260928/ord0512cut_1c785a2d/frontend && npm run typecheck:all) > ord0512_chain_r2_step1.out 2>&1
echo "step1 rc=$?" >> "$PROG"

echo "== step 2: this order's gate on the r2 bytes" >> "$PROG"
python ord0512_run_gate_r1.py ord0512b3 e2e/qoder-0512-stop-names-on-the-glass.spec.ts --reporter=line > ord0512_chain_r2_step2.out 2>&1
echo "step2 rc=$?" >> "$PROG"

echo "== step 3: counter-examples on the r2 bytes (control + five mutants)" >> "$PROG"
ORD0512_MUT_GEN=r2 python ord0512_mutant_r1.py base_paints_no_names labels_never_paint no_crowding_rule name_replaced_by_id name_moved_into_the_pin one_sided_placement_only > ord0512_chain_r2_step3.out 2>&1
echo "step3 rc=$?" >> "$PROG"

echo "== step 4: map family on the r2 candidate (base reading is ord0512fam_base)" >> "$PROG"
python ord0512_family_r1.py cand2 > ord0512_chain_r2_step4.out 2>&1
echo "step4 rc=$?" >> "$PROG"

echo "CHAIN_R2_DONE" >> "$PROG"
