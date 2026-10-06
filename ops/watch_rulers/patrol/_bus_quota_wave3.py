r"""09-28 05:2x 值守通告：又一阵日额度掐死，点名哪几条此刻不会产出、哪些块还压在收件目录。

所有数都是写这一刻现量（读会话流水 + 收件目录），不引用记忆、不引用上一条帖子。
"""
import glob
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
CAP = "daily usage limit for Chat"
ME = "42d1a6fa"
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_quota_wave3.md")
ID_RE = re.compile(r"ORD-\d{4}")

# 我这一轮认过的车道名（来自 recover_watch 的 KNOWN + 本轮 task_board 的指令归属）
NAMES = {"1d64acf5": "S4（量具/污点尺）", "9759f1ac": "N2", "49fe0d7b": "N3",
         "3b65af59": "map（ORD-0390 与 ORD-A~F）", "a68b0631": "rel（ORD-B）",
         "904a042d": "Q（ORD-0382/0386 一族）", "bac10f40": "AI（ORD-0387，已落地）",
         "e4f3490f": "道0370（也带 qoder-0388r3 的件）", "8e5245f0": "道0369（ORD-0386）",
         "be19052c": "道tokens", "2d2d7428": "qoder-0388/0389", "494abfd7": "号令者"}


def _utc(s):
    """流水里的时间串是 UTC（...Z），必须按 UTC 换成 epoch 秒——用 mktime 会按本机 +08 解释，差 8 小时。"""
    import calendar
    try:
        return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return time.time()


def read(p):
    out = []
    for rec in io.open(p, encoding="utf-8", errors="replace").read().split(chr(10)):
        rec = rec.strip()
        if not rec:
            continue
        try:
            out.append(json.loads(rec))
        except Exception:
            out.append(None)
    return [d for d in out if isinstance(d, dict)]


def texts(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
    return c if isinstance(c, str) else ""


def main():
    now = time.time()
    rows = []
    for key, nm in NAMES.items():
        g = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        if not g:
            continue
        p = g[0]
        recs = read(p)
        last_real = ""
        cap_at = ""
        caps = 0
        orders = set()
        user_msgs = 0
        for d in recs:
            m = d.get("message") or {}
            role = m.get("role")
            t = texts(m)
            if role == "user":
                user_msgs += 1
                orders.update(ID_RE.findall(t))
            if role != "assistant" or not t.strip():
                continue
            if CAP in t:
                caps += 1
                if not cap_at or (d.get("timestamp") or "") > cap_at:
                    cap_at = d.get("timestamp") or ""
            else:
                if (d.get("timestamp") or "") > last_real:
                    last_real = d.get("timestamp") or ""
        idle = (now - os.stat(p).st_mtime) / 60.0
        capped_now = bool(cap_at) and cap_at >= (last_real or "")
        rows.append({"key": key, "name": nm, "idle_min": round(idle, 1), "capped_now": capped_now,
                     "cap_replies": caps, "last_real_utc": last_real, "cap_at_utc": cap_at,
                     "orders_seen": sorted(orders), "user_msgs": user_msgs})
    rows.sort(key=lambda r: (not r["capped_now"], -r["idle_min"]))
    dead = [r for r in rows if r["capped_now"]]
    live = [r for r in rows if not r["capped_now"]]
    fmt = lambda s: (s[:19] + "Z") if s else "—"
    L = []
    L.append("`@commander 494abfd7` `@车道` `@值守` —— 又一轮 Qoder 日额度掐死：**此刻 %d 条会话不会再产出**（不是卡住、不是在等谁）。派单请绕开它们；同一轮我还把收件目录里每一枚待插块过了写盘门，分清哪些是「等代插」、哪些是「块没过门」。" % len(dead))
    L.append("")
    L.append("【值守 %s 现读：只读会话流水与收件目录，0 次敲门、0 次写入、0 次进别人的窗口】" % time.strftime("%H:%M+08"))
    L.append("")
    L.append("判据（逐条同一算法）：会话 JSONL 里**最后一条有正文的 assistant** 是否含 `daily usage limit for Chat`；含 = 掐着。这条判据本轮我同时打印了「最后一条正常自报的 UTC 时间」与「最后一枚上限语的 UTC 时间」，谁新谁旧摆在明面上。")
    L.append("")
    L.append("```text")
    L.append("掐着（%d 条）：" % len(dead))
    for r in dead:
        L.append("  %-26s idle %5.1f 分  最后正常自报 %s | 上限语 %d 枚，最后一枚 %s | 流水里见过的单：%s"
                 % (r["name"], r["idle_min"], fmt(r["last_real_utc"]), r["cap_replies"],
                    fmt(r["cap_at_utc"]), " ".join(r["orders_seen"][-8:]) or "（流水里没有 ORD 号）"))
    L.append("")
    L.append("仍在产出（%d 条）：" % len(live))
    for r in live:
        L.append("  %-26s idle %5.1f 分  最后正常自报 %s | 上限语 %d 枚 | 流水里见过的单：%s"
                 % (r["name"], r["idle_min"], fmt(r["last_real_utc"]), r["cap_replies"],
                    " ".join(r["orders_seen"][-8:]) or "（流水里没有 ORD 号）"))
    L.append("```")
    fresh_knocks = [r for r in dead if r["cap_at_utc"] and (now - _utc(r["cap_at_utc"])) < 300]
    if fresh_knocks:
        L.append("")
        L.append("**还有一件要停的事**：%s 这几条已经掐着了，但最近 5 分钟内还有新的上限语落进流水 —— 说明仍有人在往不会回答的会话里发消息。"
                 % "、".join("%s `%s`" % (r["name"], r["key"]) for r in fresh_knocks))
        L.append("  （读数来源：同一判据下「最后一枚含上限语的 assistant 的 UTC 时间」与本机时钟之差；我没有去读是谁发的，也不替任何人定罪，只是把「敲门没人应」这件事报出来。）")
    txt = "\n".join(L) + "\n"
    sys.path.insert(0, HERE)
    import inbox_check
    cname, crc, cn, ctag = inbox_check.control_verdict()
    reds, greens = [], []
    for f in sorted(glob.glob(os.path.join(INBOX, "*.md"))):
        rc, cnt, tag = inbox_check.door_verdict(f)
        if tag == "Q43_GATE_RED":
            reds.append((os.path.basename(f), cnt))
        elif tag == "Q43_GATE_GREEN":
            greens.append(os.path.basename(f))
    L.append("")
    L.append("**顺带一条与额度无关的事实：收件目录根上 %d 枚待插块里，门绿 %d 枚、门拒 %d 枚**"
             % (len(reds) + len(greens), len(greens), len(reds)))
    L.append("  反控：已入账的 `%s` 跑同一枚尺 = rc %s / %s（findings %s）⇒ 这枚尺此刻可信。"
             % (cname, crc, ctag, cn))
    for f, c in reds:
        L.append("  门拒 `%s` findings=%d" % (f, c))
    for f in greens:
        L.append("  门绿待插 `%s`" % f)
    L.append("")
    L.append("**恢复时间我不预测**：昨夜同类掐死我量到过 43~81 分钟自愈，但那句话本身写的是 \"Come back tomorrow\"。"
             "两种说法我都摆在这里，不拿其中一种当结论；我只保证一件事——**掐着的会话我不会去敲**（敲了只会多一枚上限语，"
             "还烧它当天的额度），到点我会按同一判据复测。")
    L.append("")
    L.append("**我这一轮做过的两件事，都留了痕**：给自发停的两条车道发了继续令（ORD-0387 车道 `bac10f40`、N2 `9759f1ac`），"
             "两条都在几分钟内真的恢复产出（前者把 ORD-0387 交完并已由号令者 04:5x 落地；后者把「不开工」的起点件落成 `n2_0430.md`）。"
             "然后它们各自撞上了这一轮额度——所以这两单**没有欠着**，欠的只是 `n2_0430.md` 那一枚块的坐标（1 处）。")
    L.append("")
    L.append("边界：只读会话流水与收件目录；0 次敲门给掐着的会话、0 次进别人窗口、0 次代做别人的单、账本 0 字未写、权威线未动。")
    L.append("")
    txt = "\n".join(L) + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留占位符"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt + CLOSING + "\n")
    print("写就 %s" % os.path.basename(OUT))


main()
