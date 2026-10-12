# -*- coding: utf-8 -*-
"""独立复验 ORD-0588 的搬运：不看搬运器自己的话，另起一把尺——
  · 从清单读每一行的「来源枝 + 源路径 + blob + 行数 + 字节数」；
  · 现读源枝那枚 blob 的字节，与树上归档后那枚文件的字节逐字节比；
  · 再数并集：八枚枝里 evidence/gpt-assist/ 下的路径全集，必须与清单条数相等（一枚不落）。
任一不符就非零退出。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
MANIFEST_FILE = TREE + "/docs/revolution-archive/gpt-assist/MANIFEST.tsv"
PREFIX = "evidence/gpt-assist/"


def git_bytes(args, cwd):
    proc = subprocess.run(["git", "-C", cwd] + args, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("ABORT git %s :: %s" % (" ".join(args), proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout


rows = [line.split("\t") for line in open(MANIFEST_FILE, encoding="utf-8").read().splitlines()[1:] if line.strip()]
bad = []
for branch, sha, row_no, src, dest, blob, lines, nbytes in rows:
    source_bytes = git_bytes(["show", "%s:%s" % (sha, src)], REPO)
    with open(TREE + "/" + dest, "rb") as handle:
        tree_bytes = handle.read()
    if source_bytes != tree_bytes:
        bad.append("BYTES_DIFFER %s" % dest)
    hashed = git_bytes(["hash-object", TREE + "/" + dest], TREE).decode().strip()
    if hashed != blob:
        bad.append("BLOB_MISMATCH %s manifest=%s now=%s" % (dest, blob[:10], hashed[:10]))
    if len(tree_bytes) != int(nbytes):
        bad.append("LENGTH %s" % dest)
    counted = source_bytes.count(b"\n") + (0 if source_bytes.endswith(b"\n") or not source_bytes else 1)
    if counted != int(lines):
        bad.append("LINES %s counted=%d manifest=%s" % (dest, counted, lines))

union = set()
for branch, sha, row_no in {(r[0], r[1], r[2]) for r in rows}:
    pass
seen_branches = {}
for row in rows:
    seen_branches.setdefault((row[0], row[1]), True)
for branch, sha in seen_branches:
    listing = git_bytes(["ls-tree", "-r", "--name-only", sha, "--", PREFIX], REPO).decode("utf-8", "replace")
    for path in [p.strip() for p in listing.splitlines() if p.strip()]:
        union.add((branch, path))

manifest_pairs = {(r[0], r[3]) for r in rows}
missing = sorted(union - manifest_pairs)
extra = sorted(manifest_pairs - union)
print("MANIFEST_ROWS %d 源枝并集 %d 缺 %d 多 %d 逐字节不符 %d"
      % (len(rows), len(union), len(missing), len(extra), len(bad)))
for text in (bad + ["MISSING %s %s" % m for m in missing] + ["EXTRA %s %s" % e for e in extra])[:8]:
    print("  " + text)
if bad or missing or extra:
    raise SystemExit(1)
print("VERDICT ord0588_copy_verified rows=%d union=%d" % (len(rows), len(union)))
