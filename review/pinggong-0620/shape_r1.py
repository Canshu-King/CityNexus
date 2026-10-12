# -*- coding: utf-8 -*-
"""0620 枝的远端形状与改动面现读（尖不写死，从 GitHub 现取）。"""
import subprocess
import sys

BARE = "D:/moodle/CityNexus"
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/pinggong-0620-r1"
LINES = []


def git(*a, cwd=REPO):
    proc = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout.strip()
    LINES.append("CMD %s -> rc=%d -> %s" % (" ".join(a), proc.returncode, out[:220]))
    return out, proc.returncode


tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1",
          cwd=BARE)[0].split("\t")[0]
head = git("rev-parse", "HEAD", cwd=TREE)[0]
LINES.append("现尖 %s｜枝尖 %s" % (tip, head))
for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    out = git("ls-remote", "origin", BRANCH, cwd=cwd)[0]
    LINES.append("READBACK %s：%s" % (label, out))
    if not out or out.split("\t")[0] != head:
        print("ABORT %s 侧回读不是本轮头" % label)
        sys.exit(1)
kind_b = git("cat-file", "-t", head, cwd=BARE)[0]
kind_i = git("cat-file", "-t", head, cwd=REPO)[0]
LINES.append("CATFILE bare=%s integration=%s" % (kind_b, kind_i))
counts = git("rev-list", "--left-right", "--count", "%s...%s" % (tip, head))[0]
merged, mrc = git("merge-tree", "--write-tree", tip, head)
status = git("status", "--porcelain", cwd=TREE)[0]
diff = git("diff", "--name-only", "%s...%s" % (tip, head), cwd=TREE)[0]
LINES.append("先人位（左=现尖独有 右=本枝独有）：%s" % counts)
LINES.append("只读合流预测 rc=%d 写树=%s" % (mrc, merged.splitlines()[0][:40]))
LINES.append("工作树未登记改动 %d 处" % (0 if not status else len(status.splitlines())))
LINES.append("本枝相对现尖改动面 %d 枚：%s" % (len(diff.splitlines()), diff.replace("\n", " | ")))
blob = git("rev-parse", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % head)[0]
LINES.append("入表后那枚对账表的 blob %s（%d 字节）" % (blob, len(git("show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % head)[0]) + 1))
with open("D:/moodle/_qoder_pinggong_0588/review/pinggong-0620/branch_shape.txt", "w",
          encoding="utf-8", newline="\n") as h:
    h.write("\n".join(LINES) + "\n")
print("\n".join(LINES[-6:]))
