# -*- coding: utf-8 -*-
"""数一扇窗在某时刻之后**往外发过哪些话**（send_message 的回执），用来分清「谁叫醒了谁」。

为什么要有它：归属要说得出口。19:34 那次我差点把号令者自己的叫醒记到我账上，
反过来也一样——我 01:25 递的是**清单**，之后车道复工到底是他点的头、还是车道自申报，
只能从他流水里的 `messageSent` 回执看，不能靠时间相邻就下结论。

只读；回执里的 sessionId 只印前 8 位。
"""
import io
import json
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def epoch_of(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    s = str(ts).strip()
    if s.endswith("Z"):
        import calendar
        for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return calendar.timegm(time.strptime(s[:-1], f))
            except Exception:
                continue
        return None
    return None


def main():
    pre = sys.argv[1] if len(sys.argv) > 1 else "494abfd7"
    since = sys.argv[2] if len(sys.argv) > 2 else "01:00:00"
    kb = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    t0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " " + since, "%Y-%m-%d %H:%M:%S"))
    cands = [p for p in os.listdir(PROJ) if p.startswith(pre) and p.endswith(".jsonl")]
    if not cands:
        print(u"REFUSE：找不到 %s 的流水" % pre)
        return 1
    path = os.path.join(PROJ, cands[0])
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - kb * 1024))
        if size > kb * 1024:
            f.readline()
        data = f.read()
    hits = []
    unparsed = 0
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            unparsed += 1
            continue
        e = epoch_of(r.get("timestamp"))
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m or not isinstance(m.get("content"), list):
            continue
        for x in m["content"]:
            if not isinstance(x, dict) or x.get("type") != "tool_result":
                continue
            cc = x.get("content")
            txt = cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False)
            sid = re.search(r'"sessionId"\s*:\s*"([0-9a-f]{8})', txt)
            if sid and u"messageSent" in txt:
                hits.append((e, sid.group(1)))
    print(u"%s｜尾部 %d KB 内 send_message 回执：共 %d 条，其中 %s 之后 %d 条%s" % (
        pre, kb, len(hits), since,
        len([h for h in hits if h[0] and h[0] >= t0]),
        u"（另有 %d 行解析不出，未计入）" % unparsed if unparsed else u""))
    tgt = {}
    for e, sid in hits:
        if e and e >= t0:
            tgt.setdefault(sid, []).append(e)
    for sid, es in sorted(tgt.items(), key=lambda kv: min(kv[1])):
        print(u"  %-9s %d 条｜最早 %s｜最晚 %s" % (
            sid, len(es),
            time.strftime("%H:%M:%S", time.localtime(min(es))),
            time.strftime("%H:%M:%S", time.localtime(max(es)))))
    if not tgt:
        print(u"  （那一刻之后没有对外发话的回执）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
