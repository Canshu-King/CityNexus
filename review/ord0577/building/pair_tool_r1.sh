set -e
R="D:/moodle/_qoder_b_ord0417_20260928/run"
S="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
cd "$R"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8
cp "$R/_shell_union_fixed.tsx" "$S"
echo "### with the union sidebar: $(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"
ORD0512_PORTS="5244,5245" timeout 2400 python ord0512_run_gate_r1.py ord0577entrysets_r2 e2e/qoder-8ac89982-ord0577-entry-sets-match-r1.spec.ts --reporter=line > _ord0577_entrysets_gate.out 2>&1 || true
tail -2 _ord0577_entrysets_gate.out

cp "$R/_shell_union_base.tsx" "$S"
echo "### tip bytes (sidebar still desktop-only): $(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"
ORD0512_PORTS="5246,5247" timeout 2400 python ord0512_run_gate_r1.py ord0577entrysets_counter2 e2e/qoder-8ac89982-ord0577-entry-sets-match-r1.spec.ts --reporter=line > _ord0577_entrysets_counter.out 2>&1 || true
tail -2 _ord0577_entrysets_counter.out

cp "$R/_shell_union_fixed.tsx" "$S"
echo "restored=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"

echo "### typecheck"
cd D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend
timeout 600 npm run typecheck:all > "$R/_ord0577_entrysets_tsc.out" 2>&1 || true
echo "TSC_RC=$?" | tee -a "$R/_ord0577_entrysets_tsc.out"