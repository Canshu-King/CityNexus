# -*- coding: utf-8 -*-
"""车道活动与产出时间线（只读）：按小时数每条车道的『有正文产出』与『工具动作』。

为什么要两列（19:29 我自己被抓到的一次错读）：只数『有正文的 assistant 记录』会把
**闷头用工具的会话**读成没干活——号令者 B 那条 18:00 以后有 164 条 assistant 记录、
其中 0 条带正文（全是 tool_use/thinking），可他 18:46 与 19:12 各插了一块账本、落了四笔。
所以这张表同时给：T＝有正文产出条数，t＝工具动作（tool_use）条数，末次活动＝任一 assistant 记录。

口径：只数今天；`daily usage limit` 那条回话不算产出（它是闸，不是活）。
"""
import calendar
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道",
    "494abfd7": "号令者B", "6efab655": "CMDR-A",
}
FROM = int(sys.argv[1]) if len(sys.argv) > 1 else 12


def epoch(ts, fb):
    if isinstance(ts, (int, float)):
        return ts / 1000.0 if ts > 1e12 else float(ts)
    if isinstance(ts, str) and len(ts) > 18:
        try:
            return calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            return fb
    return fb


def main():
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 00:00", "%Y-%m-%d %H:%M"))
    hours = list(range(FROM, int((now - day0) / 3600) + 1))
    print("=== 车道活动/产出时间线 %s（T=有正文产出，t=工具动作；只数今天；额度回话不计）===" % time.strftime("%H:%M"))
    print("        " + "".join("%9d" % h for h in hours) + "    末次产出     末次活动")
    rows = []
    for sid8, nick in NICKS.items():
        c = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
        if not c:
            continue
        p = max([os.path.join(BASE, f) for f in c], key=os.path.getsize)
        tb = {}
        kb = {}
        last_txt = None
        last_any = None
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") != "assistant":
                continue
            e = epoch(o.get("timestamp"), os.path.getmtime(p))
            if e < day0:
                continue
            h = int((e - day0) // 3600)
            m = o.get("message") or {}
            cc = m.get("content") or []
            items = cc if isinstance(cc, list) else []
            ntool = sum(1 for x in items if isinstance(x, dict) and x.get("type") == "tool_use")
            txt = "".join(x.get("text", "") for x in items if isinstance(x, dict) and x.get("type") == "text")
            if ntool:
                kb[h] = kb.get(h, 0) + ntool
                last_any = max(last_any or e, e)
            if txt.strip() and "daily usage limit" not in txt:
                tb[h] = tb.get(h, 0) + 1
                last_txt = max(last_txt or e, e)
                if not ntool:
                    last_any = max(last_any or e, e)
        if last_any is None:
            continue
        rows.append((nick, tb, kb, last_txt, last_any))
    rows.sort(key=lambda r: -(r[4] or 0))
    for nick, tb, kb, lt, la in rows:
        cells = ""
        for h in hours:
            a = tb.get(h, 0)
            b = kb.get(h, 0)
            cells += "%9s" % ("%d+%d" % (a, b) if (a or b) else ".")
        print("  %-8s%s   %s   %s" % (nick, cells,
                                      time.strftime("今天 %H:%M:%S", time.localtime(lt)) if lt else "—          ",
                                      time.strftime("今天 %H:%M:%S", time.localtime(la))))
    T = sum(sum(b.values()) for _, b, _, _, _ in rows)
    t = sum(sum(b.values()) for _, _, b, _, _ in rows)
    print("合计：有正文产出 %d 条、工具动作 %d 条（%d 条会话，%02d:00 起算）。" % (T, t, len(rows), FROM))
    print("读法提醒：`+` 左边是正文、右边是工具动作。像号令者那种『整段都在跑脚本』的会话，"
          "正文列会是 0，但工具列不为 0——只看正文会把他读成没干活，这是我 19:29 自己差点写进报告里的错。")
    print("边界：只读 `projects/D--moodle/<id>.jsonl`。0 次写账本、0 次派单、0 次改别人的枝、0 次重启进程。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
