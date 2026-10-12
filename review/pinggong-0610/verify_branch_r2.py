# -*- coding: utf-8 -*-
"""远端回读尺 r2：权威尖不写死，从 GitHub 现取；枝尖取本地头。
逐枚判：两处 ls-remote 同为该头、这一拍点到的每枚 40 位都能 cat-file、对现尖的先人位、只读合流预测、工作树干净、改动面逐枚。
不推、不 force、不删 ref。"""
import subprocess
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
BARE = r"D:/moodle/CityNexus"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/pinggong-0610-r1"
OUT = "D:/moodle/_pinggong_scratch/0610/r2_branch_readback.txt"
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
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(LINES) + "\n")


tip = cmd(["git", "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
          cwd=BARE).split("\t")[0]
if len(tip) != 40:
    die("现尖取不到")
head = cmd(["git", "rev-parse", "HEAD"], cwd=TREE)
if len(head) != 40:
    die("枝尖取不到")
LINES.append("现尖 %s｜枝尖 %s" % (tip, head))
for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    out = cmd(["git", "ls-remote", "origin", BRANCH], cwd=cwd)
    if not out or out.split("\t")[0] != head:
        die("%s 侧回读不是本轮头：%r" % (label, out))
    LINES.append("READBACK %s：%s" % (label, out))
for obj in (tip, head, "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9",
            "42a66f506493e0b6096fe3f40101d1f5e4ee9411",
            "197b36f13cd739e2f491d6128f928fada44e8ff6"):
    for label, cwd in (("bare", BARE), ("integration", REPO)):
        kind = cmd(["git", "cat-file", "-t", obj], cwd=cwd)
        if kind not in ("commit", "blob", "tree"):
            die("%s 在 %s 取不到" % (obj[:12], label))
counts = cmd(["git", "rev-list", "--left-right", "--count", "%s...%s" % (tip, head)])
merged = cmd(["git", "merge-tree", "--write-tree", tip, head])
status = cmd(["git", "status", "--porcelain"], cwd=TREE)
diff = cmd(["git", "diff", "--name-only", "%s...%s" % (tip, head)], cwd=TREE)
LINES.append("先人位（左=现尖独有 右=本枝独有）：%s" % counts)
LINES.append("只读合流预测写树：%s" % merged)
LINES.append("工作树未登记改动 %d 处" % (0 if not status else len(status.splitlines())))
LINES.append("本枝相对现尖改动面（逐枚）：%s" % (diff.replace("\n", " | ") or "（无）"))
flush()
print("\n".join(LINES[-6:]))
print("VERIFY OK head=%s tip=%s" % (head, tip))
