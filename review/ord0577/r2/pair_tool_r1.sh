set -e
R="D:/moodle/_qoder_b_ord0417_20260928/run"
S="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
cd "$R"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8
cp "$S" "$R/_shell_recut_fixed.tsx"
echo "### recut fixed = $(git -C D:/moodle/CityNexus hash-object --no-filters "$R/_shell_recut_fixed.tsx")"

ORD0512_PORTS="5220,5221" timeout 1500 python ord0512_run_gate_r1.py ord0577recut_bar e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts --reporter=line > _ord0577_recut_bar_gate.out 2>&1 || true
tail -2 _ord0577_recut_bar_gate.out

cp "$R/_shell_recut_base.tsx" "$S"
ORD0512_PORTS="5222,5223" timeout 1500 python ord0512_run_gate_r1.py ord0577recut_bar_counter e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts --reporter=line > _ord0577_recut_bar_counter.out 2>&1 || true
tail -2 _ord0577_recut_bar_counter.out

cp "$R/_shell_recut_fixed.tsx" "$S"
ORD0512_PORTS="5224,5225" timeout 1800 python ord0512_run_gate_r1.py ord0577recut_layers e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts --reporter=line > _ord0577_recut_layers_gate.out 2>&1 || true
tail -2 _ord0577_recut_layers_gate.out

cp "$R/_shell_recut_base.tsx" "$S"
ORD0512_PORTS="5226,5227" timeout 1800 python ord0512_run_gate_r1.py ord0577recut_layers_counter e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts --reporter=line > _ord0577_recut_layers_counter.out 2>&1 || true
tail -2 _ord0577_recut_layers_counter.out

cp "$R/_shell_recut_fixed.tsx" "$S"
echo "restored=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S")"

echo "### typecheck"
cd D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend
timeout 600 npm run typecheck:all > "$R/_ord0577_recut_tsc.out" 2>&1 || true
echo "TSC_RC=$?" | tee -a "$R/_ord0577_recut_tsc.out"