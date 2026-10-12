# -*- coding: utf-8 -*-
"""对账表现读体检：列名、carried 与 absorbed_on 的既有用词、四十一枚 pin 在本地对象库取不取得到、
以及每枚枝相对现尖「独有文件集」的规模——这些是新增那枚 stamp 尺的口径输入。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BARE = "D:/moodle/CityNexus"
REPO = "D:/moodle/_qoder_integration_20260919"
LIVE = subprocess.run(["git", "-C", BARE, "ls-remote", "origin",
                       "refs/heads/mirror/integration-frontend-apple-pass1"],
                      capture_output=True, text=True).stdout.split("\t")[0]


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


raw = git(REPO, "show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % LIVE).stdout
lines = raw.split("\n")
cols = lines[0].split("\t")
rows = [dict(zip(cols, ln.split("\t"))) for ln in lines[1:] if ln.strip()]
print("现尖 %s" % LIVE)
print("列名 %d 枚：%s" % (len(cols), " ".join(cols)))
print("数据行 %d 条" % len(rows))
print("carried 既有取值分布：%s" % sorted({r.get("carried", "") for r in rows}))
print("absorbed_on 非空 %d 条，verdict 取值 %s"
      % (len([r for r in rows if r.get("absorbed_on")]), sorted({r.get("verdict", "") for r in rows})))

missing = [r["name"] for r in rows if git(BARE, "cat-file", "-e", r["sha"]).returncode != 0]
print("pin 在本地对象库取不到的枝：%d 条" % len(missing))
for name in missing:
    print("   MISS %s" % name)

tip_tree = {}
for line in git(REPO, "ls-tree", "-r", "--format=%(objectname) %(path)", LIVE).stdout.splitlines():
    blob, _, path = line.partition(" ")
    tip_tree[path] = blob
print("现尖树内文件 %d 枚" % len(tip_tree))

for row in rows[:6]:
    if git(BARE, "cat-file", "-e", row["sha"]).returncode:
        continue
    branch_tree = {}
    for line in git(REPO, "ls-tree", "-r", "--format=%(objectname) %(path)", row["sha"]).stdout.splitlines():
        blob, _, path = line.partition(" ")
        branch_tree[path] = blob
    unique = [p for p, b in branch_tree.items() if tip_tree.get(p) != b]
    same_blob = [p for p in unique if p in tip_tree]
    print("%-58s 枝内 %5d｜相对现尖独有 %5d｜其中同样字节已在尖上 %4d"
          % (row["name"][:58], len(branch_tree), len(unique), len(same_blob)))
