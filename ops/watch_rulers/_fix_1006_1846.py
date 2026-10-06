# -*- coding: utf-8 -*-
u"""两件事：① 给五·四十九补上正文（上次写丢了）；② 给体检加一条"标题下正文非空"判据。

为什么加这条判据（10-06 18:45 实测）：我那次写五·四十九时**算出了正文却没写进去**（变量算完没用），
结果交接稿里只剩一行光标题。**结构体检当时报"全绿"**——因为它只查粘连/重影/重复行/异常标题，
查不出"标题有、正文空"。这类缺陷对下一班的伤害和粘连一样（读到一节没内容），
所以补：任一 `## ` 标题后若紧跟空行到文末、或下一行仍是标题/空行 ⇒ 判红。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
FIX = os.path.join(HERE, "_handoff_fix_r1.py")

BODY = u"""## 五·四十九、负对照来了：**真停摆 40+ 分，与交活型 42–49 分重叠 ⇒ 阈值永远分不开，只有末条形态能**

现读（18:45）：
- **分布**（census 八拍）：交活型静默中位 16.0→31.8→32.9→34.1→34.9 分，**最大 42–49 分**。
- **负对照**：五·三十八那枚真停摆（2d2d7428，末条平台错误、停在 18:00:36、被重发叫醒）**停了 40+ 分**。

⇒ **真停摆（40+ 分）与交活型（最大 42–49 分）在时长上完全重叠** ⇒ 五·四十"把 8 分调大"、
五·四十三"等分布出来就能定阈值"两条路**都被这份数据否掉了**：调阈值无论调到多少，
都会在另一侧误报或漏报。**唯一可靠的判据是末条形态**（交活语句 vs 平台错误 vs 等模型 vs 等点单），
也就是五·三十三那条规矩的深化：**先读形态，再谈时长**。

附带一句：census 本来就是每拍在落的，所以**形态分流现在就能用、不必等攒够分布**——
分布只是用来证明"阈值这条路走不通"的。

"""


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"真停摆（40+ 分）" not in t:
        head = (u"## 五·四十九、负对照来了：**真停摆 40+ 分，与交活型 42–49 分重叠"
                u" ⇒ 阈值永远分不开，只有末条形态能**")
        idx = t.find(head)
        assert idx >= 0, "找不到五·四十九的标题行"
        end = t.index(u"\n", idx) + 1
        # 标题后面紧跟着的空行吃掉，再插入正文
        while end < len(t) and t[end] in u"\n":
            end += 1
        t = t[:t.index(u"\n", idx) + 1] + u"\n" + BODY + t[end:]
        io.open(HAND, "w", encoding="utf-8", newline="").write(t)
        print("已给 五·四十九 补上正文")
    else:
        print("正文已在，不重复写")

    # 给体检加判据
    f = io.open(FIX, encoding="utf-8", newline="").read()
    if u"empty_body_head" in f:
        print("体检已带 empty_body_head，不重复加")
        return 0
    old = '''        u"decision_sheet": os.path.exists(os.path.join(HERE, u"DECISION_1006.md")),'''
    new = '''        u"decision_sheet": os.path.exists(os.path.join(HERE, u"DECISION_1006.md")),
        # 标题下正文为空（写丢了正文、光剩一行标题）：结构体检查不出，必须单独判
        u"empty_body_head": [lines[i][:34] for i, l in enumerate(lines)
                             if l.startswith(u"## ")
                             and (i + 1 >= len(lines)
                                  or lines[i + 1].startswith(u"## ")
                                  or (not lines[i + 1].strip() and i + 2 < len(lines)
                                      and lines[i + 2].startswith(u"## ")))],'''
    assert f.count(old) == 1, f.count(old)
    io.open(FIX, "w", encoding="utf-8", newline="").write(f.replace(old, new))
    print("体检已加 empty_body_head 判据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
