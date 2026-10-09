# -*- coding: utf-8 -*-
u"""上游拥塞那一波的现读尺（第二版）：只认"此刻状态"与"近窗内的波次"。

第一版的两处错，都是我自己抓出来的，写在这里别再犯：
  一、`daily usage limit` 拿全文正则去搜 ⇒ 历史文件里**提过**这句话的会话全被算成"此刻撞限额"，
     连 9-27 号的老会话都进了分母（实测"只撞日限额 32 扇"是假的，真实只有 6efab655 那一扇的末条是它）。
     ⇒ 措辞只允许在**末条**上判状态；历史出现只作"曾撞过"的记录，不进状态。
  二、扫了整个 `~/.qoder/projects/D--moodle` 目录 ⇒ 波次被拉到 9-27（9544 分前的老会话），
     把"这一波"讲成了"历史上有过"。⇒ 只看近 LOOK_H 小时（默认 12），窗口外的另算一行"窗外还有 N 枚老会话"。

判据（现读，逐扇只取三样东西）：
  末条形态   = 该扇最后一条 assistant 节点的文字（tool_use 也算一次真产出）
  末条形态属于哪一档：busy（上游拥塞）／daily limit（日限额）／正常文字
  波次       = 窗口内含 busy 文字的节点，首/末时刻与次数
第二腿（号令者）：他此刻的末条形态 = 同一时刻另一条腿的读数，用来判"上游现在通不通"。

只读：0 次写、0 次发帖、0 次敲门。
跑法：PYTHONIOENCODING=utf-8 python _busy_wave_evidence_r2.py [--json] [--look-hours 12]
"""
import glob
import io
import json
import os
import re
import sys
import time

BASE = os.path.expanduser(r"~\.qoder\projects\D--moodle")
BUSY = re.compile(r"current model is busy|try again later|overloaded|rate.?limit", re.I)
LIMIT = re.compile(r"daily usage limit", re.I)
CMDR = u"494abfd7"


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
                parts.append(u"\x00TOOL\x00" + str(x.get("name")))
        return u" ".join(parts)
    return str(c or "")


def last_assistant(path):
    """末条 assistant 节点（倒着找一次即可，文件最大 50 MB 量级）。"""
    last = None
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if u'"assistant"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            last = d
    return last


def window_busy(path, since):
    hits = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if u'"assistant"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        t = parse_ts(d)
        if t < since:
            continue
        if BUSY.search(text_of(d) or ""):
            hits.append(t)
    return hits


def state_of(txt):
    if txt is None:
        return u"no_assistant_node"
    if LIMIT.search(txt):
        return u"daily_limit"
    if BUSY.search(txt):
        return u"upstream_busy"
    if u"\x00TOOL\x00" in txt:
        return u"working_on_tool"
    return u"normal_text"


def main():
    now = time.time()
    look = 12.0
    if u"--look-hours" in sys.argv:
        look = float(sys.argv[sys.argv.index(u"--look-hours") + 1])
    since = now - look * 3600.0

    per, outside = [], 0
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        id8 = os.path.basename(p)[:8]
        if len(id8) != 8:
            continue
        try:
            la = last_assistant(p)
            t = parse_ts(la) if la else 0.0
            idle = (now - t) / 60.0 if t else None
            if idle is not None and idle > look * 60:
                outside += 1
                continue
            st = state_of(text_of(la) if la else None)
            busy = window_busy(p, since)
            per.append({"id8": id8, "state": st,
                        "self_idle_min": round(idle, 1) if idle is not None else None,
                        "busy_n": len(busy),
                        "busy_first": min(busy) if busy else 0,
                        "busy_last": max(busy) if busy else 0,
                        "last_text": (text_of(la) or u"")[:70] if la else u""})
        except Exception:
            continue

    order = {u"upstream_busy": 0, u"daily_limit": 1, u"working_on_tool": 2, u"normal_text": 3,
             u"no_assistant_node": 4}
    per.sort(key=lambda r: (order.get(r["state"], 9), -(r["self_idle_min"] or 0)))
    tally = {}
    for r in per:
        tally[r["state"]] = tally.get(r["state"], 0) + 1

    cp = glob.glob(os.path.join(BASE, CMDR + "*.jsonl"))
    cmdr = None
    if cp:
        p = max(cp, key=os.path.getmtime)
        la = last_assistant(p)
        t = parse_ts(la) if la else 0.0
        cmdr = {"state": state_of(text_of(la) if la else None),
                "self_idle_min": round((now - t) / 60.0, 1) if t else None}

    waves = [r for r in per if r["busy_n"]]
    out = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "look_hours": look,
           "in_window": len(per), "outside_window": outside, "tally": tally,
           "wave_lanes": len(waves),
           "wave_first": min([r["busy_first"] for r in waves]) if waves else 0,
           "wave_last": max([r["busy_last"] for r in waves]) if waves else 0,
           "since_last_wave_min": round((now - max([r["busy_last"] for r in waves])) / 60.0) if waves else None,
           "cmdr": cmdr, "lanes": per}

    if u"--json" in sys.argv:
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + u"\n")
        return 0
    f = lambda t: time.strftime(u"%m-%d %H:%M", time.localtime(t)) if t else u"—"
    print(u"末条形态普查（现读 %s｜窗口 %.0f 小时｜窗内 %d 扇，窗外 %d 扇老会话不计入）"
          % (out["at"], look, out["in_window"], out["outside_window"]))
    print(u"分档：%s" % u"、".join(u"%s %d 扇" % (k, v) for k, v in sorted(tally.items(), key=lambda kv: order.get(kv[0], 9))))
    if waves:
        print(u"这一波：撞 busy 的 %d 扇｜%s ～ %s｜末条距今 %s 分"
              % (out["wave_lanes"], f(out["wave_first"]), f(out["wave_last"]), out["since_last_wave_min"]))
    if cmdr:
        verdict = (u"通（他在写/在跑工具）⇒ 曾经堵过 ≠ 现在还堵着，这时该叫醒的是'等模型没回来'那一档"
                   if cmdr["state"] in (u"normal_text", u"working_on_tool") else
                   u"他自己也停在 busy/日限额 ⇒ 上游或额度这一拍仍不可用，敲门是白敲")
        print(u"第二腿（号令者 %s）：末条=%s｜自产静 %s 分 ⇒ %s"
              % (CMDR, cmdr["state"], cmdr["self_idle_min"], verdict))
    print(u"逐扇：")
    for r in per:
        print(u"  %-9s %-15s 自产静%7s 分｜窗内 busy×%d｜%s"
              % (r["id8"], r["state"], r["self_idle_min"], r["busy_n"], r["last_text"][:44].replace("\n", " ")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
