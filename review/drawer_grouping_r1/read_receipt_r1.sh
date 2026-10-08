#!/usr/bin/env bash
# Print the drawer-grouping readings straight from the tracked receipt artifacts, so a BB-machine
# --evidence command can be a single path that exits 0 (the gate refuses any evidence whose command
# returns non-zero, and inline `bash -c cat\ path` quoting breaks under cmd.exe).
set -u
D=/d/moodle/_qoder_drawer_1008/review/drawer_grouping_r1
echo "RECEIPT_AFTER_BEGIN"
cat "$D/RECEIPT_AFTER.txt"
echo "RECEIPT_AFTER_END"
echo "RECEIPT_BEFORE_BEGIN"
cat "$D/RECEIPT_BEFORE.txt"
echo "RECEIPT_BEFORE_END"
echo "LEDGER_INSERT_RECEIPT"
ls /d/moodle/_qoder_ledger_inbox/_processed | grep drawer_1234
echo "BRANCH_TIP_LOCAL"
git -C /d/moodle/_qoder_drawer_1008 ls-remote origin refs/heads/review/drawer-grouping-r1
echo "BRANCH_TIP_GITHUB"
# The patrol reads GitHub, not this lane's local `origin` (which is a directory path), so the tip
# that counts as delivered is the one read back from the explicit GitHub URL over ssh:443.
git -C /d/moodle/_qoder_drawer_1008 ls-remote ssh://git@ssh.github.com:443/Canshu-King/CityNexus.git refs/heads/review/drawer-grouping-r1
echo "LOCAL_HEAD"
git -C /d/moodle/_qoder_drawer_1008 rev-parse HEAD
