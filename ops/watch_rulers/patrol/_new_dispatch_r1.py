# -*- coding: utf-8 -*-
"""值守 07:25 · 「账本里已写、车道还没动」的派单扫描（只读）。

为什么单独做这一件：`wake_from_commits.py` 扫的是**提交**里的转达线索，而号令者现在的派单
是直接写进账本块的（单写者规矩：车道不写账本，只在收件箱交块）。车道不会自己回来重读账本
（09-26 起的实测：ready/cold 的会话从不主动复读），所以他写了而车道没动，就等于没派。

口径（照我自己定过的规矩）：
  · 只认**逐字 8 位会话 id** 的派单行；没有 id 的行（「谁手空谁领」这类）不进候选，只具名计数。
  · 「已动」= 账本里存在该会话自己写的块（块头含「会话 <id8>」或其块前缀），且块里出现那个 ORD 号，
    且该块头时间晚于派单时间。落不到的报 UNCLAIMED。
  · 收件人若是号令者自己的两个实例（494abfd7 / 6efab655）一律剔除——值守永远不敲号令者的窗口。
"""
import io
import os
import re
import sys
import glob
import time

LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wake_names as WN

CMDR_IDS = ("494abfd7", "6efab655")
HEAD = re.compile(r"^### (.*)$")
DATE = re.compile(r"2026-09-(\d{2}) (\d{2}):([0-9x])([0-9x])")  # 号令者会把分钟写成掩码 07:1x
DATE2 = re.compile(r"2026-09-(\d{2}) (\d{2})(\d{2})")  # 车道块头常写没冒号的 0245+08
ID8 = re.compile(r"\b[0-9a-f]{8}\b")
ORD = re.compile(r"ORD-(\d{4})")


def head_minutes(title):
    """块头时间取最大，换算成当日分钟；没有就回 None。

    两种写法都要认：号令者 `2026-09-29 07:1x`（掩码分钟，按十分钟下界，只用于「不早于」比较），
    车道常写没冒号的 `2026-09-29 0245+08`。上一版我只认带冒号的，于是 ai_0652/rel_0222
    这些块在我眼里「没有时间」，它们点的单被误判成「未动」——差点为这个去敲已经答过的车道。
    """
    best = None
    for m in DATE.finditer(title):
        d, h = int(m.group(1)), int(m.group(2))
        g3, g4 = m.group(3), m.group(4)
        if g3 == "x" or g4 == "x":
            mi = int(g3) * 10 if g3 != "x" else 0   # 掩码按十分钟下界，只用于「不早于」比较
        else:
            mi = int(g3 + g4)
        v = d * 1440 + h * 60 + mi
        if best is None or v > best:
            best = v
    for m in DATE2.finditer(title):
        d, h, mi = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if h > 23 or mi > 59:
            continue
        v = d * 1440 + h * 60 + mi
        if best is None or v > best:
            best = v
    return best


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")

    # 先切块：块头行 -> (标题, 起行, 止行)
    heads = [(i, HEAD.match(l)) for i, l in enumerate(lines)]
    marks = [(i, m.group(1)) for i, m in heads if m]
    blocks = []
    for k, (i, title) in enumerate(marks):
        j = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = "\n".join(lines[i:j])
        blocks.append((title, i + 1, j, head_minutes(title), body))

    hh = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    mm = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    since = 29 * 1440 + hh * 60 + mm  # 默认只看 09-29 06:00 起的派单，命令行可放宽
    disp = []
    free_form = 0
    for title, ln, j, tmin, body in blocks:
        if tmin is None or tmin < since:
            continue
        author = None
        for cid, nm in WN.ID8.items():
            if cid in title or ("（会话 %s）" % cid) in title:
                author = cid
                break
        if author not in CMDR_IDS and not re.search(r"号令者|CMDR", title):
            continue
        for lno in range(i := ln, j):
            l = lines[lno - 1]
            if "值守" in l[:12]:
                continue
            ids = [x for x in ID8.findall(l) if x not in CMDR_IDS and x in WN.ID8]
            ords = ORD.findall(l)
            MARK = re.search(r"→|派给|新开|分派|请只做|手空|我给了它", l)
            DELIVERED = re.search(r"申报|已落地|交了|交 `refs/heads|已入账", l)
            if ids and ords and MARK and not DELIVERED:
                if len(ids) > 1:
                    free_form += 1
                    continue
                disp.append((tmin, ords[0], ids[0], lno, l.strip()[:150]))
            elif ords and re.search(r"谁手空谁领|请只做|任一车道|任意车道", l):
                free_form += 1

    # 车道自己的块（按块头认作者）
    own = {}
    for title, ln, j, tmin, body in blocks:
        cid = None
        for c in WN.ID8:
            if c in title:
                cid = c
                break
        if cid is None or cid in CMDR_IDS:
            continue
        for o in ORD.findall(title):
            own.setdefault(cid, {}).setdefault(o, []).append(tmin)
        # 块内第一次出现的 ORD 也算它交过（块头常常不带号）
        # 时间兜底：车道块头经常没有时刻（`### ORD-0430 · 车道 ai（会话 bac10f40）PARTIAL 那一格…`），
        # 那就退到正文里第一个时刻；再没有就用正文所在行的位置当「晚于」判定的最弱证据（不参与比较）。
        t_use = tmin if tmin is not None else head_minutes(body[:1200])
        for o in ORD.findall(title):
            own.setdefault(cid, {}).setdefault(o, []).append(t_use)
        for o in set(ORD.findall(body)):
            own.setdefault(cid, {}).setdefault(o, []).append(t_use)

    # 第二遍：收件箱里的块（root 与 _processed）也算「这条车道动过这一单」——
    # 否则正在等代插的交付（`n2_0754.md` 07:54 写好、门还没插）会被误判成「未动」而招来一次多余敲门。
    # 两处坑都是现读的：① 入账后的文件被改名成 `<块>.md.inserted_<HHMMSS>`，`_processed/*.md` 一枚都匹不到；
    # ② 车道块头常常只写花名不写 8 位 id（`### ORD-0446 · 车道 N2 · …`），所以文件名前缀要有一张对照表。
    PREFIX = {"ai": "bac10f40", "rel": "a68b0631", "dt": "be19052c", "map": "3b65af59",
              "n2": "9759f1ac", "n3": "49fe0d7b", "s4": "1d64acf5", "q": "904a042d",
              "newlane2": "6a150e1e", "newlane": "1ba48dbf", "0383": "4033270f",
              "r": "8ac89982", "dsh": "a6b95d59", "0441": "2d2d7428", "0437": "9cc37e57",
              "0415": "e4f3490f", "0370": "e4f3490f", "0369": "8e5245f0"}
    for pat in (os.path.join(INBOX, "*.md"), os.path.join(INBOX, "_processed", "*")):
        for p in glob.glob(pat):
            b = os.path.basename(p)
            if not (b.endswith(".md") or ".md.inserted_" in b or ".md.my_" in b
                   or ".md.superseded" in b or ".md.refused" in b or ".md.retired" in b):
                continue
            try:
                txt = io.open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            first = txt.split("\n", 1)[0]
            cid = None
            for c in WN.ID8:
                if c in first or c in b:
                    cid = c
                    break
            if cid is None:
                low = b.lower()
                for k in sorted(PREFIX, key=len, reverse=True):
                    if low.startswith(k + "_") or ("_" + k + "_") in low[:14] or low.startswith("qoder-" + k + "_"):
                        cid = PREFIX[k]
                        break
            if cid is None or cid in CMDR_IDS:
                continue
            t_use = head_minutes(first)
            if t_use is None:
                lt = time.localtime(os.path.getmtime(p))
                t_use = int(29 * 1440 + lt.tm_hour * 60 + lt.tm_min)
            for o in set(ORD.findall(txt[:2000])):
                own.setdefault(cid, {}).setdefault(o, []).append(t_use)

    print("09-29 06:00 起号令者块里带 id 的派单行 %d 条；无收件 id 的自由形 %d 条（后者不敲门，只报数）"
          % (len(disp), free_form))
    unclaimed = []
    restated = []
    for tmin, o, cid, lno, txt in sorted(set(disp)):
        times = own.get(cid, {}).get(o, [])
        done = [t for t in times if t is not None and t >= tmin]
        early = [t for t in times if t is not None and t < tmin]
        p = glob.glob(os.path.join(PROJ, cid + "*.jsonl"))
        idle = (time.time() - os.path.getmtime(p[0])) / 60.0 if p else -1
        if done:
            state = "已动"
        elif early:
            # 09-29 08:07 加的第三态：车道确实交过这一单，只是它的块**早于**这条派单行——
            # 号令者喜欢抄自己上一轮的状态行，于是「已拒/已答」的单会被重述成像新派单。
            # 上一版我把这种误判成「未动」，差点去敲一条早就答过的车道（ORD-0428 / 车道 rel 就是这例：
            # 它在 02:22 那块 `:21166` 已答「我没有合法实现路径」，而派单行在 `:21149` 的 03:0x 块里）。
            state = "疑似重述（车道早于此行就交过同单）"
        else:
            state = "未动"
        print("  ORD-%s → %s(%s)  账本 :%d  流水静默 %5.1f 分  %s  | %s"
              % (o, WN.ID8[cid], cid, lno, idle, state, txt[:96]))
        if not done and not early:
            unclaimed.append((o, cid, lno, txt))
        elif early and not done:
            restated.append((o, cid, lno, txt))
    print("\n未动 %d 条；疑似重述 %d 条（后者一律不敲门）" % (len(unclaimed), len(restated)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
