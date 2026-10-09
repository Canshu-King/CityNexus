# -*- coding: utf-8 -*-
u"""待看档：等单不算红（结论行与③格两处一起改）。

为什么（20:34–20:35 实测）：
  第 7 拍结论是「没人该敲；缺单的那 3 扇等包工头点」，judge() 判红 ⇒ 待看档 20:34:08 写"要人看"。
  可"交完活等下一件"是常态（交接稿五·三十三），把常态算红 ⇒ 每 12 分钟红一次，
  真出事（该敲／栈塌／未接）时就被淹掉。

两处一起改，缺一不可（我 20:35 第一版只改了③格，漏了结论行 ⇒ 照旧红，白改）：
  ① 结论行：巡逻的结论有四种形态，只有两种是真问题。
       「全队都在动」　　　　　　⇒ 绿
       「没人该敲；缺单的那 N 扇…」 ⇒ **常态，不算红**
       「有 N 扇末态不可判…」　　　⇒ 真问题（那是判词读不到）
       「有扇该敲」　　　　　　　⇒ 真问题
  ② ③格（不该敲＝等单）非零 ⇒ 不进 why，收进 `_wait`，待看档那行末尾照旧打出等单清单。
     但③格**读不到数**时仍算红（解析不到判据不许当绿）。

回滚说明：20:35 我用 shell 改结论行时把锚替了两遍、函数也没插进去，
已从 `_patrol_loop_r1.py.bak_waitnotred_2034`（改动前的干净版）重来。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_patrol_loop_r1.py")
CLEAN = os.path.join(HERE, "_patrol_loop_r1.py.bak_waitnotred_2034")

FN = u'''def _concl_is_waiting(concl):
    u"""结论行说的是「没人该敲；缺单的那 N 扇等包工头点」⇒ 不算红（那是常态）。

    20:34 装：巡逻结论有四种形态，只有两种是真问题——
    「有扇该敲」与「N 扇末态不可判」。「没人该敲＋等单」是交活型停着（五·三十三），
    每 12 分钟都会出现一次，算红就把它淹了。
    判词从**这一拍读到的结论行**里取，取不到就当不算等待（交给别的格去判红）。
    """
    if not concl:
        return False
    return (u"没人该敲" in concl) and (u"等包工头点" in concl)


'''

OLD_CELL3 = u'''    # ③不该敲：n=3，同样形制
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\\uff09")
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)'''

NEW_CELL3 = u'''    # ③不该敲：n=3，同样形制。20:34 改：**等单不算红**（常态，五·三十三）。
    # 信息不丢：收进 _wait，待看档那行末尾照旧打出「等单 N 扇：…」。
    # 但**读不到数**时仍算红——解析不到判据不许当绿。
    wait = []
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\\uff09")
        if n is None:
            why.append(v)
        elif n != 0:
            wait = [v]'''


def main():
    src = CLEAN if os.path.exists(CLEAN) else SRC
    t = io.open(src, encoding="utf-8", newline="").read()
    if u"_concl_is_waiting" in t and u"等单不算红" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if src != SRC:
        print(u"从改动前的干净备份重来：%s" % os.path.basename(src))

    steps = []

    # ① 插函数（在 _mark 之前）
    anchor = u"def _mark(n):"
    if t.count(anchor) != 1:
        print(u"REFUSE：_mark 锚命中 %d 次，未写盘" % t.count(anchor))
        return 1
    t = t.replace(anchor, FN + anchor, 1)
    steps.append(u"插 _concl_is_waiting()")

    # ② 结论行判据
    old_c = u"    elif GREEN not in concl:"
    if t.count(old_c) != 1:
        print(u"REFUSE：结论行锚命中 %d 次，未写盘" % t.count(old_c))
        return 1
    t = t.replace(old_c, u"    elif GREEN not in concl and not _concl_is_waiting(concl):", 1)
    steps.append(u"结论行认「等单」形态")

    # ③ ③格
    if t.count(OLD_CELL3) != 1:
        print(u"REFUSE：③格锚命中 %d 次，未写盘" % t.count(OLD_CELL3))
        return 1
    t = t.replace(OLD_CELL3, NEW_CELL3, 1)
    steps.append(u"③格非零不判红")

    # ④ 返回值带 _wait
    old_r = u"    return (bool(why), why, concl, cells)"
    if t.count(old_r) != 1:
        print(u"REFUSE：return 锚命中 %d 次，未写盘" % t.count(old_r))
        return 1
    t = t.replace(old_r, u"    return (bool(why), why, concl, cells, wait)", 1)
    steps.append(u"返回值带 _wait")

    # ⑤ unpack
    old_u = u"            red, why, concl, _cells = judge(txt)"
    if t.count(old_u) != 1:
        print(u"REFUSE：unpack 锚命中 %d 次，未写盘" % t.count(old_u))
        return 1
    t = t.replace(old_u, u"            red, why, concl, _cells, _wait = judge(txt)", 1)
    steps.append(u"unpack 跟上")

    # ⑥ 等单那半句仍写进日志行
    old_n = u"            if note_eyes(red, why, concl, os.path.basename(out)):"
    if t.count(old_n) != 1:
        print(u"REFUSE：note_eyes 锚命中 %d 次，未写盘" % t.count(old_n))
        return 1
    t = t.replace(old_n,
                  u"            if _wait:\n"
                  u"                why = list(why) + [u\"等单不占红位：%s\" % _wait[0]]\n"
                  u"            if note_eyes(red, why, concl, os.path.basename(out)):", 1)
    steps.append(u"等单清单照旧写进日志")

    try:
        ast.parse(t)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1

    bak = SRC + u".bak_waitnotred2_2036"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(
            io.open(SRC, encoding="utf-8", newline="").read())
    io.open(SRC, "w", encoding="utf-8", newline="").write(t)
    tmp = SRC + u".bak_tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
        print(u"（清掉了 20:35 那次半成品的 .bak_tmp）")
    print(u"已改 %d 处：%s" % (len(steps), u"；".join(steps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())