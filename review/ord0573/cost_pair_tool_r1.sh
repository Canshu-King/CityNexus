set -e
cd D:/moodle/_qoder_b_ord0417_20260928/run
SHELL_REL="D:/moodle/_qoder_b_ord0417_20260928/hubcut/frontend/src/app/V8Experience.tsx"
EV="D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/e2e"
export ORD0512_TREE="D:/moodle/_qoder_b_ord0417_20260928/hubcut"
export PYTHONIOENCODING=utf-8
ROLES_IN=5d62f7bc78a58369d871a37c820e0b9a1a6076e6
ROLES_OUT=62aa8b83c35a5d408170bc2ad4470ae70e78a136

for gen in in out; do
  if [ "$gen" = "in" ]; then SRC=_shell_roles_in.tsx; WANTED=$ROLES_IN; PORTS="5186,5187"; RID=ord0573costin_r3; else SRC=_shell_roles_out.tsx; WANTED=$ROLES_OUT; PORTS="5188,5189"; RID=ord0573costout_r3; fi
  cp "$SRC" "$SHELL_REL"
  h=$(git -C D:/moodle/CityNexus hash-object --no-filters "$SHELL_REL")
  echo "GEN=$gen blob=$h want=$WANTED agree=$([ "$h" = "$WANTED" ] && echo True || echo FALSE)"
  [ "$h" = "$WANTED" ] || { echo "ABORT: tree is not the bytes this generation claims"; exit 6; }
  rm -f "$EV/ord0573cost_en.json" "$EV/ord0573cost_zh.json"
  ORD0512_PORTS="$PORTS" timeout 900 python ord0512_run_gate_r1.py $RID e2e/qoder-8ac89982-ord0573-upstream-locator-forms-r1.spec.ts --reporter=line > _ord0573cost_$gen.out 2>&1 || true
  tail -3 _ord0573cost_$gen.out
  for arm in zh en; do
    cp "$EV/ord0573cost_$arm.json" "$EV/ord0573cost_roles_${gen}_$arm.json"
  done
  ls -la "$EV"/ord0573cost_roles_${gen}_*.json
done

cp _shell_roles_in.tsx "$SHELL_REL"
h3=$(git -C D:/moodle/CityNexus hash-object --no-filters "$SHELL_REL")
echo "RESTORED blob=$h3 expect=$ROLES_IN agree=$([ "$h3" = "$ROLES_IN" ] && echo True || echo FALSE)"
