# -*- coding: utf-8 -*-
u"""alarm_backoff() 停投闸的合成自测：四档各验一次，外加一条"它不会悄悄放行"。

为什么要这条（10-03「每加一格要造一次该报的输入」＋10-04b「不咬人的锁是假锁」）：
这道闸的失败方向有两个，而且都不显眼——
  ① 该停没停 ⇒ 号令者收件框继续被同一件事灌（就是它要解决的那个病）；
  ② 不该停却停 ⇒ 告警从此哑掉，而"哑掉"看起来和"今天很清静"一模一样。
所以正反两向都要有反证，且**喂的是真函数**，不复制判据。

不碰生产：rows/acks 都从参数注入，全程不读 bus.jsonl、不起进程、不发任何消息。
跑法：PYTHONIOENCODING=utf-8 python _alarm_backoff_selftest_r1.py
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 只取闸门那一个函数进来，不 import 整份哨兵（那份在 import 时会读环境、装 HTTP 之类）。
import re  # noqa: E402
import io  # noqa: E402

src = io.open(os.path.join(HERE, "_sentinel_relay_r1.py"), encoding="utf-8").read()
m = re.search(r"(ALARM_BACKOFF_MIN = .*?\n)(def alarm_backoff\(.*?\n(?=\ndef |\nclass ))", src, re.S)
if not m:
    print(u"FAIL：哨兵里抠不出 alarm_backoff 那段 ⇒ 结构变了，同步改这里")
    raise SystemExit(1)

NS = {
    "os": os, "io": io, "json": __import__("json"), "time": __import__("time"),
    "M_BUS": u"D:/moodle/agent_bus", "is_own_alarm": lambda mm: True,   # 真函数会看 kind/topic，这层只控形状
    "say": lambda x: NS.setdefault("_log", []).append(x),
}
exec("import os, io, json, time\nM_BUS = u'D:/moodle/agent_bus'\n"
     "def is_own_alarm(m):\n    return True\n"
     "def say(x):\n    __import__('sys').stdout.write('')\n"
     + m.group(1) + m.group(2), NS)

backoff = NS["alarm_backoff"]
NOW = 1_000_000.0
TO = NS["ALARM_TO"]


def alarm(mid, band, to=TO, age=60.0, delivered=False, acked=False):
    return {"id": mid, "kind": "alarm", "to": to, "ts": NOW - age * 60,
            "topic": u"band:%s:1006:%s" % (band, mid.split("_")[-1]),
            "delivered_at": (NOW - age * 60 + 1) if delivered else None}


fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


# ① 正例：同档欠着 3 枚到龄未取 ⇒ 停投
rows = [alarm("m_1", "M"), alarm("m_2", "M"), alarm("m_3", "M")]
blocked, why = backoff("M", TO, rows=rows, acks={}, now=NOW)
ck(blocked, u"① 欠 3 枚未取却没停投 ⇒ 这道闸不咬人")
ck(u"欠 3 枚" in why, u"① 停投理由没带条数：%s" % why)

# ② 反例：欠着的那几枚被他取走了 ⇒ 不算欠，照投
acks = {"m_1": {"by": TO}, "m_2": {"by": TO}, "m_3": {"by": TO}}
blocked2, _ = backoff("M", TO, rows=rows, acks=acks, now=NOW)
ck(not blocked2, u"② 他已取走却仍停投 ⇒ 告警会从此哑掉，而哑掉看不出来")

# ③ 反例：取走（delivered_at）同样不算欠
blocked3, _ = backoff("M", TO, rows=[alarm("m_1", "M", delivered=True),
                                      alarm("m_2", "M", delivered=True),
                                      alarm("m_3", "M", delivered=True)],
                      acks={}, now=NOW)
ck(not blocked3, u"③ delivered_at 有值却仍停投 ⇒ 同上，误停")

# ④ 阈值下沿：只欠 2 枚（默认上限 3）⇒ 照投，别把闸关死
blocked4, _ = backoff("M", TO, rows=[alarm("m_1", "M"), alarm("m_2", "M")], acks={}, now=NOW)
ck(not blocked4, u"④ 欠 2 枚（未达上限 3）就停 ⇒ 阈值过紧，一夜之间可能把真告警全灭")

# ⑤ 别档不串：M 档欠着 3 枚，问 K 档 ⇒ K 档照投
blocked5, _ = backoff("K", TO, rows=rows, acks={}, now=NOW)
ck(not blocked5, u"⑤ M 档的欠账把 K 档也压住了 ⇒ 闸按档分得太粗")

# ⑥ 不到龄的不算：刚投出 5 分钟的欠着 3 枚，仍照投（M 档的未取阈值是 45 分）
rows6 = [alarm("m_1", "M", age=5.0), alarm("m_2", "M", age=5.0), alarm("m_3", "M", age=5.0)]
blocked6, _ = backoff("M", TO, rows=rows6, acks={}, now=NOW)
ck(not blocked6, u"⑥ 5 分钟前刚投的三枚被当成欠账 ⇒ 同一拍重投会被自己压掉，告警丢一整轮")

# ⑦ 读不到账时按"暂不投"（宁可少投也不制造第二个自激环）——传一个**迭代时就会抛**的账。
#   （我第一版用 dict 子类，那是我的错：`for m in rows` 遍历空 dict 根本不抛，异常路径压根没走到——
#     于是报了条"闸放行"的假红。触发异常要靠迭代本身失败，与 dict 是不是子类无关。）
class Boom(object):
    def __iter__(self):
        raise RuntimeError(u"账读不动了")

    def __len__(self):
        return 0


blocked7, why7 = backoff("M", TO, rows=Boom(), acks={}, now=NOW)
ck(blocked7, u"⑦ 闸自己读不动账时竟放行 ⇒ 会把告警继续投进一个可能已经堵死的通道")
ck(u"暂不投" in why7 or u"读不到" in why7, u"⑦ 理由没写明是闸读不到：%s" % why7)

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    print(u"⇒ 红 %d 条" % len(fails))
    raise SystemExit(1)
print(u"⇒ 绿：欠到龄未取 3 枚→停｜他已取走/已 delivered→不欠照投｜只欠 2 枚→照投（阈值不过紧）｜"
      u"别档不串｜5 分钟前刚投的不算欠｜闸读不到账时按暂不投（不制造第二个自激环）")
