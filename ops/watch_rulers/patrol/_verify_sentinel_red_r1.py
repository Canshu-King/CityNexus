# -*- coding: utf-8 -*-
u"""哨兵 J 档红因的流水核实：89f2e2d6 断在半路 + 三扇交完活停着。

为什么必须自己读一遍：哨兵 19:28:51 判红早退，红因是它**报的事实**，
按规矩「别人给的成因是假设」⇒ 自己打开 jsonl 看末条。
四扇各自报三样：末条形态（assistant/tool/user 各是什么）、末条距今几分钟、倒数第二条是什么。
「断在半路」= 末条是 tool_use 且没有回音（下一条不是 tool_result）；那种车不会自己回来读账本。
"""
import io
import json
import os
import time

D = os.path.join(os.path.expanduser("~"), ".qoder", "projects", "D--moodle")
LANES = [("89f2e2d6", u"哨兵称：断在半路（J 档）"),
         ("2d2d7428", u"哨兵称：交完活停着（交 1686 分/静 34 分）"),
         ("6a773af1", u"哨兵称：交完活停着（交 1542 分/静 38 分）"),
         ("45d25bfb", u"哨兵称：交完活停着（交 965 分/静 31 分）")]


def nodes(pre):
    """只收**有意义的对话节点**。

    19:33 踩到的坑：原版取 jsonl 末尾三条，取到的全是 active-leaf / runtime-config /
    file-history-snapshot 这类**脚手架节点**（无 content、无 role），看着像"每扇都在动"，
    其实是 1 分钟前工具一敲就刷出来的元数据。判末条形态必须只认 assistant/user。
    """
    for f in os.listdir(D):
        if f.startswith(pre) and f.endswith(".jsonl"):
            out = []
            for line in io.open(os.path.join(D, f), encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    n = json.loads(line)
                except Exception:
                    continue
                m = n.get("message")
                if isinstance(m, dict) and (m.get("role") or m.get("content")):
                    out.append(n)
            return out
    return []


def tail_form(n):
    m = n.get("message") or {}
    role = m.get("role") or n.get("type") or "?"
    c = m.get("content")
    if isinstance(c, str):
        kinds = u"text(%d 字)" % len(c)
    elif isinstance(c, list):
        ks = []
        for b in c:
            t = (b or {}).get("type")
            if t == "tool_use":
                ks.append(u"tool_use:%s" % (b or {}).get("name"))
            elif t == "tool_result":
                ks.append(u"tool_result")
            else:
                ks.append(t or "?")
        kinds = u"、".join(ks) or u"(空)"
    else:
        kinds = u"(无 content)"
    return role, kinds


for pre, claim in LANES:
    ns = nodes(pre)
    now = time.time()
    print(u"\n【%s】%s" % (pre, claim))
    print(u"  节点数 %d" % len(ns))
    if not ns:
        print(u"  jsonl 没找到")
        continue
    for n in ns[-3:]:
        role, kinds = tail_form(n)
        ts = n.get("timestamp") or n.get("time") or n.get("createdAt") or ""
        # timestamp 可能是 int（epoch 秒）或 ISO 字符串；两种都要能打出来，别在打印时炸。
        if isinstance(ts, (int, float)):
            # Qoder 的 jsonl 里 timestamp 是 **epoch 毫秒**（实测 1791286362177），
            # 不是秒。拿秒去 fromtimestamp 会直接 OverflowError（我 19:32 撞到过）。
            ms = float(ts)
            sec = ms / 1000.0 if ms > 1e11 else ms
            import datetime
            tstr = datetime.datetime.fromtimestamp(sec).strftime("%Y-%m-%d %H:%M:%S")
            age = u" %.0f 分前" % ((now - sec) / 60.0)
        else:
            ts = str(ts)
            tstr = ts[:19]
            age = ""
            if ts:
                try:
                    import datetime
                    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if t.tzinfo is None:
                        t = t.astimezone()
                    age = u" %.0f 分前" % ((now - t.timestamp()) / 60.0)
                except Exception:
                    pass
        print(u"  - %-10s %-28s %s%s" % (role, kinds, tstr, age))
    # 断在半路的判据：末条 assistant 里有 tool_use，而全局没有更晚的 tool_result
    last = ns[-1]
    role, kinds = tail_form(last)
    if u"tool_use" in kinds:
        has_reply = any(u"tool_result" in tail_form(n)[1] for n in ns[:-1][-5:])
        print(u"  ⇒ 末条是 tool_use；后五条里有 tool_result：%s" % has_reply)