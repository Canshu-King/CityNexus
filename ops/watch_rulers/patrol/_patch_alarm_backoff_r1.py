# -*- coding: utf-8 -*-
u"""给 alarm 腿装一道"该收件人这条通道已经堵着，就别再倒第二遍"的闸。

成因（10-06 16:3x 现读 bus.jsonl）：投给号令者的 alarm 共 108 枚，其中 31 枚他从没取走；
按（档:主体）归堆，`band:1005` 同一件被投了 39 次、`band:1004` 37 次、`band:1006` 25 次。
去重键带日期（"%m%d|" 开头），所以每天第一拍都把昨夜没取走的整批重投一遍——
**"我提醒你"这件事本身成了他收件框里最大的一坨**。号令者那 77 条未取里 43 条是我发的、
31 条是 alarm。哨兵已经会把"自回声"排除出分母（`is_own_alarm`），那一半做对了；
缺的就是"跨天不再重投"。

这道闸做什么、明确不做什么：
  做   —— 投某档 alarm 前，先数收件人名下「我自己投出、同档、超阈值、至今没被取走」的枚数；
          ≥ BLOCK_MIN 就不再投，把这件事写进哨兵日志（事实仍然落在板子 M 档那一格与 _M_ECHO 里）。
  不做 —— 不改任何分母与计数口径（那几格照旧算、照旧落日志）；不动 ack 语义（归号令者裁）；
          不碰"他从没取过"这件事的判断权（堵着就是堵着，我只停止加码，不替他裁）。
为什么这条动作归值守：停的是**我自己**那条腿，且目标是"别把告警事实塞进一个不读的收件框"，
事实改由板子那一格承载——那是主人与包工头真会打开的界面。

跑法：python _patch_alarm_backoff_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_sentinel_relay_r1.py")

# ① 闸门本体：放在 try_alarm 之前
FN = u'''ALARM_BACKOFF_MIN = int(os.environ.get("ALARM_BACKOFF_MIN", "3"))
ALARM_TO = u"qoder:494abfd7"          # 与 hub_alarm 的 --to 写死值同源，改一处记得改两处
_M_BLOCK = {"n": 0, "band": u"", "to": u""}


def alarm_backoff(band, to_addr, rows=None, acks=None, now=None, unacked_min=45.0):
    u"""这一档该不该停投：收件人名下同档的"我自己投出且没被取走"已达上限 ⇒ 停。

    返回 (bool, 说明)。只认「自己投的、同档、超过未取阈值、至今没被取走」这四样同时成立的那批；
    别人投的、他已取的、别的档，都不计入——否则这一格会变成"他收件框里有多少条"那种无边界的账。
    """
    try:
        now = now if now is not None else time.time()
        if rows is None:
            rows = []
            with io.open(os.path.join(M_BUS, "bus.jsonl"), encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        if acks is None:
            acks = json.load(io.open(os.path.join(M_BUS, "state.json"),
                                    encoding="utf-8")).get("acks", {})
        band_s = u"band:%s" % band
        n = 0
        oldest = 0.0
        for m in rows:
            if str(m.get("kind")) != u"alarm":
                continue
            if str(m.get("to")) != to_addr:
                continue
            if not is_own_alarm(m):
                continue
            if not str(m.get("topic") or u"").startswith(band_s + u":"):
                continue
            if m.get("delivered_at") or acks.get(m.get("id")):
                continue
            age = (now - float(m.get("ts", now))) / 60.0
            if age < unacked_min:
                continue
            n += 1
            oldest = max(oldest, age)
        _M_BLOCK["n"], _M_BLOCK["band"], _M_BLOCK["to"] = n, band_s, to_addr
        if n >= ALARM_BACKOFF_MIN:
            return True, (u"%s 收件人 %s 名下已欠 %d 枚未取（最老 %d 分）⇒ 本拍停投；"
                          u"事实见板子 M 档那一格与日志，不往不读的收件框里加码"
                          % (band_s, to_addr, n, int(oldest)))
        return False, u""
    except Exception as e:
        # 闸门自己读不动账时**不许当成"可以投"**：宁可少投也不制造第二个自激环；
        # 也不抛出去掀掉这一轮判定。
        say(u"停投闸读不到账（%s: %s）⇒ 这一拍按'暂不投'处理" % (type(e).__name__, str(e)[:90]))
        return True, u"闸读不到账，本拍暂不投"


'''

ANCHOR = u"def try_alarm(band, id8, msg):"

# ③ 闸门插进 try_alarm 内部（单一入口，8 个档位一律过它）。
# 锚只取两行 `try:` + `return hub_alarm(...)`——那两行在全文唯一，比整段 docstring 更耐改。
OLD3 = u'''    try:
        return hub_alarm(band, id8, msg)'''
NEW3 = u'''    # alarm 只有一个收件人：hub_alarm 的 send 命令把 --to 写死成 qoder:494abfd7，
    # 所以"这条通道堵没堵"就等于"号令者名下我投的同档 alarm 欠没欠"。
    # 达上限就停投（事实落日志与板子那一格），别往不读的收件框里加第二遍——
    # 16:3x 现读：号令者名下 108 枚 alarm、31 枚他没取走，同一件被跨天重投了 25–39 次。
    blocked, why = alarm_backoff(band, ALARM_TO)
    if blocked:
        say(u"停投：%s" % why)
        return ("blocked", u"band:%s" % band)
    try:
        return hub_alarm(band, id8, msg)'''


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"def alarm_backoff" in t:
        print(u"已装过（文件里有 alarm_backoff），不重复写")
        return 0
    n1 = t.count(ANCHOR)
    n2 = t.count(OLD3)
    if n1 != 1 or n2 != 1:
        print(u"REFUSE：插入点命中 %d 次、try_alarm 体锚命中 %d 次，都要 1 次 ⇒ 未写盘" % (n1, n2))
        return 1
    new = t.replace(ANCHOR, FN + ANCHOR).replace(OLD3, NEW3)
    ast.parse(new)
    if u"--check" in sys.argv:
        print(u"--check：两处锚各命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print(u"已写 _sentinel_relay_r1.py：加 alarm_backoff() 停投闸（阈值 ALARM_BACKOFF_MIN，默认 3）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
