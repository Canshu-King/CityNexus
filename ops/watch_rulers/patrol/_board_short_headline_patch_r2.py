# -*- coding: utf-8 -*-
"""把主句里重复的"等谁"去掉——下面那行已经写着「说给『号令者』」了。

00:29 截图上看得见的毛病：「等包工头点的」那一列连着三行主句都是
「他说：下一件我这么干，等值守点头」，三行只差人名；而每行下面本来就有
「电焊工·老王 · 说给『号令者』 · 最久 22 小时」。同一个信息说两遍，扫起来就累。

主句只留"发生了什么事"，"对谁"交给下面那行。判据、条数、年龄一律不动。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/board.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip()[:44]))
        return
    s = s.replace(old, new, 1)


rep(u'        return u"他说：下一件我这么干，等%s点头" % who2',
    u'        return u"他报了下一件怎么干，等点头"')
rep(u'        return u"他交了活，等%s验收" % who2',
    u'        return u"他交了活，等验收"')
rep(u'        return u"他在等你回话" if boss else u"他问了句话，等%s答" % who2',
    u'        return u"他在等你回话" if boss else u"他问了句话，等回话"')
rep(u'        return u"有条裁语等%s点头" % who2',
    u'        return u"有条裁语等点头"')
rep(u"     ?'BB 机的信压在收件框里没去取（'+w.unread+' 条）':'手上一格没走完，等点下一格（谁点看上面那两列）';",
    u"     ?'信压着没去取（'+w.unread+' 条）':'活干到一半停了，等点下一格';")

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"主句去重｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
