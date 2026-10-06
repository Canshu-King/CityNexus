set -e
R="D:/moodle/_qoder_b_ord0417_20260928/run"
S="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
cd "$R"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8
cp "$R/_shell_0577_layers_fixed.tsx" "$S"
echo "### fixed bytes: $(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"
ORD0512_PORTS="5214,5215" timeout 1800 python ord0512_run_gate_r1.py ord0577layersfix_r1 e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts --reporter=line > _ord0577_layers_fixed_gate.out 2>&1 || true
tail -2 _ord0577_layers_fixed_gate.out

cp "$R/_shell_0577_prefix.tsx" "$S"
echo "### pre-fix bytes: $(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"
ORD0512_PORTS="5216,5217" timeout 1800 python ord0512_run_gate_r1.py ord0577layersfix_counter e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts --reporter=line > _ord0577_layers_fixed_counter.out 2>&1 || true
tail -2 _ord0577_layers_fixed_counter.out

cp "$R/_shell_0577_layers_fixed.tsx" "$S"
echo "restored=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"

echo "### typecheck"
cd D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend
timeout 600 npm run typecheck:all > "$R/_ord0577_layers_fixed_tsc.out" 2>&1 || true
echo "TSC_RC=$?" | tee -a "$R/_ord0577_layers_fixed_tsc.out"
tail -2 "$R/_ord0577_layers_fixed_tsc.out"
