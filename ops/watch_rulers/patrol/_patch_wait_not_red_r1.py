# -*- coding: utf-8 -*-
u"""待看档判据：③格（等单）**不算红**，但留一行「等单 N 扇」在文件里。

为什么（20:34 实测）：第 7 拍的结论是「没人该敲；缺单的那 3 扇等包工头点」，
judge() 把③格非零判成红 ⇒ 待看档 20:34:08 写了"要人看"。
可"交完活等下一件"是**常态**（交接稿五·三十三那条：交活型停着不该敲）。
把常态算红 ⇒ 每 12 分钟红一次，等真出事（该敲／栈塌／未接）时就被淹掉。

改法（三处，判据只对**红**这一件事表态）：
  ③格非零 ⇒ **不**进 why，但单独收进 `_wait` 清单，
    待看档那一行末尾加「｜等单 N 扇：<名字>」，信息不丢、不占红位。
  ③格读不到数（None）⇒ 仍算红（解析不到判据不许当绿）。
  ②格／①格／⑥格／⑩格／结论行 一律照旧。

自测要加两臂：③格非零且其余全绿 ⇒ **不红**但文件里出现"等单 N 扇"；
③格数字读不到 ⇒ 仍红。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_patrol_loop_r1.py")

OLD_CELL3 = u'''    # ③不该敲：n=3，同样形制
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\\uff09")
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)'''

NEW_CELL3 = u'''    # ③不该敲：n=3，同样形制。
    # 20:34 改：**等单不算红**——「交完活等下一件」是常态（五·三十三），
    # 把它算红会让待看档每 12 分钟红一次，真出事就被淹掉。
    # 但信息不丢：交给 _wait，待看档那一行末尾照旧打出「等单 N 扇：…」。
    wait = []
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\\uff09")
        if n is None:
            why.append(v)          # 读不到数 ⇒ 仍红（不许拿默认当绿）
        elif n != 0:
            wait = [v]'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"等单不算红" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD_CELL3) != 1:
        print(u"REFUSE：③格锚命中 %d 次（应为 1），未写盘" % t.count(OLD_CELL3))
        i = t.find(u"# ③不该敲")
        print(u"现读那段：\n%s" % t[max(0, i - 120):i + 400])
        return 1
    new = t.replace(OLD_CELL3, NEW_CELL3, 1)

    # 返回值里把 _wait 带出去
    old_ret = u"    return (bool(why), why, concl, cells)"
    if new.count(old_ret) != 1:
        print(u"REFUSE：return 锚命中 %d 次，未写盘" % new.count(old_ret))
        return 1
    new = new.replace(old_ret, u"    return (bool(why), why, concl, cells, wait)", 1)

    # unpack 处跟着改
    old_unp = u'            red, why, concl, _cells = judge(txt)'
    if new.count(old_unp) != 1:
        print(u"REFUSE：unpack 锚命中 %d 次，未写盘" % new.count(old_unp))
        return 1
    new = new.replace(old_unp, u'            red, why, concl, _cells, _wait = judge(txt)', 1)

    # logline / note_eyes 里把等单那半句带上
    old_note = u'''            if note_eyes(red, why, concl, os.path.basename(out)):'''
    new_note = u'''            if _wait:
                why = list(why) + [u"（等单不占红位，见下）%s" % _wait[0]]
            if note_eyes(red, why, concl, os.path.basename(out)):'''
    if new.count(old_note) != 1:
        print(u"REFUSE：note_eyes 锚命中 %d 次，未写盘" % new.count(old_note))
        return 1
    new = new.replace(old_note, new_note, 1)

    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_waitnotred_2034"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已改：等单不占红位（备份 %s）" % os.path.basename(bak))
    print(u"改动行：")
    for l in new.splitlines():
        if u"等单不算红" in l or u"_wait" in l or u"不占红位" in l:
            print(u"  " + l.rstrip()[:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())