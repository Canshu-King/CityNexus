#!/usr/bin/env bash
# Re-measure the drawer on the authoritative sha (pre-grouping), capture real stdout, restore the
# grouped tree no matter how the measurement exits.
set -u
REPO=/d/moodle/_qoder_drawer_1008
SHA=2f4abb238a004a19fbde2bd3f998536dbe967ae9
OUT=$REPO/review/drawer_grouping_r1/RECEIPT_BEFORE.txt
cd "$REPO" || exit 1
cp frontend/src/styles.css /tmp/_drawer_before_styles.keep
cp frontend/src/app/V8Experience.tsx /tmp/_drawer_before_v8.keep
restore() {
  # Absolute paths: an earlier version of this script restored with paths relative to the repo root
  # while cwd was already `frontend/`, so both cp calls failed and the tree was left at the
  # pre-change sha. The restore must not depend on cwd.
  cp /tmp/_drawer_before_styles.keep "$REPO/frontend/src/styles.css"
  cp /tmp/_drawer_before_v8.keep "$REPO/frontend/src/app/V8Experience.tsx"
  git -C "$REPO" reset -q
  echo "RESTORED rc_head=$(git -C "$REPO" rev-parse --short HEAD) dirty=$(git -C "$REPO" status --porcelain | wc -l)"
}
trap restore EXIT
git checkout "$SHA" -- frontend/src/styles.css frontend/src/app/V8Experience.tsx
cd frontend || exit 1
timeout 400 npx playwright test drawer-receipt-r1 --project=chromium --reporter=line --workers=1 2>&1 \
  | grep -a 'DRAWER_RECEIPT' > "$OUT"
echo "captured:"; cat "$OUT"
