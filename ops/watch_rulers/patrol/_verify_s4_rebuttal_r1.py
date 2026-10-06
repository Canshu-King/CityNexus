# -*- coding: utf-8 -*-
"""值守 07:09 · 复核 1d64acf5 对我 06:55 那两笔读数的反驳（全只读，不落任何写）。

要判的是两条：
  A 我说的「2 枚文件各 3 段」到底是冲突块还是 merge-tree 的 stage 行；
  B 我建议的「先落 mapFocus.ts / V12AuthoritativeJourneyPanel.tsx」在现尖上是不是死代码。
"""
import os
import re
import subprocess as sp
import tempfile
import collections
import sys

REPO = r"D:/moodle/CityNexus"
TIP = "f26e2ff78c047579a7d710d3a469be6bdf9a0540"
BR = "11eee48da2b117a2c0aafb2d71c50b0104b7d1fb"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")


def run(*args):
    r = sp.run(list(args), capture_output=True, text=True, encoding="utf-8",
               errors="replace", cwd=REPO, env=ENV)
    out = (r.stdout or "")
    if r.returncode:
        out += "ERR " + (r.stderr or "")[:200]
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    mb = run("git", "merge-base", TIP, BR).strip()
    print("merge-base 现读 %s（我 06:55 报的是 b6a8ea5c625d7e3e82f7348fad57d595a8a403c0）" % mb)

    r = sp.run(["git", "merge-tree", "--write-tree", TIP, BR], capture_output=True,
               text=True, encoding="utf-8", errors="replace", cwd=REPO, env=ENV)
    stage = collections.Counter()
    for l in (r.stdout or "").split("\n")[1:]:
        m = re.match(r"^(\d+) [0-9a-f]+ (\d+)\t(.+)$", l.strip())
        if m:
            stage[m.group(3)] += 1
    print("A) merge-tree 的 stage 行数（不是冲突块数）: %s rc=%d" % (dict(stage), r.returncode))

    for f in ("frontend/src/app/V8Experience.tsx", "frontend/src/components/v8/MapPanel.tsx"):
        sides = [run("git", "show", "%s:%s" % (TIP, f)),
                 run("git", "show", "%s:%s" % (mb, f)),
                 run("git", "show", "%s:%s" % (BR, f))]
        fps = []
        for txt in sides:
            t = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".f")
            t.write(txt)
            t.close()
            fps.append(t.name)
        rr = sp.run(["git", "merge-file", "-p", "--diff3", fps[0], fps[1], fps[2]],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    cwd=REPO, env=ENV)
        merged = rr.stdout or ""
        blocks = merged.count("<<<<<<<")
        # 逐块数两侧行数：按标记行扫，不用大正则（上一条把括号写崩过）
        cur = None
        sizes = []
        ours_n = their_n = 0
        for line in merged.split("\n"):
            if line.startswith("<<<<<<<"):
                cur = "ours"
                ours_n = their_n = 0
            elif line.startswith("|||||||") and cur == "ours":
                cur = "base"
            elif line.startswith("=======") and cur in ("ours", "base"):
                cur = "theirs"
            elif line.startswith(">>>>>>>") and cur == "theirs":
                sizes.append((their_n, ours_n))
                cur = None
            elif cur == "ours":
                ours_n += 1
            elif cur == "theirs":
                their_n += 1
        print("B) %-52s 冲突块 %d 块，(车道枝侧行数, 现尖侧行数)=%s" % (f.split("/")[-1], blocks, sizes))
        for p in fps:
            os.unlink(p)

    print("C) 现尖上 mapFocus 的消费方（逐字 `git grep -l mapFocus %s -- frontend/src`）:" % TIP[:8])
    g = run("git", "grep", "-l", "mapFocus", TIP, "--", "frontend/src").strip()
    print("   %s" % (g.replace("\n", ", ") if g else "  ↑ 0 个（该文件在现尖上没有引用者）"))
    print("   现尖上这枚文件本身存在吗: cat-file -e -> %s" % (
        "存在" if sp.call(["git", "cat-file", "-e", "%s:frontend/src/lib/mapFocus.ts" % TIP],
                         cwd=REPO, env=ENV) == 0 else "不存在"))
    print("D) V12AuthoritativeJourneyPanel 在现尖: %s" % (
        "存在" if sp.call(["git", "cat-file", "-e",
                          "%s:frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx" % TIP],
                         cwd=REPO, env=ENV) == 0 else "不存在"))
    print("   现尖上它的消费方: %s" % (run("git", "grep", "-l", "V12AuthoritativeJourneyPanel", TIP,
                                          "--", "frontend/src").strip().replace("\n", ", ") or "（0 个）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
