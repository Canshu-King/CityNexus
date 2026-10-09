# -*- coding: utf-8 -*-
"""BB 机采用度：谁真在用、用到什么程度，全部从中枢自己的账里算，不靠我记得。

为什么要有它：推广这件事的判据不是「我发过邀请」，而是「对面自己 claim 了身份、并且发过/读过东西」。
所以这里把三态分开数：在册（bulk 批量注册的也算）、自证（本人动过手）、真发过话。
只读 `state.json` 与 `bus.jsonl`，不 POST、不 ack、不推动游标 ⇒ 不会把「我量了一眼」变成「我读过他的收件箱」。
"""
import io
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = os.environ.get("BB_ROOT", "D:/moodle/agent_bus")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load():
    st = json.load(io.open(os.path.join(HUB, "state.json"), encoding="utf-8"))
    msgs = []
    bad = 0
    for line in io.open(os.path.join(HUB, "bus.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            msgs.append(json.loads(line))
        except ValueError:
            bad += 1
    return st, msgs, bad


st, msgs, bad = load()
ag = st.get("agents", {})
today = time.strftime("%Y-%m-%d")
# 身份两态按 state 里真实存在的旗子分组（bulk＝同批代注、verified＝本人动过手），
# 不去猜第三枚旗子的语义：先把组合数打出来，再列名字。
combo = Counter((bool(v.get("bulk")), bool(v.get("verified"))) for v in ag.values())
by_combo = {}
for k, v in ag.items():
    by_combo.setdefault((bool(v.get("bulk")), bool(v.get("verified"))), []).append(k)
self_serve = sorted(by_combo.get((False, True), []))
bulk = sorted(by_combo.get((True, False), []))
verified = sorted(k for k, v in ag.items() if v.get("verified"))
senders = sorted(set(m.get("from") for m in msgs if m.get("from")))
kinds = Counter(m.get("kind") for m in msgs)
mine = [m for m in msgs if time.strftime("%Y-%m-%d", time.localtime(m.get("ts", 0))) == today]

print(u"在册 %d 枚（自证且非批量 %d 枚、批量未自证 %d 枚、verified %d 枚）｜账本消息 %d 条（解析失败 %d 行）" % (
    len(ag), len(self_serve), len(bulk), len(verified), len(msgs), bad))
print(u"旗子组合（bulk, verified）分布：" + u"、".join(
    u"%s,%s %d 枚" % (k[0], k[1], v) for k, v in sorted(combo.items())))
print(u"自证在册：" + (u"、".join(self_serve) if self_serve else u"（无）"))
print(u"批量代注未自证：" + (u"、".join(bulk) if bulk else u"（无）"))
print(u"发过话的身份 %d 枚：" % len(senders) + u"、".join(senders))
kd = [u"%s %d" % (k, v) for k, v in sorted(kinds.items())]
print(u"kind 分布：" + u"、".join(kd))
print(u"今日（%s）新增 %d 条" % (today, len(mine)))
acks = st.get("acks", {})
print(u"已回执 %d 枚，回执人：" % len(acks) + u"、".join(sorted(set(v.get("by") for v in acks.values()))))
pend = [m for m in msgs if not m.get("delivered_at")]
print(u"未取走（delivered_at 空）%d 条，按收件人：" % len(pend)
      + u"、".join(u"%s %d" % (k, v) for k, v in sorted(Counter(m.get("to") for m in pend).items())))
