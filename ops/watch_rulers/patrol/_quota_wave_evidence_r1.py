# -*- coding: utf-8 -*-
"""额度潮证据件（只读）：今天所有『撞额度』事件，分「已恢复产出」与「删失（至今无后续）」。

为什么要有这件，以及它自己救过我一次：窗口回的 `Come back tomorrow…` 是**说法**不是读数。
19:16 我据『15 个恢复样本、中位 20.7 分』贴总线说『到 21:00 前多数能复工』——那句话的分母
**只含恢复了的样本**，把至今没回来的那些（删失）丢在外面，是条件分布当边际分布用。
19:20 我补了删失计数才发现：今天 36 枚撞闸里只有 15 枚有后续产出，rel 那枚 15:35 撞的
到 19:19 仍无后续（3 小时 44 分）。所以这张尺必须同时报两侧。

口径：cap＝一条 assistant 记录正文含 `daily usage limit`；work＝其后最早一条有正文的
assistant 记录；恢复＝两者时间差；删失＝该 cap 之后再没有任何 work 记录。只数当天。
"""
import calendar
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QUOTA_WAVE_0929.md")
NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道",
    "e766b154": "新车道472",
    "494abfd7": "号令者B", "6efab655": "号令者A",
}


def epoch(ts, fb):
    if isinstance(ts, (int, float)):
        return ts / 1000.0 if ts > 1e12 else float(ts)
    if isinstance(ts, str) and len(ts) > 18:
        try:
            return calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            return fb
    return fb


def hms(e):
    return time.strftime("%m-%d %H:%M:%S", time.localtime(e))


def scan(sid8):
    c = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
    if not c:
        return None, []
    p = max([os.path.join(BASE, f) for f in c], key=os.path.getsize)
    seq = []
    for line in io.open(p, encoding="utf-8", errors="replace"):
        if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") != "assistant":
            continue
        e = epoch(o.get("timestamp"), os.path.getmtime(p))
        m = o.get("message") or {}
        txt = "".join(x.get("text", "") for x in (m.get("content") or []) if isinstance(x, dict))
        if "daily usage limit" in txt:
            seq.append((e, "cap"))
        elif txt.strip():
            seq.append((e, "work"))
    seq.sort(key=lambda x: x[0])
    return p, seq


def main():
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 00:00", "%Y-%m-%d %H:%M"))
    allcap = []
    for sid8, nick in NICKS.items():
        p, seq = scan(sid8)
        if not p:
            continue
        for i, (e, k) in enumerate(seq):
            if k != "cap" or e < day0:
                continue
            nxt = [f for f, k2 in seq[i + 1:] if k2 == "work" and f > e]
            allcap.append((nick, sid8, e, nxt[0] if nxt else None))
    recovered = [x for x in allcap if x[3] is not None]
    censored = [x for x in allcap if x[3] is None]
    waits = sorted((x[3] - x[2]) / 60.0 for x in recovered)
    bands = [(day0, day0 + 15 * 3600, u"00:00–15:00"),
             (day0 + 15 * 3600, day0 + 18.5 * 3600, u"15:00–18:30"),
             (day0 + 18.5 * 3600, now + 1, u"18:30–现在")]

    b = []
    b.append(u"# 额度潮证据件 · 生成于 %s（只读；0 次写账本 / 0 次派单 / 0 次重启进程）" % hms(now))
    b.append(u"")
    b.append(u"## 1. 总量与删失（这两个数必须一起看）")
    episodes = 0
    for sid8, nick in NICKS.items():
        _p, seq = scan(sid8)
        prev = None
        for e, k in seq:
            if k == "cap" and e >= day0:
                if prev is None or (e - prev) / 60.0 > 5:
                    episodes += 1
            prev = e if k == "cap" else prev
    b.append(u"- 单位先说清楚：**`daily usage limit` 的回复条数**（一辆车每被敲一次就多一条，所以这不是『几辆车』）＝今天 **%d 条**；其中其后有过产出 **%d 条**、至今无后续 **%d 条**。" % (len(allcap), len(recovered), len(censored)))
    b.append(u"- 换算成车：今天出现过额度回话的车道/实例 **%d 条**，此刻仍停在闸上的 **%d 条**（按名册尺为准，见 `patrol/_quota_roster_r1.py`）；条与条之间隔 >5 分才算另一次撞闸，这样数出来是 **%d 次**。" % (len(set(x[0] for x in allcap)), len(set(x[0] for x in censored)), episodes))
    if waits:
        b.append(u"- 恢复间隔（只数恢复的那 %d 枚）：min %.1f｜中位 %.1f｜p75 %.1f｜max %.1f 分。" % (
            len(waits), waits[0], waits[len(waits) // 2], waits[min(int(len(waits) * .75), len(waits) - 1)], waits[-1]))
        b.append(u"- 这条分布是**条件分布**（条件＝它回来了）。拿它说『都会在一小时半内回来』是错的，下面那 %d 枚没回来的就是反例。" % len(censored))
    b.append(u"")
    b.append(u"## 2. 分时段")
    for t0, t1, lab in bands:
        s = [x for x in allcap if t0 <= x[2] < t1]
        r = [x for x in s if x[3] is not None]
        c = [x for x in s if x[3] is None]
        w = sorted((x[3] - x[2]) / 60.0 for x in r)
        b.append(u"- %s：撞 %d｜已回 %d（min %s｜max %s 分）｜未回 %d%s" % (
            lab, len(s), len(r),
            ("%.1f" % w[0]) if w else u"—", ("%.1f" % w[-1]) if w else u"—", len(c),
            u"" if w else u"　← 这一段没有任何恢复样本，别拿它推『必然回血』"))
    b.append(u"")
    b.append(u"## 3. 至今无后续的那 %d 枚（按撞闸时间排）" % len(censored))
    for nick, sid8, e, _n in sorted(censored, key=lambda x: x[2]):
        b.append(u"- `%s`(%s) 撞于 %s，至今 %2.0f 分无产出" % (nick, sid8, hms(e), (now - e) / 60.0))
    b.append(u"")
    b.append(u"## 4. 已恢复的 %d 枚（可回读）" % len(recovered))
    for nick, sid8, e, w in sorted(recovered, key=lambda x: (x[3] - x[2])):
        b.append(u"- `%s` 撞于 %s → %s 恢复（%.1f 分）" % (nick, hms(e), hms(w), (w - e) / 60.0))
    b.append(u"")
    b.append(u"## 5. 边界与自记")
    b.append(u"- 只读 `projects/D--moodle/<id>.jsonl` 全量尾部记录；不判『谁偷懒』，撞闸前后的静默是闸不是选择。")
    b.append(u"- 本件第 1 版（19:01）只印恢复样本，害我在 19:16 的总线贴里把条件分布当边际用；第 2 版补上删失计数。19:16 那句『到 21:00 前多数能复工』的更正按规矩另发新帖，不改旧帖。")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(chr(10).join(b) + chr(10))
    print("写好 %s（%d B）：撞 %d｜已回 %d｜未回 %d｜中位 %s 分" % (
        os.path.abspath(OUT), os.path.getsize(OUT), len(allcap), len(recovered), len(censored),
        ("%.1f" % waits[len(waits) // 2]) if waits else "—"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
