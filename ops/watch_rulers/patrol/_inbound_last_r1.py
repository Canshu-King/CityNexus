# -*- coding: utf-8 -*-
"""取一扇窗**收到的最后一记外来的话**（承载 = user 节点 或 attachment/queued_command），用来回读裁语原文。

为什么要有它：我递的是清单，之后那两扇复工了——但「复工」不等于「裁语到了」。
送达尺以前瞎过一次（只扫 user 节点，把 attachment/queued_command 读成没送到，43 分钟九次误判），
所以这里三类承载都扫，并且把发件时刻与收件时刻分开印。只读，不回话。
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


def carriers(path, kb):
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - kb * 1024))
        if size > kb * 1024:
            f.readline()
        data = f.read()
    outs = []
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        e = epoch_of(r.get("timestamp"))
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if m and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                outs.append((u"user 节点", e, c))
            elif isinstance(c, list):
                for x in c:
                    if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                        outs.append((u"user 节点", e, x["text"]))
        at = r.get("attachment") if isinstance(r.get("attachment"), dict) else None
        if at:
            kind = u"attachment/%s" % at.get("type")
            pr = at.get("prompt")
            if isinstance(pr, str):
                outs.append((kind, e, pr))
            elif isinstance(pr, list):
                for x in pr:
                    if isinstance(x, dict) and x.get("text"):
                        outs.append((kind, e, x["text"]))
    return outs


def main():
    pre = sys.argv[1] if len(sys.argv) > 1 else "2d2d7428"
    kb = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    cands = [p for p in os.listdir(PROJ) if p.startswith(pre) and p.endswith(".jsonl")]
    if not cands:
        print(u"REFUSE：找不到 %s 的流水" % pre)
        return 1
    path = os.path.join(PROJ, cands[0])
    outs = [x for x in carriers(path, kb) if x[0] == u"user 节点" or x[0].startswith(u"attachment/")]
    print(u"%s｜尾部 %d KB 内外来承载 %d 条｜取最后 %d 条：" % (pre, kb, len(outs), n))
    for kind, e, t in outs[-n:]:
        print(u"  [%s] 收件 %s｜%d 字" % (kind, time.strftime("%H:%M:%S", time.localtime(e)) if e else u"?", len(t)))
        print(u"  " + t.replace(chr(10), u" ⏎ ")[:900])
    if not outs:
        print(u"  （这一段里没有外来话——别把它读成「没送到」，也可能只是窗口不够大）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
