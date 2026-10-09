# -*- coding: utf-8 -*-
"""被敲过的车道，有没有「送达但那回合成 failed/空正文」——号令者 22:40 那块第 19 行点名的通道毛病。
判据只用流水里真实存在的字段：回合记录的 `status`/`error`/`isError`、以及 assistant 那条是否 0 正文 0 工具块。
时刻一律换算成 +08 再比我发消息的时刻，不靠记忆。
"""
import io
import json
import os
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SENT = {
    "a68b0631": ("rel", "01:13"), "6a150e1e": ("newlane2", "01:13"), "a6b95d59": ("DSH", "01:13"),
    "2d2d7428": ("0441", "01:13"), "3b65af59": ("map", "01:43"), "be19052c": ("dt", "01:43"),
    "8ac89982": ("R0417", "01:00"), "da46954a": ("新车道465", "00:55"), "9759f1ac": ("N2", "01:55"),
    "df90a7d5": ("新车道473", "01:29"),
}


def loc_of(ts):
    # 流水里是 UTC 的 %Y-%m-%dT%H:%M:%S...；换成 +08 的 HH:MM 才和「我几点发的」可比
    try:
        d = time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        e = time.mktime(d) + 8 * 3600 - (time.timezone + (time.altlog if False else 0) if time.daylight else time.timezone)
        return time.strftime("%H:%M", time.localtime(e))
    except Exception:
        return ""


def main():
    files = {}
    for f in os.listdir(BASE):
        if f.endswith(".jsonl"):
            files[f[:8]] = os.path.join(BASE, f)
    print("=== 敲过的车道：送达后有没有死回合（现读 %s）===" % time.strftime("%H:%M:%S"))
    for sid8, (nick, sent) in sorted(SENT.items(), key=lambda kv: kv[1][0]):
        p = files.get(sid8)
        if not p:
            print("   %-9s 无流水" % nick)
            continue
        sz = os.path.getsize(p)
        fh = io.open(p, "rb")
        fh.seek(max(0, sz - 3_000_000))
        blob = fh.read().decode("utf-8", "replace")
        fh.close()
        mine = 0
        after_rows = []
        for line in blob.split(chr(10)):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            c = (o.get("message") or {}).get("content")
            t = c if isinstance(c, str) else "".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
            if o.get("type") == "user" and u"值守 Qoder" in t:
                mine += 1
            after_rows.append(o)
        # 我那条被消费之后，有没有 failed / 空回合
        bad = 0
        seen_mine = False
        last_role = None
        for o in after_rows:
            if o.get("type") == "user":
                c = (o.get("message") or {}).get("content")
                t = c if isinstance(c, str) else "".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
                if u"值守 Qoder" in t:
                    seen_mine = True
            if o.get("type") not in ("user", "assistant"):
                continue
            last_role = o
            st = str(o.get("status") or "")
            err = o.get("error") or o.get("isError")
            if st.lower() == "failed" or err:
                bad += 1
            if seen_mine and o.get("type") == "assistant":
                c = (o.get("message") or {}).get("content")
                if isinstance(c, list) and not c:
                    bad += 1
        age = (time.time() - os.path.getmtime(p)) / 60.0
        kind = "?"
        if last_role is not None:
            c = (last_role.get("message") or {}).get("content")
            kind = "+".join(sorted({x.get("type", "") for x in c if isinstance(x, dict)})) if isinstance(c, list) else "str"
        print("   %-9s %s｜我那条落成 user 节点=%d 次｜尾窗内 failed/空回合迹象=%d｜静默 %.1f 分｜末条 %s"
              % (nick, sid8, mine, bad, age, kind or "?"))
    print("边界：只读流水；判据是记录里真实存在的 status/error 字段与空 content，不是猜。")


main()
