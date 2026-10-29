"""Correct the just-inserted citation: the classifier sits at line 48, not 44."""

import io
import sys

DOC = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"
OLD = "_cmdr_full_red_reason_census_r164.py:44"
NEW = "_cmdr_full_red_reason_census_r164.py:48"

text = io.open(DOC, encoding="utf-8", newline="").read()
if text.count(OLD) != 1:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("ABORT stale citation hits=%d" % text.count(OLD))
    sys.exit(5)
io.open(DOC, "w", encoding="utf-8", newline="").write(text.replace(OLD, NEW, 1))
read_back = io.open(DOC, encoding="utf-8", newline="").read()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("FIXED stale_hits=%d fixed_hits=%d" % (read_back.count(OLD), read_back.count(NEW)))
