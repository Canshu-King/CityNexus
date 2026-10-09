# -*- coding: utf-8 -*-
"""给 BB 机加一条具名 forget op（号令者 10-04 裁：点「加一条具名 forget op」）。

裁语原话：「写门上把『往已作废地址发信』一起拒，语义集中在一个工具里比让号令者手改 state.json
安全（state.json 直接改没有审计痕迹）。作废地址 = file:nightwatch 与 codex:laneE7。」

这一版装了四件事，缺一件就不算"集中在一个工具里"：
① POST /agents/forget：从名册摸掉 + 记下 by/at/reason + 摸之前清点它收件框里压着几条未取（写进审计）；
② validate() 里把「发往已作废地址」单独拒一条具名理由——不能让它落到「未注册」那句含糊话上，
   那正是今晚 M 档反复报警、别人一直往死地址投的原因；
③ 那枚 id 自己回来注册 ⇒ 作废自动解除并补一行审计。作废拦的是"别人往死地址投"，
   不是"这枚腿永远不许活"；
④ 审计另落 forget.log（追加式），state.json 之外再有一份人能直接 tail 的痕迹。

改的是共享写门，所以逐条 assert 命中 + ast.parse 通过才落盘；跑自测时不并发（探针名会过命名闸）。
"""
import ast
import io
import sys

HUB = u"D:/moodle/agent_bus/bus_hub.py"
CLI = u"D:/moodle/agent_bus/bus.py"
h0 = io.open(HUB, encoding="utf-8", errors="replace").read()
c0 = io.open(CLI, encoding="utf-8", errors="replace").read()
h, c = h0, c0
miss = []


def rep(store, old, new):
    """三参形制：store 选文件，标签从 old 头一段自动取（省得我给每条再编一遍名字）。"""
    global h, c
    label = old.strip().splitlines()[0][:34]
    cur = h if store == u"h" else c
    if cur.count(old) != 1:
        miss.append(u"%s（命中 %d 次）" % (label, cur.count(old)))
        return
    newv = cur.replace(old, new, 1)
    if store == u"h":
        h = newv
    else:
        c = newv


# ──  审计落盘的位置与一行式写手 ────────────────────────────────────────────
rep(u"h", u"STATE = os.path.join(ROOT, \"state.json\")",
    u'''STATE = os.path.join(ROOT, "state.json")
# 作废是破坏性动作，痕迹不能只躺在 state.json 里（那文件谁都可能在编辑器里顺手改）。
FORGOT_LOG = os.path.join(ROOT, "forget.log")''')

rep(u"h", u"def validate(rec, st):",
    u'''def _forgot_line(text):
    u"""追加一行作废审计；写不进去就抛——审计缺一条比不记更糟（它会让人以为没发生过）。"""
    with io.open(FORGOT_LOG, "a", encoding="utf-8") as fh:
        fh.write(u"%s｜%s\\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))


def forget(b):
    u"""具名作废一枚地址：摸出名册 + 记 by/at/reason + 清点它压着的未取信。

    为什么要有这条 op（号令者 10-04 裁）：手改 state.json 没有痕迹；而「作废」和
    「别再往这投」必须发生在同一个工具里，否则名册摸掉了、别人的脚本还在往里灌。
    """
    aid = unicode_s(b.get("id")).strip()
    by = unicode_s(b.get("by")).strip()
    why = unicode_s(b.get("reason")).strip()
    if not aid:
        return ({"error": "forget 要带 --id（可多枚，逐枚作废）"}, 422)
    if not by:
        return ({"error": "forget 要带 --by：作废是破坏性动作，得留谁经的手"}, 422)
    if not why:
        return ({"error": "forget 要带 --reason：为什么作废，写下来"}, 422)
    st = load_state()
    if by not in st["agents"]:
        return ({"error": "by=%s 自己都不在册，不能替名册做主" % by}, 422)
    held = [m.get("id") for m in messages()
            if m.get("to") == aid and not m.get("delivered_at")]
    a = st["agents"].pop(aid, None)
    if a is None and aid not in (st.get("forgotten") or {}):
        return ({"error": "名册里没有 %s，也没有它的作废记录（先 status --agents 看看是不是写错了 id）"
                        % aid, "held_undelivered": len(held)}, 404)
    st.setdefault("forgotten", {})[aid] = {
        "at": time.time(), "by": by, "reason": why,
        "name": (a or {}).get("name") or aid,
        "held_undelivered": len(held), "held_ids": held[:20]}
    save_state(st)
    _forgot_line(u"作废 %s｜经手 %s｜理由：%s｜摸掉时收件框压着未取 %d 条：%s"
                 % (aid, by, why, len(held), u",".join(held[:20]) or u"（无）"))
    say(u"作废 %s（by=%s；摸掉前压着 %d 条未取）" % (aid, by, len(held)))
    return {"forgotten": aid, "by": by, "reason": why,
            "held_undelivered": len(held), "held_ids": held[:20],
            "log": FORGOT_LOG}, 200


def validate(rec, st):''')

# ──  写门：发往已作废地址单独拒一条具名理由 ────────────────────────────────
rep(u"h", u'''    to = str(rec.get("to", "*"))
    if to != "*" and to not in st["agents"]:
        bad.append("to=%s 未注册" % to)''',
    u'''    to = str(rec.get("to", "*"))
    fg = st.get("forgotten") or {}
    if to in fg:
        e = fg[to] or {}
        bad.append(u"to=%s 已被具名作废（%s 于 %s 摸掉，理由：%s）⇒ 别再往这投。"
                   u"要复活只能让那枚 id 自己 POST /agents，注册会自动解除作废并补一行审计"
                   % (to, e.get("by", u"?"),
                      time.strftime("%m-%d %H:%M", time.localtime(float(e.get("at", 0)))),
                      e.get("reason", u"")))
    elif to != "*" and to not in st["agents"]:
        bad.append("to=%s 未注册" % to)''')

# ── ③ 那枚 id 自己回来注册 ⇒ 解除作废并留痕 ─────────────────────────────────
rep(u"h", u'''    st = load_state()
    now2 = time.time()
    prev = st["agents"].get(aid)''',
    u'''    st = load_state()
    now2 = time.time()
    prev = st["agents"].get(aid)
    # 曾被作废的 id 自己回来注册：作废自动解除。作废拦的是「别人往死地址投」，
    # 不是「这枚腿永远不许活」；解除也要落一行，否则它就名单上无声消失了。
    revived = (st.get("forgotten") or {}).pop(aid, None)
    if revived:
        _forgot_line(u"解除作废 %s｜它自己重新注册回来（上次由 %s 于 %s 作废，理由：%s）"
                     % (aid, revived.get("by", u"?"),
                        time.strftime("%m-%d %H:%M",
                                      time.localtime(float(revived.get("at", 0)))),
                        revived.get("reason", u"")))''')

# ──  路由 ─────────────────────────────────────────────────────────────────
rep(u"h", u'''        if u.path == "/messages":
            m, bad = ingest(b, via="http")''',
    u'''        if u.path == "/agents/forget":
            obj, code = forget(b)
            return self._j(code, obj)
        if u.path == "/messages":
            m, bad = ingest(b, via="http")''')

# ──  客户端：bus.py forget ────────────────────────────────────────────────
rep(u"c", u'    p = sub.add_parser("read"); p.add_argument("--agent", required=True); p.add_argument("--kind", default="")',
    u'''    p = sub.add_parser("forget")
    p.add_argument("--id", action="append", required=True, help="可多枚，逐枚作废")
    p.add_argument("--by", required=True, help="经手人（必须在册，作废不留名就不许做）")
    p.add_argument("--reason", required=True, help="为什么作废；写门此后逐字回给撞上来的人")
    p = sub.add_parser("read"); p.add_argument("--agent", required=True); p.add_argument("--kind", default="")''')

rep(u"c", u'    if a.op == "send":',
    u'''    if a.op == "forget":
        done, bad = [], []
        for aid in a.id:
            st, res = post("/agents/forget", {"id": aid, "by": a.by, "reason": a.reason})
            done.append(res)
            if st != 200:
                bad.append(aid)
        return out({"results": done, "refused": bad,
                    "next": u"作废名单在 state.json 的 forgotten 段，另有可 tail 的 forget.log；"
                            u"此后谁发往这些地址，写门会带着 by 和理由逐字拒给他"},
                   0 if not bad else 2)

    if a.op == "send":''')

if miss:
    for m in miss:
        print(u"未命中 →", m)
    sys.exit(u"ABORT：%d 条没落上，两个文件都未改动" % len(miss))
ast.parse(h)
ast.parse(c)
io.open(HUB, "w", encoding="utf-8", newline=chr(10)).write(h)
io.open(CLI, "w", encoding="utf-8", newline=chr(10)).write(c)
print(u"forget op 已装：bus_hub.py %d→%d｜bus.py %d→%d 字节"
      % (len(h0.encode("utf-8")), len(h.encode("utf-8")),
         len(c0.encode("utf-8")), len(c.encode("utf-8"))))
