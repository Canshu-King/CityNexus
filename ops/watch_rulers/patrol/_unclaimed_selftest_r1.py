# -*- coding: utf-8 -*-
"""`_unclaimed_orders_r1.py` 的红/绿对照自测（合成件，绝不碰共享收件口）。

为什么要有这一枚：03:16 生产上「无人接的单」是 0 张。0 张有两种可能——真的没人被弃单，或者这把尺失去了报红的能力。
只看它变绿就宣布修好，是我自己定过规矩不许做的事（自己消失的红≠修好）。

三条合成单，每条走**确定性**证据，不看秒级时序：
  ① ORD-0999 收件人是一条静默一整天的真会话、也没有车道块提到 ⇒ 必须报红；
  ② ORD-0997 收件人是一个没有流水的 id ⇒ 必须报红，且明细不许把别的单的收件车道挂过来（03:14 实测错过）；
  ③ ORD-0996 靠合成车道块 `lane_note.md` 的正文提到 ⇒ 必须判已有人接。
     03:18 实测：这一条原来用「收件会话此刻在写」当正对照会假红——那一路比的是块写完与会话落笔的先后，
     秒级竞争（`收件会话已动=否` 就是这么来的），所以自测里不许拿它当正对照。

用法：python _unclaimed_selftest_r1.py    （全通过退 0；任一不符退 1 并印出现场）
"""
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # 控制台是 GBK，读数里有 ⇒ 与 ｜
PYEXE = sys.executable
FIX = os.path.join(HERE, "_fixture_inbox")

STALE_ID = "904a042d"      # 03:18 实测静默 1587 分的会话，不会自己变活
GHOST_ID = "ffffffff"      # 故意用一个没有流水的 id

TXT = (u"### CMDR test · 合成件（只给尺做红绿对照，不落真收件口）\n\n"
       + u"- `%s`（ORD-0999）：收件会话静默了一整天，必须被报成无人接。\n" % STALE_ID
       + u"- `%s`（ORD-0997）：没有这个会话的流水，必须报无人接，且明细不得借别的单的收件车道。\n" % GHOST_ID
       + u"- `%s`（ORD-0996）：这张单有车道块正文提到（同目录 `lane_note.md`），必须判已有人接，"
         u"而且不许靠『收件会话已动』那一路。\n" % STALE_ID
       # D 路（裁语行形制，15:44 补）：单号在句中、收件人在行首——缺这一路时六张已裁过的单被整批报成无人接
       + u"7. `%s`：开新单 ORD-0995 归你领，不在别的单里塞。\n" % STALE_ID
       + u"8. `%s`：顺带提到 ORD-0993 已在别处落。\n" % STALE_ID)

LANE_TXT = (u"### 车道 %s 合成块 · ORD-0996 我接了：正文里就写着单号，给尺的『车道块』那一路当正对照。\n" % STALE_ID)


def build():
    d = os.path.join(FIX, "_processed")
    if not os.path.isdir(d):
        os.makedirs(d)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    for old in os.listdir(FIX):
        fp = os.path.join(FIX, old)
        if os.path.isfile(fp):
            os.remove(fp)
    f = os.path.join(d, "cmdr_test.md.inserted_%s" % time.strftime("%H%M%S"))
    io.open(f, "w", encoding="utf-8", newline="\n").write(TXT)
    io.open(os.path.join(FIX, "lane_note.md"), "w", encoding="utf-8", newline="\n").write(LANE_TXT)
    now = time.time()
    os.utime(f, (now, now))
    return f


def row_of(out, num):
    m = re.search(u"^\\s*" + num + u"\\s+.*$", out, re.M)
    return m.group(0).strip() if m else ""


def main():
    f = build()
    env = dict(os.environ, UNCLAIMED_INBOX=FIX, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PYEXE, os.path.join(HERE, "_unclaimed_orders_r1.py"), "3"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=HERE, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    rows = dict((n, row_of(out, n)) for n in ("ORD-0999", "ORD-0997", "ORD-0996", "ORD-0995", "ORD-0993"))
    want = {"ORD-0999": "**无人接**", "ORD-0997": "**无人接**", "ORD-0996": "已有人接",
            "ORD-0995": "**无人接**", "ORD-0993": "**无人接**"}
    fails = []
    for num, exp in want.items():
        if not rows[num]:
            fails.append(u"%s：读数里根本没有这一行（尺可能整把没跑成）" % num)
        elif exp not in rows[num]:
            fails.append(u"%s：期望「%s」，实读：%s" % (num, exp, rows[num][:112]))
    # 正对照必须是被『车道块』那一路认下的，不能靠秒级时序那一路
    if rows["ORD-0996"] and u"车道块=否" in rows["ORD-0996"]:
        fails.append(u"ORD-0996 判对了但走的是『收件会话已动』那一路（正对照失效）：%s" % rows["ORD-0996"][:112])
    mm = re.search(u"^\\s*!! ORD-0997(.*)$", out, re.M)
    if not mm:
        fails.append(u"ORD-0997 的明细行没有（它该被点名）")
    elif u"在写" in mm.group(1) or u"ORD-0996" in mm.group(1):
        fails.append(u"ORD-0997 明细借了别的单的收件车道：%s" % mm.group(0).strip()[:130])
    # D 路要到的不是「判成已有人接」，而是**点得到名**：这张派了、收件车道还没动，判语仍该是无人接；
    # 但那一格必须写出收件 id —— 15:44 那次假红的害处就在明细写成「块里没点名」，只能借别的车道现况。
    if rows["ORD-0995"] and u"块里没点名" in rows["ORD-0995"]:
        fails.append(u"ORD-0995 没被 D 路认出收件车道（还写块里没点名）：%s" % rows["ORD-0995"][:112])
    # D 路的闸：同一形制但行里没有「你」，不许把顺带提到的单号算给这枚收件车道
    if rows["ORD-0993"] and u"块里没点名" not in rows["ORD-0993"]:
        fails.append(u"ORD-0993 这一行没有「你」，D 路不该配它：%s" % rows["ORD-0993"][:112])
    total = re.search(u"无人接的单 (\\d+) 张", out)
    print(u"合成件：%s｜车道块：lane_note.md" % os.path.basename(f))
    for num in ("ORD-0999", "ORD-0997", "ORD-0996", "ORD-0995", "ORD-0993"):
        print(u"   %s" % (rows[num] or u"（无该行）"))
    print(u"汇总：%s（期望 4）" % (total.group(0) if total else u"读数不全"))
    if total and total.group(1) != "4":
        fails.append(u"汇总张数不是 4：%s" % total.group(0))
    if fails:
        print(u"FAIL %d 条：" % len(fails))
        for x in fails:
            print(u"   - " + x)
        return 1
    print(u"PASS：四张该红的都红了（静默会话、无流水 id、被 D 路点名但那条车道没动、形制像 D 却没有「你」的那张），"
          u"该绿的靠车道块判出来，明细也没借别的单的收件车道 ⇒ 这把尺报得出红，D 路补的是「点得到名」这一格。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
