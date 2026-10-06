# -*- coding: utf-8 -*-
"""值守 07:10 · 把「哪一侧是 29 行」钉死：用正文回认，不用 arg 顺序推。

做法：对每个冲突块取「<<<<<<<…|||||||」之间那段与「=======…>>>>>>>」之间那段，
分别拿这两段的原文去 `git show <rev>:path` 的两个 blob 里找——正文在哪个 blob 里，
那一侧就是谁。两侧都找到或都找不到就具名报不可判，不猜。
"""
import os
import re
import subprocess as sp
import sys

REPO = r"D:/moodle/CityNexus"
TIP = "f26e2ff78c047579a7d710d3a469be6bdf9a0540"
BR = "11eee48da2b117a2c0aafb2d71c50b0104b7d1fb"
MB = "b6a8ea5c625d7e3e82f7348fad57d595a8a403c0"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")


def show(rev, path):
    r = sp.run(["git", "show", "%s:%s" % (rev, path)], capture_output=True,
               text=True, encoding="utf-8", errors="replace", cwd=REPO, env=ENV)
    return r.stdout or ""


def blocks(ours, base, theirs):
    """`git merge-file -p --diff3` 之后按标记切块，返回 [(A段行, B段行, 中段行)]。"""
    import tempfile
    fp = []
    for txt in (ours, base, theirs):
        t = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".f")
        t.write(txt)
        t.close()
        fp.append(t.name)
    r = sp.run(["git", "merge-file", "-p", "--diff3", fp[0], fp[1], fp[2]],
               capture_output=True, text=True, encoding="utf-8", errors="replace",
               cwd=REPO, env=ENV)
    for p in fp:
        os.unlink(p)
    out = []
    seg = None
    a = b = c = None
    for line in (r.stdout or "").split("\n"):
        if line.startswith("<<<<<<<"):
            seg = "a"
            a, b, c = [], [], []
        elif line.startswith("|||||||") and seg == "a":
            seg = "c"
        elif line.startswith("=======") and seg in ("a", "c"):
            seg = "b"
        elif line.startswith(">>>>>>>") and seg == "b":
            out.append((a, c, b))
            seg = None
        elif seg == "a":
            a.append(line)
        elif seg == "c":
            c.append(line)
        elif seg == "b":
            b.append(line)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for path in ("frontend/src/app/V8Experience.tsx", "frontend/src/components/v8/MapPanel.tsx"):
        tip_txt = show(TIP, path)
        br_txt = show(BR, path)
        mb_txt = show(MB, path)
        # arg 顺序：current=现尖, base=merge-base, other=车道枝
        bs = blocks(tip_txt, mb_txt, br_txt)
        print("== %s：merge-file 冲突块 %d 块（arg 序：current=现尖 / other=车道枝）" % (path, len(bs)))
        for i, (cur_seg, base_seg, oth_seg) in enumerate(bs, 1):
            def where(seg):
                body = "\n".join(seg).strip("\n")
                if not body:
                    return "空"
                in_tip = body in tip_txt
                in_br = body in br_txt
                return ("现尖" if in_tip else "") + ("/车道枝" if in_br else "") or "两处都没有"
            print("   块%d  current侧 %2d 行[%s]  other侧 %2d 行[%s]" %
                  (i, len([x for x in cur_seg if x.strip()]), where(cur_seg),
                   len([x for x in oth_seg if x.strip()]), where(oth_seg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
