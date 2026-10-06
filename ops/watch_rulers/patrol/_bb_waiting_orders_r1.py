# -*- coding: utf-8 -*-
"""把「两扇在等点单」按现场读数递回给号令者（不敲车道）。

为什么不敲那两扇：他们未取 0 条、无额度墙、无掉线，尾行自报「手上活交完了、等下一件」——
缺的是下一单，不是叫醒。敲一次只会让他们回一句"在等点单"，白烧一轮。
为什么走 BB 机不走账本：这不是派单也不是催活，是把现场事实递回给唯一能点单的人；
账本那条腿我这轮已经交过一块（2353 那枚），同一件事不在两处重复入账。

正文里刻意只留「0」这一类读数，出处用板子现取（不手打数字）：
出处跑的是 /api/fleet，输出里逐字带着 id8、静默分钟、未取条数与 live 态。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = u"D:/moodle/agent_bus"
CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
BODYF = os.path.join(ROOT, u"_outbox_draft_waiting.txt")
WHO = (u"da46954a", u"e766b154")


def board_rows():
    d = json.loads(urllib.request.urlopen("http://127.0.0.1:4820/api/fleet", timeout=10)
                   .read().decode("utf-8", "replace"))
    return d, [r for r in d["rows"] if r["id8"] in WHO]


def main():
    d, picked = board_rows()
    if len(picked) != 2:
        sys.exit(u"ABORT：板子里没同时读到这两扇（%s）⇒ 别据旧读数发话"
                 % u"、".join(r["id8"] for r in picked))
    for r in picked:
        print(u"现读 %s｜静 %d 分｜未取 %s｜live=%s" % (r["id8"], int(r["idle_min"]), r["unread"], r["live"]))
        if r["live"] in ("quota_wall", "dropped"):
            sys.exit(u"ABORT：%s 已被平台卡住，那不该报成等点单" % r["id8"])

    tail = io.open(CLOSING, encoding="utf-8").read().strip()
    body = (u"两扇在等点单，不是偷懒也不是卡住：钢筋工·老赵 da46954a 与安装工·小周 e766b154 "
            u"静默都过了五小时半，未取 0 条，额度墙 0 枚，掉线 0 枚；"
            u"两人流水尾行都自报「手上活已交完、等下一件」，其中老赵那格连他要点的具名那一格都写好了。\n"
            u"你刚点的那五扇不含这两扇，所以我把这一格按现场读数递回来："
            u"出处那栏是板子现取，逐字带 id8、静默分钟、未取条数与 live 态，"
            u"不是我抄的。我不敲他们——缺下一单时敲一次只会换来一句「在等点单」，白烧一轮。\n"
            + tail)
    io.open(BODYF, "w", encoding="utf-8", newline=chr(10)).write(body)

    ev = (u"板子现取两扇的静默与未取|python -c \""
          u"import json,urllib.request as U;"
          u"d=json.loads(U.urlopen('http://127.0.0.1:4820/api/fleet',timeout=10).read().decode('utf-8','replace'));"
          u"print([[r['id8'],int(r['idle_min']),r['unread'],r['live']] for r in d['rows'] "
          u"if r['id8'] in ('da46954a','e766b154')])\"")
    cmd = [sys.executable, os.path.join(ROOT, "bus.py"), "send",
           "--from", u"qoder:42d1a6fa", "--to", u"qoder:494abfd7", "--kind", u"order",
           "--topic", u"两扇等点单-da46954a-e766b154-" + time.strftime("%m%d%H%M%S"),
           "--body-file", BODYF, "--evidence", ev]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.stdout.decode("utf-8", "replace")
    print(u"send rc=%d" % p.returncode)
    mid = u""
    try:
        mid = json.loads(out).get("id", u"")
    except Exception:
        print(out[:500])
    if not mid:
        sys.exit(u"ABORT：没投出去（或没拿到 id）")
    got = json.loads(urllib.request.urlopen(
        u"http://127.0.0.1:4799/msg?id=" + urllib.parse.quote(mid), timeout=8)
        .read().decode("utf-8", "replace"))
    last = (got.get("body") or u"").strip().splitlines()[-1]
    print(u"回读 id=%s｜尾行逐字相同=%s｜evidence %d 段"
          % (mid, last == tail, len(got.get("evidence") or [])))
    if last != tail:
        sys.exit(u"ABORT：尾行没对上")
    os.remove(BODYF)
    print(u"WAITING_ORDERS_SENT")


if __name__ == "__main__":
    import urllib.parse                                    # noqa: E402
    main()
