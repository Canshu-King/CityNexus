# -*- coding: utf-8 -*-
"""给 selftest_bus.py 补 forget op 的断言（装了没测等于没装）。

九条各锁一件事，其中三条是这次裁语的真正落点：
· 发往已作废地址必须被**具名**拒（拒因里要有「已被具名作废」＋经手人＋理由）——
  落成含糊的「未注册」就不算修好：那正是今晚 M 档反复报警、别人一直往死地址投的形状。
· 作废时要把它收件框里压着的未取信点数带回来（摸掉前那条 ORD-0544 唯一裁定就是这么救回来的）。
· 那枚 id 自己回来注册要能自动解除作废（作废拦的是别人往死地址投，不是这枚腿永远不许活）。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/selftest_bus.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0

ANCHOR = u'''        st, r = req("GET", "/agents")
        check("两个 transport 都在册（qoder + codex）", "%s%s" % (list(r)[0], list(r)[1]), "qoder:cmdr01")'''

NEW = ANCHOR + u'''

        # ── forget op（10-04 号令者裁：作废与「别再往死地址投」必须同一扇门）──
        req("POST", "/agents", {"id": "file:deadend1", "name": u"死信·探针", "note": u""})
        req("POST", "/messages", {"from": "qoder:cmdr01", "to": "file:deadend1", "kind": "note",
                                  "topic": u"作废前先压一条", "body": u"这条要在作废时被点到数"})
        st, r = req("POST", "/agents/forget", {"id": "file:deadend1", "by": "qoder:cmdr01",
                                               "reason": u"探针：地址已死"})
        check(u"forget 具名作废要回 200", st, 200)
        check(u"作废时点数它收件框压着的未取信", r.get("held_undelivered"), 1)
        st, r = req("GET", "/agents")
        check(u"作废之后名册里没有它", "file:deadend1" in r, False)
        st, r = req("POST", "/messages", {"from": "qoder:cmdr01", "to": "file:deadend1", "kind": "note",
                                          "topic": u"还要往死地址投", "body": u"这条不该进账"})
        check(u"发往已作废地址被写门拒收", st, 422)
        why = u"；".join((r or {}).get("reasons") or [])
        check(u"拒因要具名：写「已被具名作废」＋经手人＋理由，不许落成含糊的「未注册」",
              all(x in why for x in (u"已被具名作废", u"qoder:cmdr01", u"探针：地址已死")), True)
        req("POST", "/agents", {"id": "file:deadend1", "note": u""})      # 那枚腿自己回来了
        st, r = req("GET", "/agents")
        check(u"它自己重新注册 ⇒ 作废自动解除（不是永久封死）", "file:deadend1" in r, True)
        st, r = req("POST", "/agents/forget", {"id": "file:deadend1", "by": "qoder:cmdr01", "reason": u""})
        check(u"不写理由不许作废（破坏性动作要留因）", st, 422)
        st, r = req("POST", "/agents/forget", {"id": "file:deadend1", "by": "qoder:nobody9",
                                               "reason": u"匿名作废"})
        check(u"经手人不在册不许作废", st, 422)'''

if s.count(ANCHOR) != 1:
    sys.exit(u"ABORT：锚命中 %d 次，未改动" % s.count(ANCHOR))
s = s.replace(ANCHOR, NEW, 1)
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"自测已加 9 条 forget 断言｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
