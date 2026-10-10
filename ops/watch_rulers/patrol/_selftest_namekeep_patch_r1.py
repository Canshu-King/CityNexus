# -*- coding: utf-8 -*-
"""给 selftest_bus.py 加两枚"花名保真"断言（一正一反），把今天修的行为钉住。

背景（10-04 11:1x 实测）：车道重启后跑的是 `bus.py join --id 自己`，不带 --name；
旧客户端把 `"name": a.name or a.id` 一路发出去 ⇒ 名册里刚挂好的人话花名一枚裸 join 就被顶回 id。
主人今天的原话是「只有认得到士兵的将军才是好将军」——花名被冲掉，光荣榜和耻辱墙就又变成一排 hex。
所以这条要钉进自测，不靠人记得。
"""
import ast
import io

NL = chr(10)
P = u"D:/moodle/agent_bus/selftest_bus.py"
s = io.open(P, encoding="utf-8", errors="replace").read()

BLOCK = u'''        # 花名保真（10-04 11:1x 实测到的破坏链：一枚裸 join 就把「打更人·值守」顶回 id）
        req("POST", "/agents", {"id": "qoder:tagtest1", "name": u"临时工·小探", "note": u""})
        req("POST", "/agents", {"id": "qoder:tagtest1", "note": u""})      # 不带 name 的重注册＝车道重启后那一形
        st, r = req("GET", "/agents")
        check(u"不带 name 的重注册不许把花名顶回 id",
              r.get("qoder:tagtest1", {}).get("name"), u"临时工·小探")
        req("POST", "/agents", {"id": "qoder:tagtest1", "name": u"改名·第二次", "note": u""})
        st, r = req("GET", "/agents")
        check(u"显式给了 name 仍然要能改",
              r.get("qoder:tagtest1", {}).get("name"), u"改名·第二次")

'''

anchor = u'        st, r = req("GET", "/agents")\n        check("两个 transport 都在册'
assert s.count(anchor) == 1, "锚不定（可能被另一只手改过）"
s = s.replace(anchor, BLOCK + anchor, 1)
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=NL).write(s)
print("SELFTEST_NAMECASES_ADDED AST_OK")
