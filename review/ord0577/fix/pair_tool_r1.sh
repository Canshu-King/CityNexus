set -e
R="D:/moodle/_qoder_b_ord0417_20260928/run"
S="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
cd "$R"
cp "$S" "$R/_shell_0577_fixed.tsx"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8

echo "### fixed bytes"
h=$(git -C D:/moodle/CityNexus hash-object --no-filters "$R/_shell_0577_fixed.tsx"); echo "blob=$h"
ORD0512_PORTS="5208,5209" timeout 1200 python ord0512_run_gate_r1.py ord0577fix_r1 e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts --reporter=line > _ord0577_fixed_gate.out 2>&1 || true
tail -2 _ord0577_fixed_gate.out

echo "### pre-fix bytes (the tip's own copy)"
cp "$R/_shell_0577_prefix.tsx" "$S"
h2=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S"); echo "blob=$h2"
ORD0512_PORTS="5210,5211" timeout 1200 python ord0512_run_gate_r1.py ord0577fix_counter e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts --reporter=line > _ord0577_fixed_counter.out 2>&1 || true
tail -2 _ord0577_fixed_counter.out

cp "$R/_shell_0577_fixed.tsx" "$S"
h3=$(git -C D:/moodle/CityNexus hash-object --no-filters "$S")
echo "restored=$h3 agree=$([ "$h3" = "$h" ] && echo True || echo FALSE)"

echo "### typecheck"
cd D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend
timeout 600 npm run typecheck:all > "$R/_ord0577_fixed_tsc.out" 2>&1 || true
echo "TSC_RC=$?" | tee -a "$R/_ord0577_fixed_tsc.out"
tail -2 "$R/_ord0577_fixed_tsc.out"
