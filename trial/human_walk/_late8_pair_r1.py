"""For each late-chapter bare-filename citation, print the sentence and the lines in that file matching its numbers.

The numbers a sentence quotes are the cheapest handle on the line it means; this lists every line of the cited file
that contains any of them, so the correction can take a real line instead of a guess.
"""
import io
import os
import re

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
DOC = os.path.join(ROOT, "trial", "results", "20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md")
CASES = [
    (1093, "trial/human_walk/worktree_slice_reading_1024.txt"),
    (1119, "trial/human_walk/infeasible_sentence_arms_r1.mjs"),
    (1154, "trial/human_walk/press_the_door_r1.mjs"),
    (1207, "trial/results/20261022_v3_human_chrome/stalled-research-screen-1.txt"),
    (1347, "trial/results/20261022_v3_human_chrome/first-tap-layers-3.txt"),
    (1473, "trial/results/20261022_v3_human_chrome/goal-numbers-1.txt"),
    (1758, "trial/human_walk/dock_clearance_probe_r1.mjs"),
    (1926, "trial/results/20261022_v3_human_chrome/model_503_dock_press-1.txt"),
]

rows = io.open(DOC, encoding="utf-8").read().splitlines()
out = []
for doc_line, rel in CASES:
    sentence = rows[doc_line - 1]
    full = os.path.join(ROOT, rel)
    lines = io.open(full, encoding="utf-8", errors="replace").read().splitlines() if os.path.isfile(full) else []
    numbers = sorted(set(re.findall(r"\d+(?:\.\d+)?", sentence)), key=len, reverse=True)[:6]
    hits = []
    for n, r in enumerate(lines, 1):
        if any(num in r for num in numbers):
            hits.append("%d|%s" % (n, r.strip()[:130]))
    out.append("DOC:%d file=%s lines=%d numbers=%s" % (doc_line, rel, len(lines), ",".join(numbers)))
    out.append("  sentence: " + sentence[:300])
    out.extend("  " + h for h in hits[:8])
    out.append("")
io.open(r"D:/moodle/_cmdr_v3_port_1022/late_8_pairs.txt", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("cases=%d" % len(CASES))
