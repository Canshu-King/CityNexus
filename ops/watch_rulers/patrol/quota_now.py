# -*- coding: utf-8 -*-
"""quota_now.py — 一条命令回答：此刻几条掐着、几条在产出、谁刚回来。

判据（与发总线那两帖同一条）：会话 JSONL 里**最后一条有正文的 assistant** 含 `daily usage limit for Chat` = 掐着。
同时打印每条的「最后一条正常自报的 UTC」与「最后一枚上限语的 UTC」，新旧摆在明面上，不靠 mtime 猜。

只读，且**只读每条会话文件的末尾 TAIL_BYTES**（号令者那条已 194 MB，整读一轮要几十秒还吃盘）。
掐着/可动这个判定只看最后一条有正文的 assistant，它一定落在末尾里；代价是「最后正常自报」可能被截成「末尾里最晚的一条」，
所以那一列我标 `~`，意思是 tail 下界，不是精确时间。
"""
import calendar
import glob
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
CAP = "daily usage limit for Chat"
ME = "42d1a6fa"
TAIL_BYTES = 2 * 1024 * 1024
NAMES = {"1d64acf5": "S4 量具/污点尺", "9759f1ac": "N2", "49fe0d7b": "N3", "3b65af59": "map",
         "a68b0631": "rel", "904a042d": "Q", "bac10f40": "AI", "e4f3490f": "道0370",
         "8e5245f0": "道0369", "be19052c": "道tokens", "2d2d7428": "0388/0389",
         "494abfd7": "号令者", "4033270f": "道0383(新开)"}


def epoch_utc(s):
    try:
        return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def scan(p, tail=TAIL_BYTES):
    """返回 (最后一条正常自报的 UTC, 最后一枚上限语的 UTC, 上限语枚数[tail 内])。"""
    size = os.path.getsize(p)
    with io.open(p, "rb") as f:
        if tail and size > tail:
            f.seek(size - tail)
        raw = f.read().decode("utf-8", "replace")
    last_real = cap_at = ""
    caps = 0
    for rec in raw.split(chr(10)):
        rec = rec.strip()
        if not rec:
            continue
        try:
            d = json.loads(rec)
        except Exception:
            continue                      # 截断的第一行本来就解析不了，跳过（tail 下界的代价）
        m = d.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
             if isinstance(c, list) else (c or ""))
        if not t.strip():
            continue
        ts = d.get("timestamp") or ""
        if CAP in t:
            caps += 1
            if ts > cap_at:
                cap_at = ts
        elif ts > last_real:
            last_real = ts
    return last_real, cap_at, caps


def selftest():
    """同一枚小文件：tail 读与整读的判定必须一致，否则这仪表不能用。"""
    bad = 0
    for key in ("be19052c", "49fe0d7b", "9759f1ac"):
        g = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        if not g:
            print("  %-9s 没有文件，跳过" % key)
            continue
        p = g[0]
        full = scan(p, tail=None)
        tl = scan(p, tail=256 * 1024)
        same_cap = (full[1] >= full[0]) == (tl[1] >= tl[0])
        print("  %-9s size=%9d B  整读(最后正常=%s 最后上限=%s) tail256K(最后正常=%s 最后上限=%s) 掐着判定一致=%s"
              % (key, os.path.getsize(p), full[0][:19] or "—", full[1][:19] or "—",
                 tl[0][:19] or "—", tl[1][:19] or "—", same_cap))
        bad += 0 if same_cap else 1
    print("selftest %s" % ("PASS" if bad == 0 else "FAIL"))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    now = time.time()
    rows = []
    for key, nm in NAMES.items():
        g = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        if not g:
            continue
        p = g[0]
        last_real, cap_at, caps = scan(p)
        idle = (now - os.stat(p).st_mtime) / 60.0
        capped = bool(cap_at) and cap_at >= (last_real or "")
        # 「回来」= 掐着过，但最后一条正常自报比最后一枚上限语新
        back = bool(cap_at) and bool(last_real) and last_real > cap_at
        rows.append((nm, key, idle, capped, back, caps, last_real, cap_at))
    dead = [r for r in rows if r[3]]
    live = [r for r in rows if not r[3]]
    print("[%s] 掐着 %d / 共 %d 条会话" % (time.strftime("%H:%M:%S"), len(dead), len(rows)))
    for nm, key, idle, capped, back, caps, lr, ca in sorted(dead, key=lambda r: -r[2]):
        print("  掐着 %-12s %-9s idle %5.1f 分  上限语 %2d 枚  最后正常自报 %s  最后一枚上限语 %s"
              % (nm, key, idle, caps, lr[:19] or "—", ca[:19]))
    for nm, key, idle, capped, back, caps, lr, ca in sorted(live, key=lambda r: r[2]):
        tag = "（曾经掐过，已回来）" if back else ""
        print("  可动 %-12s %-9s idle %5.1f 分  上限语历史 %2d 枚  最后正常自报 %s %s"
              % (nm, key, idle, caps, lr[:19] or "—", tag))
    return 0


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(0 if sys_exit is None else sys_exit)
