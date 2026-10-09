# -*- coding: utf-8 -*-
"""查一句话是**从哪扇门**进到某条流水里的：记录类型、role、content 块形制、时刻、附近 120 字。

为什么要有它：02:32 号令者自己说收到「六条裁语诉求」，可我那记窗内 send 的标记在 user 节点里找不到，
总线两枚 comment id 在他流水里 0 次出现。成因不能靠猜——这一枚把承载它的那条记录原形打出来。
"""
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"


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


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "494abfd7"
    needle = sys.argv[2] if len(sys.argv) > 2 else u"停在『等你一句话』"
    tail_mb = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    f = [x for x in os.listdir(PROJ) if x.startswith(sid) and x.endswith(".jsonl")]
    if not f:
        print(u"找不到 %s" % sid)
        return 1
    p = os.path.join(PROJ, f[0])
    size = os.path.getsize(p)
    win = tail_mb * 1000000
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        if size > win:
            fh.seek(size - win)
            fh.readline()
        data = fh.read()
    print(u"%s｜总 %d B｜只读尾部 %d MB（%d B）" % (
        f[0][:13], size, tail_mb, len(data.encode("utf-8", "replace"))))
    hits = 0
    for line in data.split(chr(10)):
        if needle not in line or not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            print(u"  （命中但该行不是合法 JSON，跳过）")
            hits += 1
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else {}
        c = (m or {}).get("content")
        kinds = []
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict):
                    kinds.append(x.get("type"))
        e = epoch_of(r.get("timestamp"))
        print(u"  #%d 记录 type=%-10s role=%-9s 块=%-28s 时刻=%s" % (
            hits, str(r.get("type")), str((m or {}).get("role")),
            u",".join(str(k) for k in kinds)[:28] or u"（无块）",
            time.strftime("%H:%M:%S", time.localtime(e)) if e else str(r.get("timestamp"))[:19]))
        if isinstance(c, list):
            for x in c:
                if not isinstance(x, dict):
                    continue
                t = x.get("text") or x.get("content") or ""
                if isinstance(t, list):
                    t = u" ".join(str(y) for y in t)
                if needle in str(t):
                    i = str(t).find(needle)
                    print(u"      块 %s 内偏移 %d｜附近：%s" % (
                        x.get("type"), i, str(t)[max(0, i - 90):i + 90].replace(chr(10), u" ⏎ ")))
                    break
        hits += 1
        if hits >= 6:
            break
    if not hits:
        print(u"  尾部 %d MB 内没有这句话 ⇒ 承载它的那条记录更老（或它根本不在这一侧）" % tail_mb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
