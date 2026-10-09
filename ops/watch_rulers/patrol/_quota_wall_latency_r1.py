# -*- coding: utf-8 -*-
u"""额度墙的实际恢复延迟：不问"什么时候重置"（那没人告诉我），
而是从各扇自己的流水里量**上一回撞墙到下一回真产出**隔了多少分钟。

为什么要它（10-06 03:3x 现场）：号令者 494abfd7 与副号令者 6efab655 两腿同时被日限额挡住，
而"守到 11:00"这件事的验收口在他手上；敲他窗不会让额度早点回来（额度墙这一档本来就不该敲）。
所以能给的只有实测的等待时长与它的分母。

判据（都从流水节点推，不写字面）：
  撞墙那一刻 = 含额度词表的 assistant 节点时间戳；
  恢复那一刻 = 其后第一条**有实际内容**的 assistant 节点（文字或工具调用），外壳节点不算；
  两者之差 = 这一扇这一回的墙长。
只读：0 次写、0 次上总线、0 次敲门。

跑法：PYTHONIOENCODING=utf-8 python _quota_wall_latency_r1.py
"""
import glob
import io
import json
import os
import re
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
Q = re.compile(u"(daily usage limit|usage limit|rate.?limit|额度|限流|try again later)", re.I)
SYSNODE = re.compile(u"platform error|system error", re.I)
SHELL = (u"active-leaf", u"last-prompt", u"workspace-directories", u"runtime-config",
         u"attachment")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def iso(t):
    return time.strftime(u"%m-%d %H:%M", time.localtime(t)) if t else u"—"


def nodes(path):
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out.append(d)
    return out


def content(d):
    m = d.get("message") if isinstance(d.get("message"), dict) else d
    c = m.get("content")
    if isinstance(c, list):
        txt = u"".join(x.get("text", u"") for x in c if isinstance(x, dict) and x.get(u"type") == u"text")
        tools = [x.get("name") for x in c if isinstance(x, dict) and x.get(u"type") == u"tool_use"]
        return txt, tools
    return (str(c) if c else u""), []


def ts(d):
    v = d.get("timestamp")
    if isinstance(v, (int, float)):
        return float(v) / 1000.0 if v > 1e11 else float(v)
    if isinstance(v, str) and len(v) >= 17:
        try:
            return time.mktime(time.strptime(v[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
        except Exception:
            return 0.0
    return 0.0


def main():
    now = time.time()
    # 只看当班：整本流水能跑出三百多回墙（9 月底到现在的每一回），那种表没法用来等谁。
    LOOK_H = float(os.environ.get("QWL_LOOK_H", "12"))
    rows = []
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        if (now - os.path.getmtime(p)) / 3600.0 > LOOK_H:
            continue
        id8 = os.path.basename(p)[:8]
        ns = nodes(p)
        walls = []
        for i, d in enumerate(ns):
            if d.get("type") != "assistant":
                continue
            txt, tools = content(d)
            if not Q.search(txt or u"") and not SYSNODE.search(txt or u""):
                continue
            if txt and len(txt) > 400:
                continue          # 长文里提一句"额度"不算撞墙
            t0 = ts(d)
            if t0 and t0 < now - LOOK_H * 3600.0:
                continue          # 老墙不进这一档的分子
            back = 0.0
            for d2 in ns[i + 1:]:
                if d2.get("type") != "assistant":
                    continue
                t2 = ts(d2)
                if t2 <= t0:
                    continue
                txt2, tools2 = content(d2)
                if (txt2.strip() or tools2) and not Q.search(txt2 or u""):
                    back = t2
                    break
            walls.append((t0, back))
        if walls:
            rows.append((id8, walls))
    print(u"窗口：只看近 %.0f 小时有产出、且墙点落在窗口内的流水（QWL_LOOK_H 可改）" % LOOK_H)
    if not rows:
        print(u"近 12 小时有产出的流水里读不到额度形制 ⇒ 这一格写不可得，不许当绿")
        return 0
    ok, open_now = [], []
    print(u"逐扇逐回（撞墙时刻 → 恢复时刻｜墙长分钟）现读 %s" % time.strftime("%H:%M:%S", time.localtime(now)))
    for id8, walls in sorted(rows):
        for t0, back in walls:
            if back:
                ok.append(((back - t0) / 60.0, id8))
                print(u"  %s  %s → %s｜%5.0f 分" % (id8, iso(t0), iso(back), (back - t0) / 60.0))
            else:
                open_now.append((t0, id8))
                print(u"  %s  %s → 还没回来｜已挡 %5.0f 分" % (id8, iso(t0), (now - t0) / 60.0))
    print(u"⇒ 已恢复的 %d 回，墙长中位 %.0f 分、最短 %.0f 分、最长 %.0f 分"
          % (len(ok), sorted([x[0] for x in ok])[len(ok) // 2] if ok else 0,
             min([x[0] for x in ok]) if ok else 0, max([x[0] for x in ok]) if ok else 0)
          if ok else u"⇒ 还没有一扇恢复过，墙长不可得（别拿外推当数）")
    if open_now:
        print(u"还挡着的：%s" % u"、".join(u"%s（%s 起，已 %d 分）" % (i, iso(t), (now - t) / 60)
                                     for t, i in sorted(open_now)))
    print(u"边界：判据只看各扇自己的 assistant 节点；外壳节点（active-leaf 等）不算产出，"
          u"长文里提一句额度词不算撞墙。恢复时刻是「下一条真产出」，其中可能包含人敲过门——"
          u"所以这个数是墙长的**上界**，别当纯自恢复速率用。")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
