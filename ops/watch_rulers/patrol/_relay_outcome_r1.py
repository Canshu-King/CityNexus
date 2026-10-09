# -*- coding: utf-8 -*-
"""传话之后看结果：目标会话（通常是号令者）在某一刻之后，有没有逐条点名裁定。

为什么要它：把清单送到只是半件事， objective 要的是「车队因此继续干」。
以前我只能靠肉眼翻他的流水，眼睛一扫就会把**旧的派单行**当成新裁定（这一版第一跑就撞上了：
六个 id 各命中几十行，全是 09-30/10-01 的老派单）。所以这里强制带时间下界，只算那一刻之后的新行。
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
    target = sys.argv[1] if len(sys.argv) > 1 else "494abfd7"
    since_hhmm = sys.argv[2] if len(sys.argv) > 2 else None
    ids = sys.argv[3:] if len(sys.argv) > 3 else []
    f = [x for x in os.listdir(PROJ) if x.startswith(target) and x.endswith(".jsonl")]
    if not f:
        print(u"REFUSE：找不到 %s 的流水" % target)
        return 1
    p = os.path.join(PROJ, f[0])
    since = None
    if since_hhmm:
        since = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " " + since_hhmm, "%Y-%m-%d %H:%M:%S"))
        if since > time.time() + 3600:
            since -= 86400
    size = os.path.getsize(p)
    win = min(size, int(os.environ.get("RO_MB", "60")) * 1000000)
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        if size > win:
            fh.seek(size - win)
            fh.readline()
        data = fh.read()
    rows = []
    for line in data.split(chr(10)):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        e = epoch_of(r.get("timestamp"))
        if since is not None and (e is None or e < since):
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for x in c:
            if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                rows.append((e, x["text"]))
    print(u"%s｜只算 %s 之后的助手正文，共 %d 段（读尾部 %d MB，不数 tool_result）" % (
        target, since_hhmm + u" 起" if since_hhmm else u"（无下界）", len(rows), win // 1000000))
    if not rows:
        print(u"⇒ 那一刻之后他没有新的助手正文落流水（可能那一轮还没结束）——这不等于没裁，只说明还没可证")
        return 0
    blob = u"\n".join(t for _e, t in rows)
    if ids:
        for i in ids:
            sent = [s for s in re.split(u"(?<=[。；;\n])", blob) if i in s]
            last = sent[-1].strip().replace(chr(10), u" ⏎ ") if sent else u""
            if len(last) > 170:
                last = last[:170] + u"…"
            print(u"  %-9s 新段落里点名 %d 次%s" % (i, len(sent), (u"｜最新：" + last) if sent else u"（未点名）"))
    else:
        print(u"  最近三段（各取 140 字）：")
        for e, t in rows[-3:]:
            print(u"   %s｜%s" % (time.strftime("%H:%M:%S", time.localtime(e)),
                                  t.strip().replace(chr(10), u" ⏎ ")[:140]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
