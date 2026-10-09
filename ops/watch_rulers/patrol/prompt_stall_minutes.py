"""Measure how many lane-minutes tonight were spent sitting on an un-answered tool prompt.

For each session: walk the transcript; an `assistant/tool_use` whose next records contain no `tool_result`
before the next user text is a prompt. We pair prompt -> the first later tool_result (if any) and sum the gap.
Prints per-lane episodes with both clocks (Z and +08) and the fleet total. Read-only.
"""
import glob
import io
import json
import os
import re
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ID8 = {"494abfd7": "号令者", "e4f3490f": "道0370", "4033270f": "道0383", "a68b0631": "rel",
       "3b65af59": "map", "904a042d": "Q", "8e5245f0": "道0369", "49fe0d7b": "N3",
       "9759f1ac": "N2", "1d64acf5": "S4", "be19052c": "道tokens", "bac10f40": "AI",
       "2d2d7428": "0388/0389"}
SINCE = "2026-09-28T11:00"     # 19:00+08 - tonight's shift window


def ep(ts):
    import calendar
    try:
        return calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def show(ts):
    e = ep(ts)
    return "%sZ / %s+08" % (ts[11:19], time.strftime("%H:%M:%S", time.gmtime((e or 0) + 8 * 3600))) if e else ts


def main():
    total_min = 0.0
    episodes = []
    now = time.time()
    for id8, nm in ID8.items():
        g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")), key=os.path.getmtime)
        if not g:
            continue
        seq = []
        for p in g:
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        d = json.loads(s)
                    except Exception:
                        continue
                    m = d.get("message") or {}
                    c = m.get("content")
                    ts = d.get("timestamp") or ""
                    if not isinstance(ts, str) or ts[:19] < SINCE:
                        continue
                    if not isinstance(c, list):
                        continue
                    for x in c:
                        if not isinstance(x, dict):
                            continue
                        if m.get("role") == "assistant" and x.get("type") == "tool_use":
                            inp = json.dumps(x.get("input"), ensure_ascii=False)
                            seq.append(("use", ts, (x.get("name"), inp)))
                        elif m.get("role") == "user" and x.get("type") == "tool_result":
                            seq.append(("result", ts, None))
        open_use = None
        for kind, ts, payload in seq:
            if kind == "use":
                if open_use is None:
                    open_use = (ts, payload)
            else:
                if open_use is not None:
                    gap = (ep(ts) - ep(open_use[0])) / 60.0
                    if gap >= 3:
                        episodes.append((nm, id8, open_use[0], ts, round(gap, 1), open_use[1], False))
                    open_use = None
        if open_use is not None:
            gap = (now - ep(open_use[0])) / 60.0
            if gap >= 3:
                episodes.append((nm, id8, open_use[0], "(至今无 tool_result)", round(gap, 1), open_use[1], True))
    # classify: a prompt is what a `rm`/write-permission gate looks like; a 3-minute gap can also be a
    # genuinely long-running command. Report both numbers instead of one inflated total.
    def is_gate(payload):
        inp = (payload[1] or "") if payload else ""
        return bool(re.search(r"\brm\s+-|\brmdir\b|\bRemove-Item\b", inp))
    gated = [e for e in episodes if is_gate(e[5])]
    other = [e for e in episodes if not is_gate(e[5])]
    print("shift window: since %s+08" % show(SINCE + "Z"))
    for nm, id8, a, b, gap, payload, pending in sorted(episodes, key=lambda x: -x[4]):
        tag = "删除/写权限形" if is_gate(payload) else "普通长命令形（无法与弹窗区分）"
        print("  %-10s %-9s %5.1f min  %s -> %s  tool=%s  %s%s"
              % (nm, id8, gap, show(a), (b[:19] if b.startswith("20") else b),
                 (payload[0] if payload else "?"), tag, "  [仍挂着]" if pending else ""))
    print("episodes=%d  其中删除/写权限形=%d 计 %.1f 分钟；普通长命令形=%d 计 %.1f 分钟（后者我不算进弹窗损失）"
          % (len(episodes), len(gated), sum(e[4] for e in gated), len(other), sum(e[4] for e in other)))
    io.open(os.path.dirname(os.path.abspath(__file__)) + r"\prompt_stall_rows.json", "w",
            encoding="utf-8").write(json.dumps(
                {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "gated": [{"lane": e[0], "id8": e[1], "from": e[2], "to": e[3], "minutes": e[4],
                             "still_pending": e[6]} for e in gated],
                 "other": [{"lane": e[0], "minutes": e[4]} for e in other]},
                ensure_ascii=False, indent=1))
    total_min = sum(e[4] for e in gated)
    print("CONFIRMED prompt-class lane-minutes = %.1f" % total_min)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
