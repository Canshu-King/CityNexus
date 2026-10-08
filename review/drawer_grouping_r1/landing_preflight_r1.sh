#!/usr/bin/env bash
# Read-only landing pre-flight: does this lane's review branch still merge onto the CURRENT
# authoritative tip, and did anyone land edits in the same region of the two files I touched?
# Nothing is merged, checked out, or written to any tree but this lane's review/ notes.
set -u
REPO=/d/moodle/_qoder_drawer_1008
AUTH=refs/heads/mirror/integration-frontend-apple-pass1
URL=ssh://git@ssh.github.com:443/Canshu-King/CityNexus.git
BASE=2f4abb238a004a19fbde2bd3f998536dbe967ae9
git -C "$REPO" fetch --depth=50 "$URL" "$AUTH:refs/remotes/auth/now" >/dev/null 2>&1
TIP=$(git -C "$REPO" rev-parse refs/remotes/auth/now)
git -C "$REPO" merge-base --is-ancestor "$BASE" refs/remotes/auth/now && ANC=yes || ANC=no
TREE=$(git -C "$REPO" merge-tree --write-tree refs/remotes/auth/now HEAD 2>/dev/null | head -1)
CONFLICTS=$(git -C "$REPO" merge-tree --write-tree refs/remotes/auth/now HEAD 2>/dev/null | grep -acE 'CONFLICT|<<<<<<<' || true)
CHANGED=$(git -C "$REPO" diff --name-only "$BASE" refs/remotes/auth/now | wc -l)
OVERLAP=$(git -C "$REPO" diff --name-only "$BASE" HEAD > /tmp/mine.txt; git -C "$REPO" diff --name-only "$BASE" refs/remotes/auth/now > /tmp/theirs.txt; grep -Fxf /tmp/mine.txt /tmp/theirs.txt | wc -l)
SYMHITS=$(git -C "$REPO" diff "$BASE" refs/remotes/auth/now -- frontend/src/app/V8Experience.tsx frontend/src/styles.css | grep -aicE '^[+-].*(drawerRoutes|v8-nav-drawer|navGroupKey|v8-nav-group|v8-drawer)')
echo "LANDING_PREFLIGHT tip=$TIP base_is_ancestor=$ANC merge_tree_tree=$TREE conflict_markers=$CONFLICTS auth_files_changed=$CHANGED overlap_files=$OVERLAP drawer_symbol_hits=$SYMHITS"
