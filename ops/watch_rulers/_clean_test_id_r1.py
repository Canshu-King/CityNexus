# -*- coding: utf-8 -*-
u"""清掉我 22:01 干跑 join 时留下的测试身份 `codex:zzTESTONLY`（**带门**）。

**我做了什么**：为了验「接入件里那条 join 命令不是废文本」，我拿一枚明显是测试的 id
真跑了一次 `bus.py join --id codex:zzTESTONLY`。它 rc=0 并**真的注册进了名册**
（还带 `verified: True`、`self_seen: True`——它把自己标成已读全部）。
⇒ 这是我造成的污染，名册里多了一扇**不存在的车道**，而第⑦格与推广格都从名册取分母。

**污染面（22:01 逐项摸清，不是猜）**：
  · `state.json` 的 `agents` 里**一条** `codex:zzTESTONLY`；
  · `seen_topics` 819 项里含它的：**0**；
  · `forgotten` 2 项里含它的：**0**；
  · `bus.jsonl` 768 行里发件或收件是它的：**0 行**。
⇒ 只需删那**一个**键，不需要动账本、不需要发 forget、不碰任何真身份。

**同一扇门**（按纪律：破坏性动作与它的后果同一扇门）：
  ① 备份 state.json（带时刻）；② 打印**删前**的该项原文（留名册）；
  ③ 只删那一个键，回写；④ **回读**四项：agents 里没有了、seen_topics 仍 0、
     forgotten 仍 0、账本仍 0 行；真身份 bbfix1 仍在。
任何一步不符 ⇒ 立刻从备份还原并退出 1。

边界：不碰 bus.jsonl、不碰别人的 agents 项、不改 seen_topics/forgotten。
"""
import io
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = r"D:\moodle\agent_bus"
STATE = os.path.join(BUS, "state.json")
LEDGER = os.path.join(BUS, "bus.jsonl")
TARGET = "codex:zzTESTONLY"
KEEP = ("codex:bbfix1",)


def census(state):
    """返回 (agents 里命中数, seen_topics 命中数, forgotten 命中数, 账本行命中数)。"""
    ags = state.get("agents") or {}
    a = sum(1 for k in ags if TARGET in str(k))
    s = sum(1 for k in (state.get("seen_topics") or {}) if TARGET in str(k))
    f = sum(1 for k in (state.get("forgotten") or []) if TARGET in str(k))
    n = 0
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8", errors="replace"):
            if TARGET in line:
                n += 1
    return a, s, f, n


def main():
    if not os.path.exists(STATE):
        print(u"REFUSE：state.json 不在 %s，不动" % STATE)
        return 1
    raw = io.open(STATE, encoding="utf-8", newline="").read()
    st = json.loads(raw)
    before = census(st)
    print(u"删前四项（agents/seen_topics/forgotten/账本）：%s" % (before,))
    if before != (1, 0, 0, 0):
        print(u"REFUSE：污染面与预期 (1,0,0,0) 不符 ⇒ 不动（别盲删）")
        return 1

    bak = STATE + u".bak_testid_%s" % time.strftime("%H%M%S")
    shutil.copy2(STATE, bak)
    print(u"① 已备份：%s" % os.path.basename(bak))

    ags = st.get("agents") or {}
    hit = [k for k in ags if TARGET in str(k)]
    print(u"② 要删的那一项原文（留名册）：%s = %s"
          % (hit[0], json.dumps(ags[hit[0]], ensure_ascii=False)))

    del ags[hit[0]]
    st["agents"] = ags
    io.open(STATE, "w", encoding="utf-8", newline="").write(
        json.dumps(st, ensure_ascii=False, indent=2))
    print(u"③ 已回写 state.json")

    st2 = json.loads(io.open(STATE, encoding="utf-8").read())
    after = census(st2)
    keep_ok = all(k in (st2.get("agents") or {}) for k in KEEP)
    print(u"④ 回读四项：%s（应为 (0,0,0,0)）｜保留身份仍在：%s" % (after, keep_ok))
    if after != (0, 0, 0, 0) or not keep_ok:
        print(u"FAIL：回读不符 ⇒ 立刻从备份还原")
        shutil.copy2(bak, STATE)
        print(u"已还原到 %s" % os.path.basename(bak))
        return 1
    print(u"⇒ 清干净了。接入件里那条 join 我 22:01 实跑过、rc=0、返回结构完整（joined/inbox 都在），")
    print(u"  所以它**不是废文本**；但跑它会真注册身份 ⇒ 那一步仍要那扇窗自己执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())