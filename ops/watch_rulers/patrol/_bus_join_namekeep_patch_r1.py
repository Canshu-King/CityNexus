# -*- coding: utf-8 -*-
"""让「没带 --name 的 reg/join」不再把花名顶回 id——问题出在客户端，不在中枢。

10-04 11:1x 实测链：
  1) 裸 join 会把 name 从「打更人·值守」冲回 id（真跑出来的，不是读码猜）；
  2) 我先在中枢 register 里加了「保留上一份名字」，**再测仍然被冲**；
  3) 原因在 bus.py：它把 `"name": a.name or a.id` 一直发出去 ⇒ 中枢收到的是"你显式给了 name"，
     保不保留那条逻辑根本没被触发。当年的注释还写着"不必编花名（hub 会拿 id 顶上）"——
     那是花名还不存在时定的形制，现在名册里有了人话花名，这条就成了破坏源。

改法：没给 --name 就**干脆不发这个键**，把决定权留在写入口那一侧（中枢）。
"""
import ast
import io

NL = chr(10)
P = u"D:/moodle/agent_bus/bus.py"
s = io.open(P, encoding="utf-8", errors="replace").read()

old = u'''        st, res = post("/agents", {"id": a.id, "name": a.name or a.id,
                                   "note": getattr(a, "note", "") or ""})'''
new = u'''        payload = {"id": a.id, "note": getattr(a, "note", "") or ""}
        if a.name:
            payload["name"] = a.name
        # 没带 --name 就**不发这个键**：早先这里是 `a.name or a.id`，等于每次裸 join 都亲手把
        # 花名顶回 id（10-04 实测：「打更人·值守」一枚裸 join 就没了）。保留谁的旧名，
        # 由中枢 register 那一侧决定——规则要装在真正写盘的那扇门上。
        st, res = post("/agents", payload)'''
assert s.count(old) == 1, "客户端那行赋值找不到（可能被另一只手改过）"
s = s.replace(old, new, 1)
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=NL).write(s)
print("CLIENT_NAME_KEY_OMITTED AST_OK")
