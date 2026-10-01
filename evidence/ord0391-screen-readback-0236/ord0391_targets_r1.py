# -*- coding: utf-8 -*-
"""ORD-0391 step 3 groundwork - which of the 23 reworded lines still exist, verbatim, on the current tip.

The owed work is an on-screen verbatim read-back. Before driving a browser I need to know what the target
set actually is today: the strings were written at 4fcfe6e5 on base 8fddeb76, and the authoritative line has
moved a long way since. A line that no longer exists is not a screen reading I can take, and a line that was
reworded a second time has to be read in its new shape - so this script diffs the delivered pair, then looks
for each added line's exact text at the tip named on the command line.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work"
BASE = "8fddeb76a79968592a7a3e98d2f296dda450d4df"
HEAD = "4fcfe6e595bba9de30ff35a1b49ff6dc93fe8d95"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=600)
    if r.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (a[:2], (r.stderr or "")[-200:]))
    return r.stdout or ""


def main():
    tip = (sys.argv[1] if len(sys.argv) > 1 else
           git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0])
    files = [l.split("\t")[-1].strip() for l in
             git("diff", "--name-only", BASE, HEAD).splitlines() if l.strip()]
    rows = []
    for f in files:
        added = [l[1:] for l in git("diff", "-U0", BASE, HEAD, "--", f).splitlines()
                 if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in git("diff", "-U0", BASE, HEAD, "--", f).splitlines()
                   if l.startswith("-") and not l.startswith("---")]
        tip_text = git("show", tip + ":" + f)
        tip_lines = tip_text.split("\n")
        for a in added:
            stripped = a.strip()
            where = [i + 1 for i, l in enumerate(tip_lines) if l.strip() == stripped]
            # the literal copy a screen would show: quoted string bodies on that line
            lit = re.findall(r"[\"'`]([^\"'`]{6,})[\"'`]", stripped)
            rows.append({"file": f, "added_at_head": stripped, "line_at_tip": where or None,
                         "literal_candidates": lit,
                         "gone_from_tip": not where,
                         "same_line_existed_at_base": any(r.strip() == stripped for r in removed)})
    doc = {"tip": tip, "base": BASE, "head": HEAD, "files": files,
           "added_lines": len([r for r in rows]),
           "still_on_tip": len([r for r in rows if not r["gone_from_tip"]]),
           "gone_from_tip": len([r for r in rows if r["gone_from_tip"]]),
           "rows": rows}
    out = os.path.join(WORK, "ord0391_targets_r1.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "files": len(files), "added_lines": doc["added_lines"],
                      "still_on_tip": doc["still_on_tip"], "gone": doc["gone_from_tip"],
                      "out": out}, ensure_ascii=False))


raise SystemExit(main())
