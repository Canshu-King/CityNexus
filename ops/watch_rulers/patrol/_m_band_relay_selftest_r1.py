# -*- coding: utf-8 -*-
"""M 档新口径（号令者两扇互递的复述件不进分母）的自测——含「该红的那一次」。

副号令者·夜班 10-05 具名要求：一、被写盘门拒的车道块要算 deliver 类堆积；二、号令者之间互递的
复述件不计进「未取」的分子。第二条我装了；第一条我先去量它现在住在哪（F 档 door_backlog 已在数
门拒/闸拒枚数且属 actionable），同一件事在两档各报一次＝双报警，所以那条交回裁，不擅自造重复锁。

四格合成读数（临时目录里的假 bus.jsonl 与假 state.json，正式账一个字节都不动）：
甲 车道→号令者 的 order 压过档 ⇒ **照旧进分母**（这是负对照：装了新口径不许把尺弄瞎）
乙 号令者→号令者 的 note/order 压过档 ⇒ 不进分母，但数落在 _M_RELAY 里、日志具名留一行
丙 同类但没到档 ⇒ 两头都不算（证明我挡的是"复述件"，不是"新信"）
丁 旧写法在同一份合成账上必须把乙那几枚算进分母 ⇒ 这一格就是新锁"该红的那一次"，
   旧尺不红，说明这条口径其实没在管事（假锁）
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
CMDR1 = u"qoder:494abfd7"
CMDR2 = u"qoder:6efab655"
LANE = u"qoder:1ba48dbf"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def mkmodule(tmp):
    spec = importlib.util.spec_from_file_location(u"m_band_selftest", TARGET)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.M_BUS = tmp
    m.LOG = os.path.join(tmp, u"sentinel_test.log")       # 桩日志，不混进值守日志
    return m


def main():
    tmp = tempfile.mkdtemp(prefix="mband_")
    now = time.time()
    rows = [
        {u"id": u"a1", u"from": LANE, u"to": CMDR1, u"kind": u"order",
         u"topic": u"ORD-自测甲", u"ts": now - 200 * 60},
        {u"id": u"b1", u"from": CMDR1, u"to": CMDR2, u"kind": u"order",
         u"topic": u"复述乙·派单副本", u"ts": now - 300 * 60},
        {u"id": u"b2", u"from": CMDR2, u"to": CMDR1, u"kind": u"deliver",
         u"topic": u"复述乙·交付副本", u"ts": now - 150 * 60},
        {u"id": u"c1", u"from": CMDR1, u"to": CMDR2, u"kind": u"order",
         u"topic": u"复述丙·没到档", u"ts": now - 5 * 60},
    ]
    with io.open(os.path.join(tmp, u"bus.jsonl"), u"w", encoding=u"utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + chr(10))
    io.open(os.path.join(tmp, u"state.json"), u"w", encoding=u"utf-8").write(
        json.dumps({u"acks": {}, u"forgotten": {}, u"agents": {}}, ensure_ascii=False))

    m = mkmodule(tmp)
    n, oldest, who = m.bus_unread_alarms()
    log = io.open(m.LOG, encoding=u"utf-8").read() if os.path.exists(m.LOG) else u""
    res = []

    def check(name, got, want):
        ok = got == want
        res.append(ok)
        print("%-64s %s" % (name, "PASS" if ok else "FAIL got=%r want=%r" % (got, want)))

    check(u"甲 车道→号令者 过档那枚照旧进分母（尺没被弄瞎）", n, 1)
    check(u"甲 分母里只有那一枚收件人", who, [CMDR1])
    check(u"甲 最老龄取的是甲那枚（不是复述件的 300 分）", oldest, 200)
    check(u"乙 复述件单独数出来（不藏）", m._M_RELAY["n"], 2)
    check(u"乙 复述件最老龄", m._M_RELAY["oldest"], 300)
    check(u"乙 日志具名留了一行「复述件」", u"复述件 2 条不计入分母" in log, True)
    check(u"丙 没到档的复述件两头都不算", m._M_RELAY["oldest"] >= 90 and n == 1, True)

    # 丁：旧写法在同一份账上会把乙那两枚也算进分母 ⇒ 证明这条口径真的在管事
    thr = {u"alarm": m.M_UNREAD_MIN, u"deliver": m.M_UNREAD_KIND_MIN, u"order": m.M_UNREAD_KIND_MIN}
    pend_old = [(x, (now - float(x.get("ts", now))) / 60.0) for x in rows
                if x.get("kind") in thr and not x.get("delivered_at")]
    old_aged = [p for p in pend_old if p[1] >= thr[p[0].get("kind")]]
    check(u"丁 旧写法在同一份账上数到三枚（新口径确实咬到了）", len(old_aged), 3)
    check(u"丁 新写法比旧写法少的正是那两枚复述件", len(old_aged) - n, 2)

    n_ok = sum(1 for x in res if x)
    print(u"\n%d/%d 过" % (n_ok, len(res)))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if n_ok == len(res) else 1


if __name__ == u"__main__":
    sys.exit(main())
