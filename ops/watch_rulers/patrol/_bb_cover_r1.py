# -*- coding: utf-8 -*-
"""BB 机覆盖面：哪些窗在干活、哪些还没接进来、哪些是这一拍新冒出来的。

为什么要有它：推广这件事不能靠我记得去挨个看。新窗口随时会出现（10-03 05:07 就多了一扇
cmdrA 派出去修屏上机词的车道），名册必须从文件系统推、并且**每拍自己比出增量**；
比出来的新窗与没接进来的窗，直接把可粘贴的命令打出来，我下一步就只做「发」这一件事。

只读：读 jsonl 的 mtime 与中枢的 state.json（不 POST、不 read 别人的收件箱 ⇒ 不会把别人那格标成已送达）。
"""
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
STATE = os.path.join("D:/moodle/agent_bus", "state.json")
SEEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bb_cover_seen.json")
ALIVE_H = float(os.environ.get("BB_COVER_ALIVE_H", "6"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def roster():
    out = {}
    now = time.time()
    for n in os.listdir(PROJ):
        if not n.endswith(".jsonl") or len(n) < 40:
            continue
        p = os.path.join(PROJ, n)
        idle = (now - os.path.getmtime(p)) / 60.0
        if idle <= ALIVE_H * 60.0:
            out[n[:8]] = (n[:-6], round(idle, 1))
    return out


def hub_ids():
    try:
        st = json.load(io.open(STATE, encoding="utf-8"))
    except Exception as e:
        return None, u"读不到中枢 state：%s" % type(e).__name__
    ag = st.get("agents", {})
    return {k.split(":")[-1]: bool(v.get("verified")) for k, v in ag.items()}, None


def main():
    r = roster()
    ids, err = hub_ids()
    if ids is None:
        print(u"REFUSE：%s ⇒ 覆盖面判不了不算覆盖到" % err)
        return 3
    prev = set()
    if os.path.isfile(SEEN):
        try:
            prev = set(json.load(io.open(SEEN, encoding="utf-8")).get("seen", []))
        except Exception:
            prev = set()
    joined = sorted(k for k in r if ids.get(k))
    verified = sorted(k for k in r if ids.get(k) is True)
    unjoined = sorted(k for k in r if k not in ids)
    # 三态要说清：光有 id 而本人从没动过手（早期我批量代注的那几枚）＝还没真接进来，
    # 只报「在册 vs 不在册」会把这一格藏进分子里，看起来像覆盖了。
    listed = sorted(k for k in r if k in ids and ids.get(k) is not True)
    fresh = sorted(k for k in r if k not in prev)
    first_run = not prev
    print(u"干活 %d 扇｜自证 %d｜在册但没动过手 %d｜完全没接 %d｜这一拍新出现 %d 扇" % (
        len(r), len(verified), len(listed), len(unjoined), 0 if first_run else len(fresh)))
    if listed:
        print(u"在册没自证（我代注过、本人没 claim）：" + u"、".join(
            u"%s(静 %s 分)" % (k, r[k][1]) for k in listed))
    if first_run:
        print(u"（首跑：只建基线，不报「新窗」——否则把整张名册当新人报一遍，下一班分不清谁是真新）")
    elif fresh:
        print(u"新窗：" + u"、".join(u"%s(静 %s 分)" % (k, r[k][1]) for k in fresh))
    if unjoined:
        print(u"没接进来的：" + u"、".join(u"%s(静 %s 分)" % (k, r[k][1]) for k in unjoined))
        for k in unjoined:
            print(u"  邀请就发这一行：python D:/moodle/agent_bus/bus.py reg --id qoder:%s --name <花名>"
                  u"   （会话 id：%s）" % (k, r[k][0]))
    if not unjoined and not listed:
        print(u"覆盖面满：干活的窗全部自证在册")
    io.open(SEEN, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"seen": sorted(r.keys()), "at": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
