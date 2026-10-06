set -e
R="D:/moodle/_qoder_b_ord0417_20260928/run"
S="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
cd "$R"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8
cp "$S" "$R/_shell_0573copy_fixed.tsx"
echo "### fixed bytes: $(git -C D:/moodle/CityNexus hash-object --no-filters "$R/_shell_0573copy_fixed.tsx")"

ORD0512_PORTS="5236,5237" timeout 1500 python ord0512_run_gate_r1.py ord0573copy_r1 e2e/qoder-8ac89982-ord0573-sections-copy-r1.spec.ts --reporter=line > _ord0573_copy_gate.out 2>&1 || true
tail -2 _ord0573_copy_gate.out

cp "$R/_shell_recut_base.tsx" "$S"
echo "### counter bytes (the tip's own shell, literals back): $(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"
ORD0512_PORTS="5238,5239" timeout 1500 python ord0512_run_gate_r1.py ord0573copy_counter e2e/qoder-8ac89982-ord0573-sections-copy-r1.spec.ts --reporter=line > _ord0573_copy_counter.out 2>&1 || true
tail -2 _ord0573_copy_counter.out

cp "$R/_shell_0573copy_fixed.tsx" "$S"
echo "restored=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"

echo "### typecheck"
cd D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend
timeout 600 npm run typecheck:all > "$R/_ord0573_copy_tsc.out" 2>&1 || true
echo "TSC_RC=$?" | tee -a "$R/_ord0573_copy_tsc.out"