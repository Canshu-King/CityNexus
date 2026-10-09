# -*- coding: utf-8 -*-
u"""把交接稿附录清单里的裸文件名补成实际路径（今晚它们都在 patrol/ 子目录下）。

为什么：清单里写裸名，下一班（或我明天）在 live_checks/ 下按名找会全部"无"——
那正是「引用会失效」那族（`feedback-citation-rot-in-shipped-comments` 的精神）：
清单必须能被人按图索骥找到，裸名不是路径。
只补真实存在的（存在则写实际路径、不存在保持原样并待人核）。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

PAT = re.compile(r"`(_[A-Za-z0-9_]+\.py)`")


def fix(m):
    name = m.group(1)
    for cand in (name, os.path.join("patrol", name)):
        if os.path.exists(os.path.join(HERE, cand)):
            return "`%s`" % cand.replace(os.sep, "/")
    return m.group(0)


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    new = PAT.sub(fix, t)
    bare = PAT.findall(new)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print("已补实际路径；仍是裸名的：%s" % (bare or "无"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
