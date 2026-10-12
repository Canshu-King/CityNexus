# -*- coding: utf-8 -*-
"""0607 交付前的两件事：一、远端与合流形状现读；二、把 41 条判据逐枚转成交块用的表格行
（每行自带它在读数件里的那一行号，不手数、不记忆）。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
BARE = "D:/moodle/CityNexus"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/pinggong-0607-r1"
HEAD = "cb657e2cc0b6c84b98179fbab1f9d4b5ba386ec8"
RUN = TREE + "/review/pinggong-0607/stamp_final_run.txt"
LINES = []


def git(*a, cwd=REPO):
    proc = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout.strip()
    LINES.append("CMD %s -> rc=%d -> %s" % (" ".join(a), proc.returncode, out[:180]))
    return out, proc.returncode


tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1", cwd=BARE)[0].split("\t")[0]
for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    out = git("ls-remote", "origin", BRANCH, cwd=cwd)[0]
    if not out or out.split("\t")[0] != HEAD:
        print("ABORT %s 侧回读不是本轮头：%r" % (label, out))
        sys.exit(1)
    LINES.append("READBACK %s：%s" % (label, out))
for label, cwd in (("bare", BARE), ("integration", REPO)):
    kind = git("cat-file", "-t", HEAD, cwd=cwd)[0]
    if kind != "commit":
        print("ABORT %s 取不到枝尖" % label)
        sys.exit(1)
counts, _ = git("rev-list", "--left-right", "--count", "%s...%s" % (tip, HEAD))
merged, mrc = git("merge-tree", "--write-tree", tip, HEAD)
status = git("status", "--porcelain", cwd=TREE)[0]
LINES.append("现尖 %s｜枝尖 %s｜先人位 %s｜合流预测 rc=%d 写树 %s｜工作树未登记改动 %d 处"
             % (tip[:12], HEAD[:12], counts, mrc, merged[:12], 0 if not status else len(status.splitlines())))
with open("D:/moodle/_pinggong_scratch/0607/branch_shape.txt", "w", encoding="utf-8", newline="\n") as h:
    h.write("\n".join(LINES) + "\n")
print(LINES[-1])

row_re = re.compile(r"^(\S.*?)\s+自改\s+(\d+)｜在线上\s+(\d+)｜carried\s+(NO \d+/\d+|PART \d+/\d+|YES \d+/\d+|NONE 0/0)\s+｜absorbed_on (\S+)")
# 打印那行把枝名截到 58 字，所以名字从对账表按行序取，数字从读数件取，两边条数必须相等
manifest = git("show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % HEAD)[0].split("\n")
names = [ln.split("\t")[0] for ln in manifest[1:] if ln.strip()]
table, buckets, seen = [], {"YES": 0, "PART": 0, "NO": 0, "NONE": 0}, 0
for number, line in enumerate(open(RUN, encoding="utf-8").read().split("\n"), start=1):
    m = row_re.match(line)
    if not m:
        continue
    _name, own, on, carried, absorbed = m.groups()
    buckets[carried.split()[0]] += 1
    name = names[seen]
    seen += 1
    table.append("| `%s` | 自改 %s 个｜在线上 %s 个 | %s | 吸收代 %s | `review/pinggong-0607/stamp_final_run.txt:%d` |"
                 % (name, own, on, carried, absorbed if absorbed != "-" else "空（未全量在线上）", number))
if seen != len(names):
    print("ABORT 判据 %d 条与表里 %d 条枝对不上" % (seen, len(names)))
    sys.exit(1)
print("表格行 %d 条（= 表内枝数）｜分桶 %s" % (len(table), buckets))
with open("D:/moodle/_pinggong_scratch/0607/block_table.md", "w", encoding="utf-8", newline="\n") as h:
    h.write("| 来源枝 | 判据 | carried 新值 | absorbed_on | 读数行 |\n|---|---|---|---|---|\n")
    h.write("\n".join(table) + "\n")
print("表格已生成，供交块直接粘")
