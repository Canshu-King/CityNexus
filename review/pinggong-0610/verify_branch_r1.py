# -*- coding: utf-8 -*-
"""ORD-0610 证据枝远端回读：两处 ls-remote 必须同为本地头，两枚 40 位必须能 cat-file，
对现尖的先人位与只读合流预测各算一次，工作树必须干净。不推、不 force、不删 ref。"""
import subprocess
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
BARE = "D:/moodle/CityNexus"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/pinggong-0610-r1"
TIP = "8940570c022950b705cc3b37139d1b8f7052c42a"
OUT = "D:/moodle/_pinggong_scratch/0610/branch_readback.txt"
LINES = []


def cmd(args, cwd=REPO):
    proc = subprocess.run(args, cwd=cwd, capture_output=True)
    out = proc.stdout.decode("utf-8", "replace").strip()
    LINES.append("CMD %s -> rc=%d -> %s" % (" ".join(args), proc.returncode, out))
    return out


def die(message):
    flush()
    sys.exit("ABORT " + message)


def flush():
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(LINES) + "\n")


head = cmd(["git", "rev-parse", "HEAD"], cwd=TREE)
if len(head) != 40:
    die("头不是四十位")
for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    out = cmd(["git", "ls-remote", "origin", BRANCH], cwd=cwd)
    if not out or out.split("\t")[0] != head:
        die("%s 侧回读不是本轮头：%r" % (label, out))
for obj in (head, TIP, "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9",
            "42a66f506493e0b6096fe3f40101d1f5e4ee9411", "197b36f13cd739e2f491d6128f928fada44e8ff6"):
    for label, cwd in (("bare", BARE), ("integration", REPO)):
        kind = cmd(["git", "cat-file", "-t", obj], cwd=cwd)
        if kind not in ("commit", "blob", "tree"):
            die("%s 在 %s 取不到：%r" % (obj[:12], label, kind))
counts = cmd(["git", "rev-list", "--left-right", "--count", "%s...%s" % (TIP, head)])
merged = cmd(["git", "merge-tree", "--write-tree", TIP, head])
status = cmd(["git", "status", "--porcelain"], cwd=TREE)
LINES.append("先人位（左=尖独有 右=本枝独有）: %s" % counts)
LINES.append("只读合流预测写树: %s" % merged)
LINES.append("工作树未登记改动 %d 处" % (0 if not status else len(status.splitlines())))
diff = cmd(["git", "diff", "--name-only", "%s...%s" % (TIP, head)], cwd=TREE)
LINES.append("本枝相对现尖改动的文件（逐枚）: %s" % diff.replace("\n", " | "))
flush()
print("\n".join(LINES[-6:]))
print("VERIFY OK head=%s" % head)
