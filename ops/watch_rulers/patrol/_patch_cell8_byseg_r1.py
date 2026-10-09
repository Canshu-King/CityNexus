# -*- coding: utf-8 -*-
u"""第⑧格改成按 `｜` 切段打印，不再按 120 字硬砍。

为什么（20:32 实测）：原写法是 `seg[seg.index(u"已送未拆"):][:120]`——
哨兵那一轮总结里这一段**原文 455 字**，被砍到 120 字，砍掉的 41 字里有：
  · 第三扇的名字（a68b0631 浇筑工·老钱 交1129 分/静28 分）
  · 段尾的 **「｜红」**——也就是"这一轮哨兵判了红"这半句判语。
⇒ 每拍都在丢一句判语，而我每拍把它当完整读数转述。**按字数砍句子＝按字数砍判语。**

改法：先按 `｜` 切，取从「已送未拆」起的那几段，**逐段整段打印**（不截断）；
段数超上限时截的是**段数**并明写"还有 N 段没打"，不是把段腰斩。
那半句「｜红」会自己落在某一段里，不会被腰斩丢掉。

安全：只动这一处 print 与它上面的 seg 取法；⑧格判据仍只有哨兵那一份，不另算。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")

OLD = u'''        seg = next((l for l in reversed(sl) if u"已送未拆" in l), None)
        if seg is None:
            print(u"⑧ 已送未拆：那一轮总结里没有这一段 ⇒ 不可得（不当零）")
        else:
            print(u"⑧ 已送未拆（哨兵同一次读数）：%s" % seg[seg.index(u"已送未拆"):][:120])'''

NEW = u'''        seg = next((l for l in reversed(sl) if u"已送未拆" in l), None)
        if seg is None:
            print(u"⑧ 已送未拆：那一轮总结里没有这一段 ⇒ 不可得（不当零）")
        else:
            # 按 `｜` 切段、逐段**整段**打（20:32 装）。原来按 120 字硬砍，
            # 把第三扇的名字和段尾那半句「｜红」（＝这一轮哨兵判红）一起砍掉了——
            # 按字数砍句子＝按字数砍判语。超上限时截**段数**并明写还有几段没打，不腰斩。
            _i = seg.index(u"已送未拆")
            _parts = [p for p in seg[_i:].split(u"｜") if p.strip()]
            _MAXP = 6
            for _p in _parts[:_MAXP]:
                print(u"⑧ %s" % _p.strip())
            if len(_parts) > _MAXP:
                print(u"⑧ （还有 %d 段没打，见哨兵日志同名段）" % (len(_parts) - _MAXP))'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"_MAXP" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        i = t.find(u'⑧ 已送未拆')
        print(u"现读那段：\n%s" % t[max(0, i - 300):i + 300])
        return 1
    new = t.replace(OLD, NEW, 1)
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_cell8seg_2032"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已改按段打印（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())