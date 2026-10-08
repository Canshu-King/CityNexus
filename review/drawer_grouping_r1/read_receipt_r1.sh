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
echo "BRANCH_TIP"
git -C /d/moodle/_qoder_drawer_1008 ls-remote origin refs/heads/review/drawer-grouping-r1
