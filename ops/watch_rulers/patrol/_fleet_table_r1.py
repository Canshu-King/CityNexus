# -*- coding: utf-8 -*-
"""值守 08:14 · 一张「每条车道手上是什么单、交到哪一步、现在卡在哪」的表（只读，产出 md 文件）。

用户的原令是「检查工人工作要读取他们的任务」，而 `PATROL_LOG` 是按轮记的流水、
`HANDOVER` 是按证据记的总账，两者都不给「一条车道一行」的可读视图。这张表把四个已有的
只读读数拼到一起：
  ① 花名与 id —— `wake_names.ID8`（唯一真源，名字表今夜已改正过 dt/0441）
  ② 现在在干什么 —— `_idle_reason_r1.py` 的分类（读它自己最后一句助手正文）
  ③ 最近一枚已入账块 —— `_processed/*.md.inserted_<HHMMSS>`
  ④ 收件口还没落的块 —— root 里按命名门的 .md
输出 `FLEET_TABLE_0929.md`，供 11:00 汇报直接引用。不写账本、不动任何别人的件。
"""
import glob
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = r"D:/moodle/_qoder_ledger_inbox"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
PY = sys.executable
sys.path.insert(0, HERE)
import wake_names as WN

GATE = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")
# 文件名前缀 → 会话 id（车道块头常常只写花名不写 id，这张表是补那一块的）
PREFIX = {"ai": "bac10f40", "rel": "a68b0631", "dt": "be19052c", "map": "3b65af59",
          "n2": "9759f1ac", "n3": "49fe0d7b", "s4": "1d64acf5", "q": "904a042d",
          "newlane2": "6a150e1e", "newlane": "1ba48dbf", "0383": "4033270f",
          "r": "8ac89982", "dsh": "a6b95d59", "0441": "2d2d7428", "0437": "9cc37e57",
          "0415": "e4f3490f", "0370": "e4f3490f", "0369": "8e5245f0"}
ORD = re.compile(r"ORD-(\d{4})")


def owner_of(basename, first_line=""):
    # 三条来路依次试：① 文件名或块头里有 8 位会话 id；② 文件名是车道前缀（ai_/rel_/n2_…）；
    # ③ 文件名是**单号**形如 `qoder-0415_0709.md`——这种只能靠块头里那句「车道 …（会话 <id>）」认领，
    # 上一版我只看文件名，于是 21 枚这类块在表里是「无主」，账面数也就少算了。
    for hay in (basename, first_line):
        low = hay.lower()
        for c in WN.ID8:
            if c in low:
                return c
    low = basename.lower()
    for k in sorted(PREFIX, key=len, reverse=True):
        if low.startswith(k + "_") or low.startswith("qoder-" + k + "_"):
            return PREFIX[k]
    return None


def idle_map():
    """调 `_idle_reason_r1.py`，把它的分类原样搬过来（不重写判据，避免两份逻辑漂移）。"""
    try:
        r = subprocess.run([PY, os.path.join(HERE, "_idle_reason_r1.py")], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=600,
                           cwd=HERE, env=dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8"))
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return {}, "ERR %s" % type(e).__name__
    m = {}
    for l in out.split("\n"):
        mm = re.match(r"\s{3}([0-9a-f]{8}) 静默\s*([\d.]+)分\s+(\S.*?)\s*\|", l)
        if mm:
            m[mm.group(1)] = (mm.group(3).strip(), float(mm.group(2)))
    return m, ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    idle, err = idle_map()
    ins = {}
    DAY0 = time.mktime(time.strptime("2026-09-29 00:00", "%Y-%m-%d %H:%M"))
    skipped_old = 0
    for p in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")):
        # `_processed` 里混着 09-28 及更早的件，标记只有 HHMMSS 没有日期 ⇒
        # 用文件 mtime 卡「今夜 00:00 起」，不然这一列会把历史块一起算进来（我第一次就犯了）。
        if os.path.getmtime(p) < DAY0:
            skipped_old += 1
            continue
        b = os.path.basename(p)
        head1 = ""
        try:
            head1 = io.open(p, encoding="utf-8", errors="replace").readline()
        except Exception:
            pass
        cid = owner_of(b, head1)
        if not cid:
            continue
        ts = re.search(r"inserted_(\d{2})(\d{2})(\d{2})", b)
        t = "%s:%s:%s" % (ts.group(1), ts.group(2), ts.group(3)) if ts else "?"
        ords = sorted(set(ORD.findall(io.open(p, encoding="utf-8", errors="replace").read()[:2000])))
        cur = ins.get(cid, ("", [], 0))
        ins[cid] = (max(t, cur[0]), sorted(set(cur[1]) | set(ords)), cur[2] + 1)
    pend = {}
    for p in glob.glob(os.path.join(INBOX, "*.md")):
        b = os.path.basename(p)
        if not GATE.match(b):
            continue
        cid = owner_of(b)
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        ords = sorted(set(ORD.findall(txt[:2000])))
        pend.setdefault(cid, []).append((b, os.path.getsize(p), ords))

    lines = [u"# CityNexus 车道任务表（值守 09-29 %s 现读，只读拼装）\n" % time.strftime("%H:%M"),
             u"来源：`wake_names.ID8`（花名）+ `_idle_reason_r1.py`（读它自己最后一句助手正文）"
             u"+ `_processed/*.inserted_*`（入账时刻）+ 收件口 root（待插）。**这张表不判对错，只摆读数。**\n",
             u"| 车道 | id | 现在为什么没在写字 | 静默(分) | 今夜入账块数 | 最近入账 | 它交过的单 | 收件口还压着 |",
             u"|---|---|---|---|---|---|---|---|"]
    order = sorted(WN.ID8, key=lambda c: -ins.get(c, ("", [], 0))[2])
    tot_ins = 0
    for cid in order:
        if cid in ("494abfd7", "6efab655"):
            continue
        nm = WN.ID8[cid]
        why, mins = idle.get(cid, (u"读不到流水", -1))
        last_t, ords, n = ins.get(cid, (u"—", [], 0))
        tot_ins += n
        pj = pend.get(cid, [])
        pstr = ", ".join("%s(%d B)" % (x[0], x[1]) for x in pj) or u"—"
        lines.append(u"| %s | `%s` | %s | %s | %d | %s | %s | %s |" % (
            nm, cid, why, ("%.1f" % mins) if mins >= 0 else "?", n, last_t,
            "、".join("ORD-" + o for o in ords[:6]) or u"—", pstr))
    # 防呆（08:25 加）：入账件的前缀对不到任何会话 id 就具名报出来。
    # 这一张表今夜两次因为花名漏登记而少一条车道（`8ac89982`/`a6b95d59` 08:16、`9cc37e57` 08:23），
    # 少登记一条 = 它名下的派单在我眼里不存在，实测让 ORD-0429 躺了六小时。
    miss = {}
    for p in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")):
        if os.path.getmtime(p) < DAY0:
            continue
        b = os.path.basename(p)
        h1 = ""
        try:
            h1 = io.open(p, encoding="utf-8", errors="replace").readline()
        except Exception:
            pass
        if owner_of(b, h1) is None and not b.lower().startswith("cmdr_"):
            k0 = re.split(r"[_0-9]", b, maxsplit=1)[0]
            miss[k0] = miss.get(k0, 0) + 1
    if miss:
        lines.append(u"\n!! 有入账件的前缀对不到任何会话 id，表里就漏掉这条车道：%s"
                     % "、".join("%s×%d" % kv for kv in sorted(miss.items())))
        print("!! 未登记前缀：%s" % "、".join("%s×%d" % kv for kv in sorted(miss.items())))
    else:
        print("未登记前缀：0 类（今夜全部入账件都能对到会话 id）")

    lines.append(u"\n合计：今夜入账块 **%d** 枚（`_processed` 里带 inserted 标记的全部件数是另一回事，"
                 u"那一计把 09-28 之前的也算进去了）；收件口按命名门待插 **%d** 枚。"
                 % (tot_ins, sum(len(v) for v in pend.values())))
    lines.append(u"\n## 读数边界（别把这张表读成别的）\n")
    lines.append(u"- 「静默(分)」是**流水文件**的 mtime 差，长回合里它会滞后；真判活要看 `list_chat_sessions` 的 "
                 u"`runtimeState`+`pendingInteractionCount`（08:05 实测 20 条会话 `pendingInteractionCount` 全 0 ⇒ 没有一条停在弹窗上）。")
    lines.append(u"- 「现在为什么没在写字」是按那条会话自己最后一句话的字面分类的（等裁语/等派单/自己点名还欠/在跑/无法判定），"
                 u"**分类器不判断它该不该做**；裁语与派单都归号令者。")
    lines.append(u"- 表里没有的会话（`a6b95d59` 之外的历史 lane、`42d1a6fa` 值守自己）不算车道。")
    if err:
        lines.append(u"- 分类器读数不完整：%s" % err)
    out = os.path.join(HERE, "FLEET_TABLE_0929.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("写好 %s（%d B）；入账合计 %d 枚，待插 %d 枚"
          % (os.path.basename(out), os.path.getsize(out), tot_ins, sum(len(v) for v in pend.values())))
    for l in lines[:8]:
        print("   " + l[:150])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
