#!/usr/bin/env bash
# Apply the landing ruler's own criterion, computed inside THIS lane's tree.
# The commander's `_disjoint_scan_r1.py` chdir's into D:/moodle/CityNexus and reads
# refs/remotes/origin/review/* there -- a repo this lane is ordered not to touch, so it cannot be
# run from here and r2 will only show up on that loop's own next fetch. The criterion itself is
# reproducible without touching it: base = merge-base(tip, ref); ready means the tip-side file set
# since that base and the branch-side file set do not intersect.
set -u
REPO=/d/moodle/_qoder_drawer_1008
TIPREF=refs/remotes/auth/now
for REF in review/drawer-grouping-r1 review/drawer-grouping-r2; do
  TIP=$(git -C "$REPO" rev-parse "$TIPREF")
  BASE=$(git -C "$REPO" merge-base "$TIPREF" "$REF")
  TIPSIDE=$(git -C "$REPO" diff --name-only "$BASE" "$TIP" | sort -u)
  BRANCHSIDE=$(git -C "$REPO" diff --name-only "$BASE" "$REF" | sort -u)
  INTER=$(comm -12 <(printf '%s\n' "$TIPSIDE") <(printf '%s\n' "$BRANCHSIDE") | grep -a . | wc -l)
  COLLIDE=$(comm -12 <(printf '%s\n' "$TIPSIDE") <(printf '%s\n' "$BRANCHSIDE") | grep -a . | sed 's#.*/##' | paste -sd, -)
  echo "CRITERION ref=$REF base=$(printf %s "$BASE" | cut -c1-12) base_is_tip=$([ "$BASE" = "$TIP" ] && echo yes || echo no) tipside=$(printf '%s\n' "$TIPSIDE" | grep -ac .) branchside=$(printf '%s\n' "$BRANCHSIDE" | grep -ac .) intersect_files=$INTER collide=[$COLLIDE] verdict=$([ "$INTER" = "0" ] && echo READY-clean || echo MUST-rebase)"
done
