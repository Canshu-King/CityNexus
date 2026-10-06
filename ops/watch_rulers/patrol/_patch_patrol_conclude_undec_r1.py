# -*- coding: utf-8 -*-
u"""巡逻结论行把「②b 末态不可判」也并进去，别让不可判被读成"全队都在动"。

为什么（单向致盲那一形）：形状闸把"判词读不到"单开了一格②b，但它**没进结论行**——
结论行只看 `knock` 是否为空（现读那段：
`print(u"结论：%s" % (u"有扇该敲" if knock else (u"没人该敲；缺单的那 %d 扇…" if waiting else u"全队都在动")))`）。
于是"有三扇判词读不到、零扇真该敲"会被结论行报成**全队都在动**，
待看档与下一班都读成绿——**形状闸越界的那些扇没人看见**。
这是我自己那条"单向致盲的尺也算仪器缺陷"：②b 看得见、结论行看不见，两者不一致。

改法（只动这一处 print）：
  knock 非空              ⇒ 有扇该敲（不变）
  否则 undecidable 非空   ⇒ 有 N 扇末态不可判（**不算绿**）
  否则 waiting 非空       ⇒ 没人该敲；缺单的那 N 扇等包工头点（不变）
  否则                    ⇒ 全队都在动（不变）
跑法：python _patch_patrol_conclude_undec_r1.py
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")

OLD = u'''    print(u"结论：%s" % (u"有扇该敲" if knock else
                        (u"没人该敲；缺单的那 %d 扇等包工头点" % len(waiting) if waiting else u"全队都在动")))'''

NEW = u'''    # 不可判**不算绿**（20:18 装）：②b 那几扇若不进结论行，待看档与下一班都会把它读成"全队都在动"
    # ——单向致盲：②b 看得见、结论行看不见。形状闸越界的那些扇不能没人看见。
    if knock:
        _concl = u"有扇该敲"
    elif undecidable:
        _concl = u"有 %d 扇末态不可判（判词读不到，不算绿）" % len(undecidable)
    elif waiting:
        _concl = u"没人该敲；缺单的那 %d 扇等包工头点" % len(waiting)
    else:
        _concl = u"全队都在动"
    print(u"结论：%s" % _concl)'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"不算绿" in t and u"_concl" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：结论行锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        i = t.find(u"print(u\"结论：")
        print(u"现读那段：\n%s" % t[max(0, i - 200):i + 260])
        return 1
    new = t.replace(OLD, NEW, 1)
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_conclude_1218"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已并入不可判（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())