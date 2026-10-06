# -*- coding: utf-8 -*-
"""把 G 档在**现网**上跑一遍：真存在的那枚被硬闸拒着的块，必须真送出两条腿。

为什么要有这一支（而不是等下一拍哨兵）：旧代码在 17:21 那拍把这枚块记进了去重账
（`_sentinel_relay_gdone.json` 里那条 `1005|<块名>`），却什么也没投——正式账本回读 `band:G` 与
`bolt-words:1005:<块名>` 都是零。那种"看着报过、其实没人收到"的键是假账，得先证明它没兑现，
才准我把它撕掉重发；否则这枚块今天再也不会被送到车道。

只跑生产那份判定（S.door_backlog / S.bolt_alarms），不在这里另写第二条投递腿。
用法：PYTHONIOENCODING=utf-8 python _g_once_now_r1.py            # 真发
      PYTHONIOENCODING=utf-8 python _g_once_now_r1.py --dry      # 只看会发什么，不投
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _sentinel_relay_r1 as S

BUS = u"D:/moodle/agent_bus/bus.jsonl"


def bus_count(prefixes):
    n, rows = 0, []
    try:
        for l in io.open(BUS, encoding="utf-8"):
            if not l.strip():
                continue
            m = json.loads(l)
            t = str(m.get("topic", ""))
            if any(t.startswith(p) for p in prefixes):
                n += 1
                rows.append(t)
    except Exception as e:
        return None, [u"账本读不到:" + type(e).__name__]
    return n, rows


def main():
    dry = "--dry" in sys.argv
    g = S.load_gdone()
    print(u"去重账里 G 那几格（只数不带 |I| |K| 这类档标的）：%s" % (
        u"、".join(sorted(k for k in g if u"|" in k and k.split(u"|")[1] not in
                          (u"I", u"J", u"K", u"L", u"M", u"N", u"S", u"Q"))) or u"无"))
    nd, old, nrej, nbolt, note, bolts = S.door_backlog()
    print(u"分类尺那一拍：可插 %d｜门拒 %d｜闸拒 %d｜备注 %s｜具名 %s" % (nd, nrej, nbolt, note, bolts))
    if not bolts:
        print(u"现网没有闸拒的块 ⇒ 这一支不该发任何东西（负对照：空分母不当红）")
        return 0
    fire = []
    for nm, ag in bolts:
        key = time.strftime("%m%d") + u"|" + nm
        id8 = nm[:8]
        n_band = bus_count([u"band:G:%s:%s" % (time.strftime("%m%d"), id8)])[0]
        n_note = bus_count([u"bolt-words:%s:%s" % (time.strftime("%m%d"), nm)])[0]
        if n_band is None:
            print(u"  %s：账本读不到 ⇒ 不敢判定『已发过』，也不判定『没发过』——这一枚跳过，交人工" % nm)
            continue
        print(u"  %s（已等 %d 分）｜正式账本已有 band:G %d 条、bolt-words %d 条｜键在去重账里=%s" % (
            nm, int(ag), n_band, n_note, key in g))
        if n_band == 0 and n_note == 0 and key in g:
            g.pop(key)
            S.save_gdone(g)
            print(u"  ⇒ 那枚键是旧代码留下的假账（一条都没投出去）：撕掉键，重发" % ())
        if n_band == 0 and n_note == 0:
            fire.append((nm, ag))
    if not fire:
        print(u"结论：该发的都已经真发出去了 ⇒ 这一支不双发")
        return 0
    if dry:
        print(u"--dry：本应发 %d 枚（%s），没投" % (len(fire), u"、".join(x[0] for x in fire)))
        return 0
    reds = []
    fired = S.bolt_alarms(fire, g, reds)
    S.save_gdone(g)
    print(u"判定（红因）：%s" % (u"；".join(reds) or u"无"))
    print(u"真投出去的枚数：%d｜去重账现在：%s" % (fired, sorted(k for k in g if k in [time.strftime('%m%d') + '|' + x[0] for x in fire])))
    for nm, ag in fire:
        p = os.path.join(S.BOLT_WORDS_DIR, u"bolt_words_" + nm + u".txt")
        print(u"落盘 %s｜存在=%s" % (p, os.path.isfile(p)))
        if os.path.isfile(p):
            print(u"   头三行：%s" % u" ⏎ ".join(io.open(p, encoding="utf-8").read().splitlines()[:3]))
    return 0 if fired else 3


if __name__ == "__main__":
    sys.exit(main())
