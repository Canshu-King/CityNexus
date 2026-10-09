# -*- coding: utf-8 -*-
"""倒读一条会话流水的末端，判三态：这一轮结束了没、最后一段有没有内容、有没有额度/排队字样。

为什么要看形而不是看平台的 runtimeState：10-01 实测 updatedAt 会滞后一小时以上，
而「这轮回复失败」多为终态 failed 空回合；send 回执只证明进了队，不证明被消费。
"""
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "494abfd7"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    f = [x for x in os.listdir(PROJ) if x.startswith(sid) and x.endswith(".jsonl")]
    if not f:
        print(u"找不到 %s" % sid)
        return 1
    p = os.path.join(PROJ, f[0])
    size = os.path.getsize(p)
    window = min(size, max(60000, n * 60000))
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        if size > window:
            fh.seek(size - window)
            fh.readline()                      # 丢掉可能被切断的首行（size<=window 时不 seek，首行是完整的）
            data = fh.read()
        else:
            data = fh.read()
    lines = [x for x in data.split(chr(10)) if x.strip()]
    recs = []
    for x in lines[-40:]:
        try:
            recs.append(json.loads(x))
        except Exception:
            continue
    print(u"%s｜%d B｜mtime %s" % (f[0][:13], size, time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p)))))
    for r in recs[-n:]:
        m = r.get("message") if isinstance(r.get("message"), dict) else {}
        c = (m or {}).get("content")
        kinds, txt = [], ""
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict):
                    kinds.append(x.get("type"))
                    if x.get("type") == "text" and not txt:
                        txt = (x.get("text") or "")
        elif isinstance(c, str):
            kinds.append("str")
            txt = c
        ts = r.get("timestamp")
        try:
            v = float(ts)
            e = v / 1000.0 if v > 1e11 else v
            t = time.strftime("%H:%M:%S", time.localtime(e))
        except Exception:
            t = str(ts)[:19]
        u = (m or {}).get("usage") if isinstance(m, dict) else None
        cred = u.get("credits") if isinstance(u, dict) else None
        print(u"  %-11s role=%-9s kinds=%-26s credits=%-6s %s" % (
            r.get("type"), (m or {}).get("role"), u",".join(str(k) for k in kinds)[:26],
            cred, txt.replace(chr(10), u" ⏎ ")[:95]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
