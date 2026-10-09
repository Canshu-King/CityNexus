# -*- coding: utf-8 -*-
u"""待看档判据自测：拿真档（绿）＋造的红档，验 judge() 该绿绿、该红红。

为什么要有：这套判据是**新加的报警**，不咬人的报警等于没有报警
（同 feedback-new-arm-must-discriminate）。这里四只反控缺一不可：
  ① 真档（19:08 那份，实读结论是「全队都在动」）⇒ 必须绿
  ② 造一档只把结论行改成别的 ⇒ 必须红
  ③ 造一档结论还绿、但②该敲写成 3 扇 ⇒ 必须红（防"只看结论行"）
  ④ 造一档结论还绿、但⑥栈不是"栈完整" ⇒ 必须红（防值守栈塌了没人看见）
  ⑤ 空文本 ⇒ 必须红（解析不到判据不许当绿）
再验 note_eyes 的去重：绿⇒绿不再写；红⇒绿 写一条"已回绿"。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _patrol_loop_r1 as P

REAL = os.path.join(HERE, "rounds", "round_20261006_4676_001.txt")

fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


def mk(text):
    return u"\n".join(text)


# ① 真档
if not os.path.exists(REAL):
    print(u"REFUSE：真档不在 %s" % REAL)
    raise SystemExit(1)
real = io.open(REAL, encoding="utf-8", errors="replace").read()
red, why, concl, cells = P.judge(real)
ck(not red, u"① 真档被判红：%s" % (why,))
ck(concl.startswith(u"结论"), u"① 真档没读到结论行")
print(u"① 真档 ⇒ 红=%s 结论=%s" % (red, concl))

# ② 只把结论改成别的
lines = real.splitlines()
lines2 = [l if not l.startswith(u"结论") else u"结论：有扇该敲" for l in lines]
r2, w2, c2, _ = P.judge(mk(lines2))
ck(r2, u"② 结论行变了却没判红")
print(u"② 改结论 ⇒ 红=%s 理由=%s" % (r2, w2))

# ③ 结论还绿、该敲非零
lines3 = []
for l in lines:
    if l.startswith(u"②"):
        l = u"② 该敲（静默过档且信压着没取）3 扇：aaa、bbb、ccc"
    lines3.append(l)
r3, w3, c3, _ = P.judge(mk(lines3))
ck(c3.startswith(u"结论"), u"③ 造档把结论行也弄丢了")
ck(r3, u"③ 该敲 3 扇却判绿（只看了结论行）")
print(u"③ 该敲 3 扇 ⇒ 红=%s 理由=%s" % (r3, w3[:1]))

# ④ 结论还绿、栈塌
lines4 = [u"⑥ 值守栈：⇒ 缺 2 条腿，需要起复" if l.startswith(u"⑥") else l for l in lines]
r4, w4, c4, _ = P.judge(mk(lines4))
ck(r4, u"④ 栈塌了却判绿")
print(u"④ 栈塌 ⇒ 红=%s 理由=%s" % (r4, w4[:1]))

# ⑤ 空文本
r5, w5, c5, _ = P.judge(u"")
ck(r5, u"⑤ 空文本判绿（解析不到判据当绿）")
print(u"⑤ 空文本 ⇒ 红=%s 理由=%s" % (r5, w5))

# note_eyes 去重：先红后绿各写一条，连着绿不再写
NEEDS = os.path.join(HERE, "rounds", "_selftest_needs.log")
if os.path.exists(NEEDS):
    os.remove(NEEDS)
ST = os.path.join(HERE, "rounds", "_selftest_state.json")
if os.path.exists(ST):
    os.remove(ST)
old_needs, old_state = P.NEEDS, os.path.join(HERE, "rounds", "_needs_state.json")
P.NEEDS = NEEDS
try:
    a1 = P.note_eyes(True, [u"自测红"], u"", u"t.txt")
    a2 = P.note_eyes(False, [], u"结论：全队都在动", u"t.txt")
    a3 = P.note_eyes(False, [], u"结论：全队都在动", u"t.txt")
    ck(a1 and a2, u"note_eyes：红/转绿两条都该写")
    ck(not a3, u"note_eyes：连着绿又写了一条")
    body = io.open(NEEDS, encoding="utf-8").read().splitlines()
    # 红记录是**两行**（时间行 + 档名行），绿记录是一行 ⇒ 3 行是"一条红＋一次回绿"的正确形状。
    # 去重的判据是**条数**：连着绿第二次不写（a3 False 已验），不是行数。
    ck(len(body) == 3, u"note_eyes：待看档行数 %d，应为 3（红两行＋回绿一行）" % len(body))
    ck(sum(1 for l in body if u"档=" in l) == 1,
       u"note_eyes：红记录的档名行不止一条")
    print(u"⑥ 去重 ⇒ 写了 %d 行：%s" % (len(body), u" / ".join(body)))
finally:
    P.NEEDS = old_needs
    for p in (NEEDS, ST):
        if os.path.exists(p):
            os.remove(p)

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    raise SystemExit(1)
print(u"⇒ 自测绿：真档绿｜结论变红｜该敲非零红｜栈塌红｜空文本红｜待看档去重")