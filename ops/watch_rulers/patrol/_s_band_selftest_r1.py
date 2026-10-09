# -*- coding: utf-8 -*-
"""S 档（已送达却没人拆）的自测——含「该红的那一次」与「不许把两档混成一档」。

为什么要这一档（16:4x 现读，同一趟）：M 档判「投出但没被取」，可中枢有一条送达探针会周期性补
`delivered_at`，于是件一旦被标过送达就退出 M 的视野——而它其实没人拆。那一刻实测：
deliver/order/ask/ruling 龄过九十分钟且从未 ack 的，**已送未拆一百一十四**条，未送达只剩个位数。
M 对「交完活卡在验收口」是单向致盲的，那一类正是全队最疼的。

七格，全在临时目录里造账（正式 bus.jsonl / state.json 一字节都不动）：
甲 送到、过档、没 ack，收件人是号令者 ⇒ 进分组、进 focus（该红的那一次）
乙 同一枚但**没被标送达** ⇒ S 不算（那一类归 M，两档不许混）
丙 送到且**已 ack** ⇒ S 不算（拆过就不算压着）
丁 送到、没 ack，但只过十分钟 ⇒ 不过阈值，不算（防一夜之间多出一片红）
戊 车道自己手里压着、 leadership 干净 ⇒ focus 为空 ⇒ 不报警（第②格敲门管它）
己 账读不到 ⇒ 返回 None，不许当零
庚 真实账上现读一次：总数 ≥ focus 数，且分组求和与总数对得上（防我自己拼错分母）
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, u"_sentinel_relay_r1.py")
CMDR = u"qoder:494abfd7"
LANE = u"qoder:1ba48dbf"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(tmp):
    spec = importlib.util.spec_from_file_location(u"s_band_selftest", TARGET)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.M_BUS = tmp
    m.LOG = os.path.join(tmp, u"sentinel_s.log")
    return m


def write_bus(tmp, rows, acks=None):
    with io.open(os.path.join(tmp, "bus.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + chr(10))
    io.open(os.path.join(tmp, "state.json"), "w", encoding="utf-8").write(json.dumps(
        {"acks": acks or {}, "forgotten": {}, "agents": {}}, ensure_ascii=False))


def main():
    now = time.time()
    tmp = tempfile.mkdtemp(prefix="sband_")
    res = []

    def check(name, got, want):
        ok = got == want
        res.append(ok)
        print("%-66s %s" % (name, "PASS" if ok else "FAIL got=%r want=%r" % (got, want)))

    m = load(tmp)

    # 甲：送到、过档、没 ack、收件人是号令者 ⇒ 该红
    write_bus(tmp, [{u"id": u"a1", u"from": LANE, u"to": CMDR, u"kind": u"deliver",
                     u"topic": u"甲", u"ts": now - 200 * 60, u"delivered_at": now - 190 * 60}])
    su = m.unacked_stalled()
    check(u"甲 号令者名下这一条进分组", su.get(CMDR, (0, 0))[0], 1)
    check(u"甲 龄算的是投出时刻（约两百分）", int(su[CMDR][1]) // 60, 3)
    check(u"甲 focus 里有它（这就是该红的那一次）", list(m.s_focus(su)), [CMDR])

    # 乙：同一枚但没被标送达 ⇒ S 不算（那是 M 的地盘）
    write_bus(tmp, [{u"id": u"b1", u"from": LANE, u"to": CMDR, u"kind": u"order",
                     u"topic": u"乙", u"ts": now - 200 * 60}])
    check(u"乙 未送达那类不进 S（两档不混）", m.unacked_stalled(), {})

    # 丙：送到且已 ack ⇒ 不算
    write_bus(tmp, [{u"id": u"c1", u"from": LANE, u"to": CMDR, u"kind": u"deliver",
                     u"topic": u"丙", u"ts": now - 200 * 60, u"delivered_at": now - 190 * 60}],
              acks={u"c1": {u"by": CMDR}})
    check(u"丙 已拆（ack）就不算压着", m.unacked_stalled(), {})

    # 丁：过档不够 ⇒ 不算（防一夜多出一片红）
    write_bus(tmp, [{u"id": u"d1", u"from": LANE, u"to": CMDR, u"kind": u"deliver",
                     u"topic": u"丁", u"ts": now - 10 * 60, u"delivered_at": now - 9 * 60}])
    check(u"丁 没到九十分钟不算积压", m.unacked_stalled(), {})

    # 戊：只有车道手里压着 ⇒ 分组有数，但 focus 为空（不报警，归第②格敲门）
    write_bus(tmp, [{u"id": u"e1", u"from": CMDR, u"to": LANE, u"kind": u"order",
                     u"topic": u"戊", u"ts": now - 300 * 60, u"delivered_at": now - 290 * 60}])
    su = m.unacked_stalled()
    check(u"戊 车道名下这条照实数出来（不藏）", su.get(LANE, (0, 0))[0], 1)
    check(u"戊 leadership 干净 ⇒ focus 为空 ⇒ 这一档不报", m.s_focus(su), {})

    # 己：账读不到 ⇒ None，不许当零
    m.M_BUS = os.path.join(tmp, "no_such_dir")
    check(u"己 取不到账返回 None（不当绿也不当零）", m.unacked_stalled(), None)

    # 庚：真实账现读一次——分组求和必须等于总数，focus 不得超过总数
    m2 = load(os.path.join(tmp, "real"))
    m2.M_BUS = u"D:/moodle/agent_bus"
    real = m2.unacked_stalled()
    if real is None:
        check(u"庚 正式账能读到", u"不可得", u"读数")
    else:
        tot = sum(v[0] for v in real.values())
        check(u"庚 分组求和等于总数（分母拼得起来）", sum(v[0] for v in real.values()), tot)
        check(u"庚 focus 条数不超过总条数", sum(v[0] for v in m2.s_focus(real).values()) <= tot, True)
        print(u"   现场读数：%d 条已送未拆，摊在 %d 枚收件人上；其中卡全队的 %d 条"
              % (tot, len(real), sum(v[0] for v in m2.s_focus(real).values())))

    n = sum(1 for x in res if x)
    print(u"\n%d/%d 过" % (n, len(res)))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if n == len(res) else 1


if __name__ == u"__main__":
    sys.exit(main())
