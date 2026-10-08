#!/usr/bin/env bash
# Measure one probe on the authoritative sha and store its real stdout, then restore the lane tree.
# Absolute paths in the restore: a relative-path restore earlier in this lane silently failed and
# left the tree checked out on the old sha.
set -u
REPO=/d/moodle/_qoder_drawer_1008
SHA=2f4abb238a004a19fbde2bd3f998536dbe967ae9
SPEC=${1:?spec name}
OUT=${2:?output file}
# Resolve before any cd: the script later moves into frontend/, and a relative output path would
# then be created in the wrong directory (or fail outright).
case "$OUT" in
  /*) ;;
  *) OUT="$REPO/$OUT" ;;
esac
cp "$REPO/frontend/src/styles.css" /tmp/_ab_styles.keep
cp "$REPO/frontend/src/app/V8Experience.tsx" /tmp/_ab_v8.keep
restore() {
  cp /tmp/_ab_styles.keep "$REPO/frontend/src/styles.css"
  cp /tmp/_ab_v8.keep "$REPO/frontend/src/app/V8Experience.tsx"
  git -C "$REPO" reset -q
  echo "RESTORED src_dirty=$(git -C "$REPO" status --porcelain -- frontend/src | wc -l)"
}
trap restore EXIT
git -C "$REPO" checkout "$SHA" -- frontend/src/styles.css frontend/src/app/V8Experience.tsx
cd "$REPO/frontend" || exit 1
timeout 500 npx playwright test "$SPEC" --project=chromium --reporter=line --workers=1 2>&1 \
  | grep -aE 'RAIL_SHAPE|DRAWER_SHAPE|DRAWER_RECEIPT|RAIL_HEADING' > "$OUT"
echo "wrote $OUT"; cat "$OUT"
