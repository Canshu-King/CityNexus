# -*- coding: utf-8 -*-
"""ORD-0588 前置清点：族B 那八枚枝里 evidence/gpt-assist/ 的并集。
逐枚给「来源枝 + 仓内路径 + blob + 行数」，并单独列出同一路径在多枝内容不同的撞面
（那种不能"并成一枚"，只能按来源枝各留一份，否则评审记录会被后写的赢盖掉）。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
MANIFEST_TIP = "1cf2beccb45fcbb9da8a573acaf8f3fe0a37fcd0"
PREFIX = "evidence/gpt-assist/"


def git(*args):
    out = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if out.returncode != 0:
        raise SystemExit("ABORT git %s :: %s" % (" ".join(map(str, args)),
                                                 out.stderr.decode("utf-8", "replace")[:300]))
    return out.stdout.decode("utf-8", "replace")


rows = git("show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % MANIFEST_TIP).split("\n")
branches = []
for index, row in enumerate(rows, start=1):
    if not row.startswith("gpt/"):
        continue
    cols = row.split("\t")
    branches.append({"name": cols[0], "sha": cols[1], "manifest_line": index})
print("MANIFEST_ROWS %d" % len(branches))

items = {}
per_branch = {}
for branch in branches:
    listing = git("ls-tree", "-r", "--name-only", branch["sha"], "--", PREFIX)
    paths = [p.strip() for p in listing.splitlines() if p.strip()]
    per_branch[branch["name"]] = len(paths)
    for path in paths:
        blob = git("rev-parse", "%s:%s" % (branch["sha"], path)).strip()
        text = git("show", "%s:%s" % (branch["sha"], path))
        lines = len(text.split("\n"))
        if text.endswith("\n"):
            lines -= 1
        items.setdefault(path, []).append({"branch": branch["name"], "sha": branch["sha"],
                                           "blob": blob, "lines": lines,
                                           "manifest_line": branch["manifest_line"]})

paths_total = len(items)
clash = sorted(p for p, v in items.items() if len(set(h["blob"] for h in v)) > 1)
same_everywhere = sorted(p for p, v in items.items() if len(set(h["blob"] for h in v)) == 1 and len(v) > 1)
single = sorted(p for p, v in items.items() if len(v) == 1)
lines_sum = {}
for path, holders in items.items():
    lines_sum[path] = max(h["lines"] for h in holders)

out = open("D:/moodle/_pinggong_scratch/gpt_assist_census_r1.txt", "w", encoding="utf-8")
out.write("PREFIX %s\n" % PREFIX)
out.write("BRANCHES %d 每枝枚数 %s\n" % (len(branches),
          " ".join("%s=%d" % (k.split("revolution-")[-1], v) for k, v in per_branch.items())))
out.write("UNION_PATHS %d 单枝独有 %d 多枝同文 %d 多枝异文 %d\n"
          % (paths_total, len(single), len(same_everywhere), len(clash)))
for path in clash:
    out.write("CLASH %s 份数 %d\n" % (path, len(items[path])))
    for holder in items[path]:
        out.write("   CLASH_HOLD %s blob %s lines %d manifest %d\n"
                  % (holder["branch"], holder["blob"][:12], holder["lines"], holder["manifest_line"]))
out.close()

with open("D:/moodle/_pinggong_scratch/gpt_assist_items_r1.tsv", "w", encoding="utf-8") as handle:
    handle.write("path\tbranches\tmax_lines\tdistinct_blobs\n")
    for path in sorted(items):
        handle.write("%s\t%s\t%d\t%d\n" % (path, ",".join(sorted({h["branch"].split("revolution-")[-1] for h in items[path]})),
                                            lines_sum[path], len(set(h["blob"] for h in items[path]))))

print(open("D:/moodle/_pinggong_scratch/gpt_assist_census_r1.txt", encoding="utf-8").read())
