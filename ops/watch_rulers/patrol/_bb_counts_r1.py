# -*- coding: utf-8 -*-
"""给 BB 机的一条 alarm 现取数字：谁被重启打断、中枢里谁压着未取的回复、名册此刻在写几扇。

为什么要有它：往 Agent Bus 里发 alarm 是要带 evidence 的（工具自己的规矩，我自己定的），
而"带 evidence"的正确做法不是抄一份数，而是**把取数命令本身交给中枢去跑**。所以这段脚本就是那条命令。
只读：读 jsonl 的 mtime、读中枢 HTTP、读名册，不发消息、不派单、不代插。
"""
import io
import json
import os
import sys
import time
import urllib.request

PROJ = os.path.expanduser(u"~/.qoder/projects/D--moodle")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CUT = os.environ.get("BB_CUT", "2026-10-03 04:35:05")
WATCHING = ("6a150e1e", "da46954a", "5a53846b", "8ac89982", "2d2d7428", "e766b154",
            "6a773af1", "0afdb49b", "1ba48dbf", "82f55d8a", "1d64acf5", "cff87c64", "6efab655", "364950b4")


def main():
    now = time.time()
    b = time.mktime(time.strptime(CUT, "%Y-%m-%d %H:%M:%S"))
    dark = []
    for id8 in WATCHING:
        c = [p for p in os.listdir(PROJ) if p.startswith(id8) and p.endswith(".jsonl")]
        if not c:
            continue
        mt = os.path.getmtime(os.path.join(PROJ, c[0]))
        if mt < b:
            dark.append((id8, int((now - mt) / 60)))
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    pend = json.loads(op.open("http://127.0.0.1:4799/pending?min=0", timeout=20).read().decode("utf-8"))
    untaken = [r for r in pend if r.get("state") == "queued" and r.get("kind") in ("ruling", "order", "ask", "deliver")]
    per_to = {}
    for r in untaken:
        per_to[r["to"]] = per_to.get(r["to"], 0) + 1
    print(u"开机 %s（现 %s）" % (time.strftime("%m-%d %H:%M:%S", time.localtime(b)), time.strftime("%H:%M:%S", time.localtime(now))))
    print(u"重启后没回来的车道：被切断 %d 扇" % len(dark))
    for id8, mins in sorted(dark, key=lambda x: -x[1]):
        print(u"  %s 静 %d 分" % (id8, mins))
    print(u"中枢里未被取走的回复/派单：共 %d 条" % len(untaken))
    for to, n in sorted(per_to.items()):
        print(u"  %s 压着 %d 条" % (to, n))
    kinds = {}
    for r in untaken:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(u"  按 kind：%s" % json.dumps(kinds, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
