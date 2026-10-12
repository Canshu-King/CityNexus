# -*- coding: utf-8 -*-
"""ORD-0602 远端回读尺：本轮头、两处 ls-remote、两处 cat-file、对现尖的先人位与只读合流预测、
工作树干净度，逐条落一张读数文件。不推、不 force、不删 ref。"""
import subprocess
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
BARE = "D:/moodle/CityNexus"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/屏工-0602-r1"
TIP = "b68f381712abd9207b5ecd7625d18d0883838459"
OUT = "D:/moodle/_pinggong_scratch/0602_push_state2.txt"
LINES = []


def cmd(args, cwd=REPO):
    proc = subprocess.run(args, cwd=cwd, capture_output=True)
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    LINES.append("CMD %s\nrc=%d\n%s%s" % (" ".join(args), proc.returncode, out,
                                          ("\n[stderr] " + err) if err else ""))
    return out


def die(message):
    flush()
    sys.exit("ABORT " + message)


def flush():
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(LINES) + "\n")


head = cmd(["git", "rev-parse", "HEAD"], cwd=TREE)
if len(head) != 40:
    die("本轮头不是四十位：%r" % head)

for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    out = cmd(["git", "ls-remote", "origin", BRANCH], cwd=cwd)
    if not out or out.split("\t")[0] != head:
        die("%s 侧回读不含本轮头：%r" % (label, out))
    LINES.append("READBACK %s: %s" % (label, out))

for label, cwd in (("bare", BARE), ("integration", REPO)):
    out = cmd(["git", "cat-file", "-t", head], cwd=cwd)
    if out != "commit":
        die("%s 仓库取不到本轮头：%r" % (label, out))
    LINES.append("CATFILE %s: %s = %s" % (label, head, out))

for path, label in (("backend/app/execution/location_scope.py", "落进来的模块"),
                    ("backend/app/stay_mobility.py", "接线宿主"),
                    ("backend/tests/test_qoder_ord0602_private_buddy_location_scope.py", "行为测试")):
    out = cmd(["git", "rev-parse", "%s:%s" % (head, path)])
    LINES.append("BLOB %s: %s:%s = %s" % (label, head[:12], path, out))

counts = cmd(["git", "rev-list", "--left-right", "--count", "%s...%s" % (TIP, head)])
LINES.append("先人位（现尖...本轮头，左=尖独有 右=本枝独有）: %s" % counts)

tree = cmd(["git", "merge-tree", "--write-tree", TIP, head])
LINES.append("MERGE-TREE 对现尖 %s 只读预测写树: %s" % (TIP, tree))

status = cmd(["git", "status", "--porcelain"], cwd=TREE)
LINES.append("工作树未登记改动行数: %d" % (0 if not status else len(status.splitlines())))
flush()
print("\n".join(LINES))
print("VERIFY OK head=%s" % head)
