# -*- coding: utf-8 -*-
"""M 档别再拿死地址的信当「最老积压」（10-05 00:0x 实测，缺陷由我今天的 forget 引入）。

现场读数：M 档口径下未取 27 条，其中 2 条收件人是 `file:nightwatch`——刚被我按号令者裁语作废，
已挂 2716 分（45 小时）。这类信**永远不可能被取走**，却仍在分母里，于是：
· 板与哨兵整夜写「最老 2693 分」，读的人以为有个巨大的堵点，其实那是死信；
· 幂等键按天，明天它还会再报一次同一个死地址。

修法不是把数藏掉：死信单独数出来、单独写一行日志与一个模块级读数（像 K/L 的分母那样），
只是不再混进「谁压着信没取」的排名。返回三元组的形状不动——调用方还在按老形制解包。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_sentinel_relay_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


rep(u'''        acks = json.load(io.open(os.path.join(M_BUS, "state.json"), encoding="utf-8")).get("acks", {})
    except Exception as e:
        say(u"M 档取不到账（%s: %s）" % (type(e).__name__, str(e)[:90]))
        return None''',
    u'''        stt = json.load(io.open(os.path.join(M_BUS, "state.json"), encoding="utf-8"))
        acks = stt.get("acks", {})
        forgotten = set((stt.get("forgotten") or {}).keys())
    except Exception as e:
        say(u"M 档取不到账（%s: %s）" % (type(e).__name__, str(e)[:90]))
        return None''')

rep(u'''    aged = [(m, a) for m, a in pend if a >= thr[m.get("kind")]]
    aged.sort(key=lambda x: -x[1])
    return (len(aged), int(aged[0][1]) if aged else 0,
            sorted(set(str(m.get("to")) for m, _a in aged)))''',
    u'''    # 收件人已具名作废的信：单独数，不进「谁压着信没取」的排名——那类信永远取不走，
    # 留在分母里只会把「最老」这一格污染成假堵点（00:0x 实测：2 条挂 2716 分的死信
    # 让板整夜写「最老 2693 分」）。数照样落日志与 _M_DEAD，不藏。
    dead = [(m, a) for m, a in pend if str(m.get("to")) in forgotten]
    aged = [(m, a) for m, a in pend if str(m.get("to")) not in forgotten
            and a >= thr[m.get("kind")]]
    aged.sort(key=lambda x: -x[1])
    _M_DEAD["n"] = len(dead)
    _M_DEAD["oldest"] = int(max([a for _m, a in dead])) if dead else 0
    _M_DEAD["who"] = sorted(set(str(m.get("to")) for m, _a in dead))
    if dead:
        say(u"M 档死信 %d 条不计入分母（收件人已作废：%s，最老 %d 分）"
            % (len(dead), u"、".join(_M_DEAD["who"]), _M_DEAD["oldest"]))
    return (len(aged), int(aged[0][1]) if aged else 0,
            sorted(set(str(m.get("to")) for m, _a in aged)))''')

rep(u"def bus_unread_alarms():", u'''_M_DEAD = {"n": 0, "oldest": 0, "who": []}


def bus_unread_alarms():''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：哨兵未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"M 档死信已分列｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
