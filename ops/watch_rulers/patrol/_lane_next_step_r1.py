# -*- coding: utf-8 -*-
"""某条车道「手上还有没有明确的下一格」——只读判定。

为什么要这张尺（2026-09-29 15:13）：号令者的代插门 15:12 刚清完队列，
他自己说「ORD-0444/0437/0440 等 rebase 回来我继续排队落地」——也就是说
**车道停 20 分钟以上不一定是有活没干，也可能是没人给它下一格**。
我要推「停下的人继续」，就得先分清这两件事，不然敲门只是在骚扰。

判据（全部只读，0 次写盘 / 0 次派单 / 0 次改动任何人的枝）：
  1) 账本里点到这枚会话 id 短前缀的行 = 号令者亲手的点名（派单或退回）；
  2) 该车道流水里这枚 id 有没有被消费过——用「点名行里出现的 ORD 号
     是否出现在该车道流水」来近似，命中即认为它收到过这一格；
  3) 最近一次交件（_qoder_ledger_inbox 里以车道名开头的块）时间。
报出来的三件事一起看才叫事实：最后写流水、最后一次交件、最后一条没被消费的点名。
"""
import io
import os
import re
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"

LANES = {
    "9759f1ac": ("N2", "n2"),
    "904a042d": ("Q", "qoder-q"),
    "bac10f40": ("AI", "ai"),
    "2d2d7428": ("0441", "qoder-0441"),
    "e4f3490f": ("道0370", "dao0370"),
    "be19052c": ("dt", "dt"),
    "3b65af59": ("map", "map"),
    "1d64acf5": ("S4", "s4"),
    "a68b0631": ("rel", "rel"),
    "8ac89982": ("R0417", "r0417"),
    "4033270f": ("0383", "qoder-0383"),
    "a6b95d59": ("DSH", "dsh"),
    "6a150e1e": ("newlane2", "newlane2"),
    "1ba48dbf": ("newlane", "newlane"),
    "49fe0d7b": ("N3", "n3"),
    "8e5245f0": ("道0369", "dao0369"),
}


def sh_jsonl(sid):
    try:
        for f in sorted(os.listdir(BASE), key=len, reverse=True):
            if f.startswith(sid) and f.endswith(".jsonl"):
                return os.path.join(BASE, f)
    except Exception:
        pass
    return None


def last_block(prefixes):
    best = (0, None)
    try:
        names = os.listdir(INBOX) + os.listdir(os.path.join(INBOX, "_processed"))
    except Exception:
        names = []
    for root, _, fs in os.walk(INBOX):
        for f in fs:
            low = f.lower()
            for pre in prefixes:
                if low.startswith(pre) and ".md" in low:
                    p = os.path.join(root, f)
                    try:
                        m = os.path.getmtime(p)
                    except Exception:
                        continue
                    if m > best[0]:
                        best = (m, f)
    return best


def main():
    idle_min = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
    txt = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    lines = txt.split("\n")
    now = time.time()
    print("=== 下一格判定（只读，阈值 %.0f 分钟）%s" % (idle_min, time.strftime("%H:%M")))
    stalled = []
    for sid, (nick, pre) in sorted(LANES.items(), key=lambda x: x[1][0]):
        p = sh_jsonl(sid)
        if not p:
            print("  %-9s 流水找不到" % nick)
            continue
        mt = os.path.getmtime(p)
        age = (now - mt) / 60.0
        body = io.open(p, encoding="utf-8", errors="replace").read()
        hits = [(i + 1, l) for i, l in enumerate(lines) if sid in l]
        un = []
        for ln, line in hits:
            for om in re.finditer(r"ORD-0(\d{3})", line):
                num = "ORD-0" + om.group(1)
                if num not in body:
                    un.append((ln, num, line.strip()[:150]))
        bm, bf = last_block([pre, nick])
        if age >= idle_min:
            stalled.append(nick)
            print("  %-9s 流水 %.0f 分前｜交件 %s｜点名 %d 行，其中未被消费 %d 格"
                  % (nick, age, (time.strftime("%H:%M", time.localtime(bm)) + " " + os.path.basename(str(bf))[:26])
                     if bf else "无", len(hits), len(un)))
            for ln, num, line in un[-3:]:
                print("      未消费 %s（账本 L%d）：%s" % (num, ln, line[:150]))
    print("小结：%d 条过阈值；「未被消费」只说明该车道流水里没出现过这个单号，"
          "不等于号令者没敲过（他可能用别的话面敲门），也不等于我该替它开工——"
          "动作只有两种：把点名行原样转达（收件 id 逐字相同才转），或什么都不做。" % len(stalled))
    print("边界：只读（账本、流水、收件口 mtime），0 次写账本、0 次派单、0 次改动任何人的枝、0 次重启任何进程。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
