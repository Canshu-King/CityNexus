# -*- coding: utf-8 -*-
"""23:00 到点判据（只读）：每条车在 09-29 晚 22:00 / 22:30 / 23:00 是否还在产出。

为什么单开这张（而不是复用 _night_verdict_r1.py）：那把尺的 `--since` 只接 `HH:MM`，
内部按**当天**日期解析。00:13 再跑，"当天"已经翻成 09-30 ⇒ 阈值成了未来的时刻 ⇒
所有人打印「末次产出 —、今日撞闸 0 次」，看着像全fleet 停摆，实际是尺自己失效。
本件把三个阈值写成**绝对**时刻，并且给每条车打印「尾部窗口最早读到几点」——
够不到 22:00 的车一律记 `NOT_COVERED`，绝不写成"没产出"。
"""
import io
import json
import os
import sys
import time
import datetime

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
T = {"22:00": None, "22:30": None, "23:00": None}
NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道",
    "e766b154": "新车道472", "494abfd7": "号令者B", "6efab655": "CMDR-A",
}


def epoch(hhmm, day="2026-09-29"):
    h, m = [int(x) for x in hhmm.split(":")]
    return time.mktime((int(day[0:4]), int(day[5:7]), int(day[8:10]), h, m, 0, 0, 0, -1))


def parse_ts(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            d = datetime.datetime.strptime(s, f)
            return (d - datetime.datetime(1970, 1, 1)).total_seconds()
        except Exception:
            pass
    return None


def hhmmss(e):
    return time.strftime("%H:%M:%S", time.localtime(e)) if e else "—"


def read_tail(path, win):
    sz = os.path.getsize(path)
    with open(path, "rb") as f:
        if sz > win:
            f.seek(sz - win)
            f.readline()
        return f.read().decode("utf-8", "replace")
    return ""


def scan(blob):
    """返回 (最早可读时刻, 末条记录时刻/种类, 末次产出时刻/种类, 末次额度回话时刻)."""
    rows = []
    for line in blob.split(chr(10)):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    earliest = None
    last_any = (None, "?")
    last_prod = (None, "?")
    last_cap = None
    for o in rows:
        e = parse_ts(o.get("timestamp"))
        if e is None:
            continue
        if earliest is None or e < earliest:
            earliest = e
        ty = o.get("type")
        if ty not in ("user", "assistant"):
            continue
        c = (o.get("message") or {}).get("content")
        kinds = set()
        txt = ""
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict):
                    kinds.add(x.get("type", ""))
                    if x.get("type") == "text":
                        txt += x.get("text", "")
        elif isinstance(c, str):
            kinds.add("text")
            txt = c
        k = "+".join(sorted(x for x in kinds if x)) or "?"
        last_any = (e, k)
        if "daily usage limit" in txt or "额度" in txt and "usage" in txt:
            last_cap = e if last_cap is None or e > last_cap else last_cap
            continue
        if ty == "assistant":
            if e > (last_prod[0] or 0):
                last_prod = (e, k)
    return earliest, last_any, last_prod, last_cap


def main():
    win = int(sys.argv[1]) * 1024 if len(sys.argv) > 1 else 4096
    for k in T:
        T[k] = epoch(k)
    now = time.time()
    print("=== 23:00 到点判据（现刻 %s｜尾部窗口 %d KiB/条）===" % (hhmmss(now), win))
    print("阈值（绝对）：" + "、".join("%s=%s" % (k, hhmmss(v)) for k, v in sorted(T.items())))
    files = {}
    for f in os.listdir(BASE):
        if f.endswith(".jsonl"):
            files[f[:8]] = os.path.join(BASE, f)
    rows = []
    for sid8, nick in sorted(NICKS.items(), key=lambda kv: kv[1]):
        p = files.get(sid8)
        if not p:
            rows.append((nick, sid8, None, (None, "?"), (None, "?"), None, None, "无流水文件"))
            continue
        blob = read_tail(p, win * 1024)
        earliest, last_any, last_prod, last_cap = scan(blob)
        covered = earliest is not None and earliest <= T["22:00"]
        marks = []
        for k in ("22:00", "22:30", "23:00"):
            if earliest is None:
                marks.append("?")
            elif not (earliest <= T[k]):
                marks.append("N/C")   # 窗口够不到，不判
            elif last_prod[0] is not None and last_prod[0] >= T[k]:
                marks.append("有")
            else:
                marks.append("无")
        note = "窗口够到 %s" % hhmmss(earliest) if earliest else "空"
        if not covered:
            note += "（够不到 22:00，不判）"
        rows.append((nick, sid8, earliest, last_any, last_prod, last_cap, marks, note))
    print()
    print("%-10s %-8s %-9s %-9s %-22s %-16s %s" % ("花名", "id", "末次产出", "末条", "22/22:30/23", "末次额度回话", "窗口"))
    for nick, sid8, e, la, lp, lc, marks, note in rows:
        print("%-10s %-8s %-9s %-9s %-22s %-16s %s" % (
            nick, sid8, hhmmss(lp[0]), (la[1][:8] if la[0] else "—"),
            "/".join(marks) if marks else "?", hhmmss(lc), note))
    # 门：09-29 12:00 → 09-30 00:00 的入账，按块名前缀分 cmdr / 非 cmdr
    d0, d1 = epoch("12:00"), epoch("00:00", "2026-09-30")
    pr = os.path.join(INBOX, "_processed")
    ins = []
    if os.path.isdir(pr):
        for f in os.listdir(pr):
            if ".inserted_" in f:
                m = os.path.getmtime(os.path.join(pr, f))
                if d0 <= m < d1:
                    src = f.split(".md.inserted_")[0] + ".md"
                    ins.append((m, src, not src.startswith("cmdr")))
    ins.sort()
    print()
    print("门：09-29 12:00→09-30 00:00 入账 %d 枚，其中非 cmdr 前缀 %d 枚" % (
        len(ins), sum(1 for x in ins if x[2])))
    for m, src, isnon in ins:
        if isnon:
            print("   非 cmdr 入账 %s  %s" % (hhmmss(m), src))
    print()
    print("边界：只读流水尾部与 mtime；产出＝assistant 那条记录含 text 或工具块；"
          "「N/C」是窗口够不到该时刻，不等于没产出。0 次写账本、0 次代插、0 次动权威线。")


main()
