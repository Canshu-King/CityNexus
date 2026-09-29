"""ORD-0460: recompute the failure-vocabulary reading and write it where the recuter can fetch it.

The tree has one gate for this (`test_qoder_ord0272_continuation.py::test_G6_...`), and it scans
`error("CODE"` shapes.  My new refusal rides `reason_code`, so the set must stay exactly the base's.
"""
import io
import re
import subprocess

WT = "D:/moodle/_qoder_rel_ord0460_wt/"
BASE = "4ee14229f80691cf8e5ea913375c0caf83ac02ee"
MINE = "b00fff161c59bbd96945c38b6f7cfaf6743ee834"
PATTERN = re.compile(r'error\(\s*"([A-Z][A-Z0-9_]{3,})"')


def codes(rev):
    out = subprocess.run(["git", "-C", WT.rstrip("/"), "show", rev], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted(set(PATTERN.findall(out)))


base = codes(BASE + ":backend/app/main.py")
mine = codes(MINE + ":backend/app/main.py")
rows = [
    "regex=%s" % PATTERN.pattern,
    "base_blob=%s" % subprocess.run(["git", "-C", WT.rstrip("/"), "rev-parse", BASE + ":backend/app/main.py"],
                                    capture_output=True, text=True).stdout.strip(),
    "mine_blob=%s" % subprocess.run(["git", "-C", WT.rstrip("/"), "rev-parse", MINE + ":backend/app/main.py"],
                                    capture_output=True, text=True).stdout.strip(),
    "base_count=%d mine_count=%d new_in_mine=%d sets_equal=%s"
    % (len(base), len(mine), len(set(mine) - set(base)), base == mine),
    "mine_set=" + ",".join(mine),
    "new_reason_code_emitters_in_main_py=%d" % mine.count("SHARE_GRANT_EXPIRY_IN_PAST"),
]
# `SHARE_GRANT_EXPIRY_IN_PAST` is a reason_code, not a `error("CODE")` word: prove it is absent from the
# set above and present exactly once as a string in the file.
text = subprocess.run(["git", "-C", WT.rstrip("/"), "show", MINE + ":backend/app/main.py"],
                      capture_output=True, text=True, encoding="utf-8").stdout
rows.append("SHARE_GRANT_EXPIRY_IN_PAST_literal_occurrences=%d" % text.count("SHARE_GRANT_EXPIRY_IN_PAST"))
io.open(WT + "review/ord0460/vocabulary_r1.txt", "w", encoding="utf-8", newline="\n").write(
    "\n".join(rows) + "\n")
print("\n".join(rows))
