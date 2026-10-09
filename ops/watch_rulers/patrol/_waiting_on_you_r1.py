# -*- coding: utf-8 -*-
"""「等你点头的清单」：把静默且非额度的车，各自最后一句正文逐字摘出来。
只读。每条给：花名/会话 id/静默多久/末条是正文还是工具块/它自己的原话（截 420 字）。
不代裁、不催车道——它们停的地方是别人的手上，推它们没用。
"""
import io
import json
import os
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
WIN = 400 * 1024
NICKS = {
    "904a042d": "Q", "4033270f": "0383", "3b65af59": "map", "49fe0d7b": "N3",
    "be19052c": "dt", "8e5245f0": "道0369", "6efab655": "CMDR-A",
}
CAP = "daily usage limit"


def last_assistant_text(path):
    sz = os.path.getsize(path)
    fh = io.open(path, "rb")
    if sz > WIN:
        fh.seek(sz - WIN)
        fh.readline()
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    best = ("", "")
    nrec = 0
    kinds = "?"
    for line in blob.split(chr(10)):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant"):
            continue
        nrec += 1
        c = (o.get("message") or {}).get("content")
        ks = "+".join(sorted({x.get("type", "") for x in c if isinstance(x, dict)})) if isinstance(c, list) else "str"
        if ks:
            kinds = ks
        if o.get("type") == "assistant" and isinstance(c, list):
            t = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            if t.strip():
                best = (o.get("timestamp", ""), t.strip())
    return best, kinds, nrec


def main():
    now = time.time()
    files = {}
    for f in os.listdir(BASE):
        if f.endswith(".jsonl"):
            files[f[:8]] = os.path.join(BASE, f)
    out = []
    for sid8, nick in NICKS.items():
        p = files.get(sid8)
        if not p:
            continue
        (ts, text), kinds, nrec = last_assistant_text(p)
        age = (now - os.path.getmtime(p)) / 60.0
        capped = CAP in text
        out.append((nick, sid8, age, kinds, ts, text, capped, nrec))
    print("=== 静默且非额度的车，各自在等什么（现读 %s）===" % time.strftime("%H:%M:%S"))
    for nick, sid8, age, kinds, ts, text, capped, nrec in sorted(out, key=lambda x: -x[2]):
        flag = u"闸上" if capped else u"非闸"
        print("【%s %s】静默 %.1f 分｜%s｜尾窗内角色记录 %d 条｜末正文时刻 %s" % (nick, sid8, age, flag, nrec, ts[:19]))
        if text:
            body = text[-420:] if len(text) > 420 else text
            for l in body.split(chr(10)):
                if l.strip():
                    print("    > " + l.strip()[:150])
        print()
    print("边界：只读流水尾部；0 写账本、0 派单、0 敲闸上的车、0 改任何人的文件。截的是各自最后一条正文的尾巴，不是我转述。")


main()
