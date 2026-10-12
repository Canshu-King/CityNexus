# -*- coding: utf-8 -*-
"""ORD-0588 搬运器：族B 那八枚枝的 evidence/gpt-assist/ 并集，逐字节搬进
docs/revolution-archive/gpt-assist/，并写一份带来源的清单。

安全形制：
  · 来源枝名单取自尖上的 docs/REVOLUTION_ABSORPTION_MANIFEST.tsv 指定那几行，不手打；
  · 写文件走字节通道（git show 的原始 stdout），不过文本编码，避免行尾被翻；
  · 同一路径若在多枝内容不同，就按来源枝各留一份，绝不"并成一枚"（后写的赢会盖掉评审记录）；
  · 落盘后逐枚用 git hash-object 与源 blob 对拍，字节数也对拍，任一不符就 ABORT。"""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
TIP = open("D:/moodle/_pinggong_scratch/tip_0588.txt").read().strip()
MANIFEST = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"
PREFIX = "evidence/gpt-assist/"
DEST_ROOT = TREE + "/docs/revolution-archive/gpt-assist"
ROWS = range(32, 40)  # 号令者那张表点的就是这八行


def git_bytes(*args, cwd=REPO):
    proc = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("ABORT git %s :: %s" % (" ".join(map(str, args)),
                                                 proc.stderr.decode("utf-8", "replace")[:300]))
    return proc.stdout


def die(msg):
    raise SystemExit("ABORT " + msg)


rows_text = git_bytes("show", "%s:%s" % (TIP, MANIFEST)).decode("utf-8", "replace").split("\n")
branches = []
for number in ROWS:
    line = rows_text[number - 1]
    if not line.startswith("gpt/"):
        die("manifest row %d is not a gpt branch: %r" % (number, line[:60]))
    cols = line.split("\t")
    branches.append({"name": cols[0], "sha": cols[1], "row": number})

union = {}
for branch in branches:
    listing = git_bytes("ls-tree", "-r", "--name-only", branch["sha"], "--", PREFIX).decode("utf-8", "replace")
    for path in [p.strip() for p in listing.splitlines() if p.strip()]:
        blob = git_bytes("rev-parse", "%s:%s" % (branch["sha"], path)).decode().strip()
        body = git_bytes("show", "%s:%s" % (branch["sha"], path))
        lines = body.count(b"\n") + (0 if body.endswith(b"\n") or not body else 1)
        union.setdefault(path, []).append({"branch": branch["name"], "sha": branch["sha"],
                                           "row": branch["row"], "blob": blob,
                                           "lines": lines, "bytes": len(body)})

clash = sorted(p for p, v in union.items() if len({h["blob"] for h in v}) > 1)
os.makedirs(DEST_ROOT, exist_ok=True)
written = []
for path in sorted(union):
    holders = union[path]
    rel = path[len(PREFIX):]
    if len(holders) == 1:
        dest = DEST_ROOT + "/" + rel
        holder = holders[0]
        source_blob, bodies = holder["blob"], [holder]
    else:
        dest = DEST_ROOT + "/by-branch/" + rel
        bodies = []
        for holder in holders:
            name, _dot, rest = holder["branch"].rpartition(".")
            per = DEST_ROOT + "/by-branch/" + holder["branch"].split("gpt/revolution-")[-1] + "/" + rel
            os.makedirs(os.path.dirname(per), exist_ok=True)
            raw = git_bytes("show", "%s:%s" % (holder["sha"], path))
            with open(per, "wb") as handle:
                handle.write(raw)
            bodies.append({"file": per, "holder": holder})
        source_blob = "MULTI"
        print("KEPT_PER_BRANCH %s 份数 %d" % (path, len(holders)))
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    raw = git_bytes("show", "%s:%s" % (holder["sha"], path))
    with open(dest, "wb") as handle:
        handle.write(raw)
    written.append({"dest": dest, "source_path": path, "holder": holder})

for item in written:
    got = subprocess.run(["git", "hash-object", item["dest"]], capture_output=True, cwd=TREE)
    if got.stdout.decode().strip() != item["holder"]["blob"]:
        die("blob mismatch for %s: wrote %s source %s"
            % (item["dest"], got.stdout.decode().strip()[:12], item["holder"]["blob"][:12]))
    if os.path.getsize(item["dest"]) != item["holder"]["bytes"]:
        die("byte length mismatch for %s" % item["dest"])

lines_man = ["来源枝\t枝尖\t对账表行\t源仓内路径\t归档后路径\tblob\t行数\t字节数"]
for item in written:
    holder = item["holder"]
    lines_man.append("%s\t%s\t%d\t%s\t%s\t%s\t%d\t%d" % (
        holder["branch"], holder["sha"], holder["row"], item["source_path"],
        item["dest"].replace(TREE + "/", ""), holder["blob"], holder["lines"], holder["bytes"]))
open(DEST_ROOT + "/MANIFEST.tsv", "w", encoding="utf-8", newline="\n").write("\n".join(lines_man) + "\n")

total_paths = len(union)
print("BRANCHES %d UNION_PATHS %d 单枝独有 %d 多枝异文 %d"
      % (len(branches), total_paths, total_paths - len(clash), len(clash)))
print("WRITTEN %d 清单行数 %d" % (len(written), len(lines_man)))
print("LINES_TOTAL %d BYTES_TOTAL %d"
      % (sum(i["holder"]["lines"] for i in written), sum(i["holder"]["bytes"] for i in written)))
with open("D:/moodle/_pinggong_scratch/ord0588_census.txt", "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(lines_man) + "\n")
