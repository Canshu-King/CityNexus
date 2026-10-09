# -*- coding: utf-8 -*-
"""修「等包工头点的」那一列里的人称：句子里的"你"必须指读者（主人）。

上一版补丁把列按收件人拆开了，但 _plain() 的分岔只认「是不是主人收件」，
落在包工头那列的行仍然写「等你回一句『准』或『换哪格』」——读者是主人，那句"你"就指错了人。
现在按收件人给三种口吻：主人／包工头／值守。
「站着等活的」那列同理：原来写"等你点下一格"，改成不指人的说法（那活该谁点板上另有一列写着）。
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
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:46]))
        return
    s = s.replace(old, new, 1)


rep(u'''    boss = (to == HID) or (to == u"*")
    if u"selfdecl" in low:
        if boss:
            return u"有车道自己报了下一格要干什么 ⇒ 按规矩这格归包工头（号令者）点，你不用动；要驳那句才轮到你"
        return u"他自己报了下一格要干什么 ⇒ 等你回一句「准」或「换哪格」"''',
    u'''    # 这一列的读者永远是主人，所以句子里的「你」只能指他；该别人动的必须点名。
    boss = (to == HID) or (to == u"*")
    who2 = u"你" if boss else (u"包工头" if to == CMDR_LANE else u"值守")
    if u"selfdecl" in low:
        if boss:
            return u"有车道自己报了下一格要干什么 ⇒ 按规矩这格归包工头（号令者）点，你不用动；要驳那句才轮到你"
        return u"有车道自己报了下一格要干什么 ⇒ 等%s回一句「准」或「换哪格」，不用你动手" % who2''')

rep(u'''    if kind == u"order":
        return u"有一单没人接 ⇒ 点名给谁"
    if kind == u"ask":
        return u"他在等你回话 ⇒ 给一句裁语"
    if kind == u"ruling":
        return u"有条裁语等你点头 ⇒ 准或驳"
    if kind == u"deliver":
        return u"活交上来了 ⇒ 该验收了"''',
    u'''    if kind == u"order":
        return u"有一单没人接 ⇒ 等%s点名给谁" % who2
    if kind == u"ask":
        return (u"他在等你回话 ⇒ 给一句裁语" if boss
                else u"他在等%s回话 ⇒ 该给一句裁语，不用你动手" % who2)
    if kind == u"ruling":
        return u"有条裁语等%s点头 ⇒ 准或驳" % who2
    if kind == u"deliver":
        return u"活交上来了 ⇒ 等%s验收" % who2''')

rep(u"   const ph=w.unread&&!w.why.some(x=>String(x).indexOf('静默超')>=0)\n     ?'BB 机的信压在收件框里没去取（'+w.unread+' 条）':'手上一格没走完，等你点下一格';",
    u"   const ph=w.unread&&!w.why.some(x=>String(x).indexOf('静默超')>=0)\n     ?'BB 机的信压在收件框里没去取（'+w.unread+' 条）':'手上一格没走完，等点下一格（谁点看上面那两列）';")

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：board.py 未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"人称已按收件人分岔｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
