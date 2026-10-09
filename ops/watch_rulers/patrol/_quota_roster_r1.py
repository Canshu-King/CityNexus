# -*- coding: utf-8 -*-
"""轻量名册（只读、只取每枚流水尾部 150 KB）：谁在写、谁停在额度上、谁静默但没撞闸。

为什么单开这张：2026-09-29 傍晚这波是**额度潮**（18:38–18:57 十条车道接连撞闸），
判「要不要敲门」必须区分『停在闸上』与『自己停了』——敲一辆没油的车只是把消息堆在它窗口里。
旧的分诊脚本整份读流水（号令者那份 218 MB），一轮十几分钟太贵；这张只读尾部，够判状态。
输出会被 autumn_watch 每轮追加到 quota_roster_0929.log，形成今晚的时间序列。
"""
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
WIN = 150 * 1024
NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道",
    "e766b154": "新车道472",
    "494abfd7": "号令者B", "6efab655": "CMDR-A",
}
# 今天实测的『撞额度 → 恢复产出』中位数（QUOTA_WAVE_0929.md，15 个样本）
MEDIAN_RECOVER_MIN = 20.7


def last_kinds(blob):
    """最后一条 assistant/user 记录里装的是什么：text（说人话）还是工具块（在跑东西）。"""
    rows = [l.strip() for l in blob.split(chr(10)) if l.strip().startswith("{")]
    for line in reversed(rows[-40:]):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant"):
            continue
        c = (o.get("message") or {}).get("content")
        if isinstance(c, list):
            ks = set(x.get("type", "") for x in c if isinstance(x, dict))
            if ks:
                return "+".join(sorted(ks))
    return "?"


def universe(hours=12.0):
    """名册要扫的会话 = NICKS ∪ 最近 hours 小时真的动过的流水文件。

    09-30 18:33 实测：NICKS 只 13 条，而当天 10 小时内动过的会话有 18 枚（今晚主力 1ba48dbf /
    e766b154 / da46954a / cff87c64 / 5a53846b / 6a150e1e / 8ac89982 等都不在表里）——
    拿静态表数「在写几条」会把大半车队数成不存在。认不到花名也要数，标 `未登记·<id8>`。
    """
    ids = dict(NICKS)
    cut = time.time() - hours * 3600.0
    for f in os.listdir(BASE):
        if f.endswith(".jsonl"):
            fp = os.path.join(BASE, f)
            if os.path.getmtime(fp) >= cut:
                ids.setdefault(f[:8], u"未登记·" + f[:8])
    for sid in ("494abfd7", "42d1a6fa", "6efab655"):
        ids.pop(sid, None)
    return ids


def main():
    now = time.time()
    capped, writing, quiet = [], [], []
    for sid8, nick in universe().items():
        c = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
        if not c:
            continue
        p = os.path.join(BASE, max(c, key=lambda f: os.path.getsize(os.path.join(BASE, f))))
        try:
            n = os.path.getsize(p)
            fh = io.open(p, "rb")
            fh.seek(max(0, n - WIN))
            blob = fh.read().decode("utf-8", "replace")
            fh.close()
        except Exception:
            continue
        last = None
        for l in blob.split("\n"):
            l = l.strip()
            if not l.startswith("{"):
                continue
            try:
                o = json.loads(l)
            except Exception:
                continue
            if o.get("type") not in ("user", "assistant"):
                continue
            m = o.get("message") or {}
            cc = m.get("content")
            t = cc if isinstance(cc, str) else "".join(x.get("text", "") for x in (cc or []) if isinstance(x, dict))
            if t.strip():
                last = t.strip().replace("\n", " ")
        age = (now - os.path.getmtime(p)) / 60.0
        # 21:19 学到：mtime 静默不等于停下——尾条若是 tool_use/tool_result/thinking，
        # 那是**正在跑一个长工具**（构建、套件），敲它只是打断。所以静默那档再分两类。
        kinds = last_kinds(blob)
        if last and "daily usage limit" in last:
            capped.append((nick, sid8, age))
        elif age < 8:
            writing.append((nick, sid8, age))
        else:
            quiet.append((nick, sid8, age, kinds))
    print("%s 名册：停在额度 %d｜在写 %d｜静默非闸 %d" % (
        time.strftime("%H:%M:%S"), len(capped), len(writing), len(quiet)))
    if capped:
        print("   闸上：" + "、".join("%s(%.0f分前)" % (x[0], x[2]) for x in sorted(capped, key=lambda y: y[2])))
    if writing:
        print("   在写：" + "、".join("%s(%.0f分)" % (x[0], x[2]) for x in sorted(writing, key=lambda y: y[2])))
    if quiet:
        print("   静默非闸：" + "、".join("%s(%.0f分｜尾条 %s)" % (x[0], x[2], x[3] if len(x) > 3 else "?") for x in sorted(quiet, key=lambda y: -y[2])))
    print(u"   口径：今天『撞额度→恢复产出』能数到 15 个样本、中位 %.1f 分（QUOTA_WAVE_0929.md）——但那条只统计**回来了的**；"
          "至今没回的另有一批（同一件里分开印）。所以超中位数仍不写的车，可能是闸还没松，也可能是今晚不松：**等回血只能当参考，不能当计划**。" % MEDIAN_RECOVER_MIN)
    print("   边界：只读流水尾部与 mtime；0 次写账本、0 次派单、0 次重启任何进程。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
