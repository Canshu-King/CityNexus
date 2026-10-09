# -*- coding: utf-8 -*-
u"""上游模型拥塞那一波的现读尺：从各扇自己的流水里量"busy"出现与停止的时刻。

为什么要有它（10-06 16:2x 现场）：十四扇车道同时静默 11.5 小时，末条几乎全是同一句
`The current model is busy`。这件事有两个方向的可能，而判据完全不同：
  · 上游还在堵 ⇒ 敲门无用（值守再敲一百次也是同一句），该做的是具名报出去；
  · 上游已通、只是那一轮等模型没回来 ⇒ 这才是该叫醒的形态。
肉眼分不出来——板子把它们判成"收班"（不在在册行里），只有回到各自流水才看得见。
所以这把尺必须能：① 逐扇给出首/末条 busy 时刻与次数；② 给出"此刻上游是否通"的第二个证据；
③ 两者分开写，不许用"曾经堵过"冒充"现在还堵着"。

第二个证据取自**号令者自己的流水**（他此刻是否还在等模型／还在写）——它是同一时刻另一条腿的读数，
比"我猜上游通了"强。取不到就写不可得。

只读：0 次写、0 次发帖、0 次敲门。跑法：
  PYTHONIOENCODING=utf-8 python _busy_wave_evidence_r1.py          （人看的表）
  PYTHONIOENCODING=utf-8 python _busy_wave_evidence_r1.py --json   （给总线 evidence 用）
"""
import glob
import io
import json
import os
import re
import sys
import time

BASE = os.path.expanduser(r"~\.qoder\projects\D--moodle")
BUSY = re.compile(r"current model is busy|please try again later|overloaded", re.I)
LIMIT = re.compile(r"daily usage limit", re.I)
CMDR = u"494abfd7"          # 号令者：拿他当"此刻上游通不通"的另一条腿


def parse_ts(d):
    t = d.get("timestamp")
    if isinstance(t, (int, float)):
        return float(t) / 1000.0 if t > 1e11 else float(t)
    if isinstance(t, str) and len(t) >= 19:
        try:
            return time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
        except ValueError:
            return 0.0
    return 0.0


def nodes(path):
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def text_of(d):
    m = d.get("message") if isinstance(d.get("message"), dict) else {}
    c = m.get("content")
    if isinstance(c, list):
        parts = []
        for x in c:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "text":
                parts.append(x.get("text", ""))
            elif x.get("type") == "tool_use":
                parts.append(u"[tool %s]" % x.get("name"))
        return u" ".join(parts)
    return str(c or "")


def scan(path):
    busy, lim = [], False
    last_self = 0.0
    for d in nodes(path):
        if d.get("type") != "assistant":
            continue
        t = parse_ts(d)
        txt = text_of(d)
        if t:
            last_self = max(last_self, t)
        if BUSY.search(txt or ""):
            busy.append(t)
        if LIMIT.search(txt or ""):
            lim = True
    return busy, lim, last_self


def main():
    now = time.time()
    per = []
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        id8 = os.path.basename(p)[:8]
        if len(id8) != 8:
            continue
        try:
            busy, lim, last_self = scan(p)
        except Exception:
            continue
        if not busy and not lim:
            continue
        per.append({
            "id8": id8,
            "busy_n": len(busy),
            "busy_first": min(busy) if busy else 0,
            "busy_last": max(busy) if busy else 0,
            "quota_wall": bool(lim),
            "self_idle_min": round((now - last_self) / 60.0, 1) if last_self else None,
        })
    per.sort(key=lambda r: -(r["busy_last"] or 0))

    # 第二个证据：号令者此刻在干什么（同一时刻的另一条腿）
    cmdr = None
    cp = glob.glob(os.path.join(BASE, CMDR + "*.jsonl"))
    if cp:
        busy_c, lim_c, last_c = scan(max(cp, key=os.path.getmtime))
        cmdr = {"busy_n": len(busy_c), "quota_wall": bool(lim_c),
                "self_idle_min": round((now - last_c) / 60.0, 1) if last_c else None,
                "file_idle_min": round((now - os.path.getmtime(max(cp, key=os.path.getmtime))) / 60.0, 1)}
    waves = [r for r in per if r["busy_n"]]
    out = {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "busy_lanes": len(waves),
        "quota_only_lanes": sum(1 for r in per if r["quota_wall"] and not r["busy_n"]),
        "wave_first": min([r["busy_first"] for r in waves]) if waves else 0,
        "wave_last": max([r["busy_last"] for r in waves]) if waves else 0,
        "since_last_wave_min": round((now - max([r["busy_last"] for r in waves])) / 60.0) if waves else None,
        "cmdr": cmdr,
        "lanes": per,
    }
    if u"--json" in sys.argv:
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + u"\n")
        return 0
    f = lambda t: time.strftime(u"%m-%d %H:%M", time.localtime(t)) if t else u"—"
    print(u"上游拥塞那一波（现读 %s）" % out["at"])
    print(u"撞过 busy 的车道 %d 扇｜只撞日限额的 %d 扇｜波次 %s ～ %s｜末条距今 %s 分"
          % (out["busy_lanes"], out["quota_only_lanes"], f(out["wave_first"]),
             f(out["wave_last"]), out["since_last_wave_min"]))
    if cmdr:
        print(u"同一时刻另一条腿（号令者 %s）：自产静 %s 分｜busy %d 次｜撞日限额 %s"
              % (CMDR, cmdr["self_idle_min"], cmdr["busy_n"], cmdr["quota_wall"]))
        print(u"  ⇒ %s" % (u"他此刻还在产出/等模型 ⇒ 上游已通，'曾经堵过'不能当成'现在还堵着'"
                           if (cmdr["self_idle_min"] is not None and cmdr["self_idle_min"] < 25
                               and not cmdr["quota_wall"])
                           else u"他此刻也没产出 ⇒ 上游可能仍堵，这时敲门是白敲"))
    print(u"逐扇：")
    for r in per:
        print(u"  %s busy×%d（%s～%s）自产静 %s 分%s"
              % (r["id8"], r["busy_n"], f(r["busy_first"]), f(r["busy_last"]),
                 r["self_idle_min"], u"｜日限额" if r["quota_wall"] else u""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
