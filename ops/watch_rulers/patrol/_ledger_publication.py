"""Is the 19:24 bypass local-only or published? Read-only git history of the ledger file.

Also prints what the local repo thinks the ledger's path/last commits are, and reads back whether the two
Q43-RED rel headings are in the committed blob (git show <rev>:<path> piped through the same ruler is NOT run -
just a heading occurrence count, so nothing is rewritten).
"""
import io
import os
import subprocess

REPO = r"D:\moodle\CityNexus"
HEADINGS = ["### ORD-B · 车道 rel · 契约补「来源 + 坐标系」两格 · 2026-09-28 0338+08",
            "### ORD-B r3 · 车道 rel · 回答\"两条路各靠哪个 schema\"+ 勘误我自己 0408 块一处归因"]


def g(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (("[stderr] " + r.stderr) if r.returncode else "")


for a in (["ls-files", "--", "*CITYNEXUS_AGENT_CONTROL*"],
          ["rev-parse", "--abbrev-ref", "HEAD"],
          ["log", "-3", "--format=%h|%an|%ad|%s", "--date=format:%H:%M:%S"],
          ["status", "--porcelain", "--", "CITYNEXUS_AGENT_CONTROL.md"]):
    rc, out = g(*a)
    print("$ git %s  rc=%d\n%s" % (" ".join(a), rc, out.rstrip()[:900]))

rc, paths = g("ls-files", "--", "*CITYNEXUS_AGENT_CONTROL*")
tracked = [p.strip() for p in paths.splitlines() if p.strip()]
print("\ntracked ledger paths in local repo: %r" % (tracked,))
for p in tracked[:1]:
    for rev in ["HEAD", "@{u}" if False else None]:
        if not rev:
            continue
        rc, out = g("show", "%s:%s" % (rev, p))
        if rc:
            print("  git show %s:%s failed rc=%d" % (rev, p, rc))
            continue
        for h in HEADINGS:
            print("  %s:%s  heading occurrences=%d  bytes=%d" % (rev, p, out.count(h), len(out.encode("utf-8"))))
