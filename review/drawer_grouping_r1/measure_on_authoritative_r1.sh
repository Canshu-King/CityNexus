#!/usr/bin/env bash
# Measure one probe on the authoritative sha, then restore the grouped tree. Absolute paths only:
# a relative-path restore in an earlier script silently failed and left the tree on the old sha.
set -u
REPO=/d/moodle/_qoder_drawer_1008
SHA=2f4abb238a004a19fbde2bd3f998536dbe967ae9
SPEC=${1:-rail-leak-probe-r1}
cp "$REPO/frontend/src/styles.css" /tmp/_leak_styles.keep
cp "$REPO/frontend/src/app/V8Experience.tsx" /tmp/_leak_v8.keep
restore() {
  cp /tmp/_leak_styles.keep "$REPO/frontend/src/styles.css"
  cp /tmp/_leak_v8.keep "$REPO/frontend/src/app/V8Experience.tsx"
  git -C "$REPO" reset -q
  echo "RESTORED dirty=$(git -C "$REPO" status --porcelain -- frontend/src | wc -l)"
}
trap restore EXIT
git -C "$REPO" checkout "$SHA" -- frontend/src/styles.css frontend/src/app/V8Experience.tsx
cd "$REPO/frontend" || exit 1
timeout 400 npx playwright test "$SPEC" --project=chromium --reporter=line --workers=1 2>&1 | grep -aE 'LEAK|_RECEIPT|passed|failed' | head -4
