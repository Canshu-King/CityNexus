# -*- coding: utf-8 -*-
"""值守 11:46 · 「门有没有停」探测器（只读）。

为什么今天才需要它：cron 的每小时一跳 `expiresAt = 11:00:00` 已经过期（`nextRunAt = 11:15:12` 在到期之后 ⇒ 不会再起），
所以入账代插从现在起**只靠号令者自己手动跑**。夜里那种「块在收件口躺一小时」本来是 cron 抖动，
现在它会变成常态风险：车道的活照交、门不跑 ⇒ 全天零落地。

判据两条，都现读：
  ① 收件口里有几枚按命名门算的待插块、最老的一枚躺了几分钟；
  ② `_processed/*.inserted_*` 里最后一次代插离现在几分钟。
只有「有待插」且「代插已停 30 分钟以上」才报门停——两条件缺一就不报，免得把空队列读成停摆。
"""
import glob
import io
import os
import re
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
NAMES = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")
GAP = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    pend = []
    for f in glob.glob(os.path.join(INBOX, "*.md")):
        b = os.path.basename(f)
        if NAMES.match(b):
            pend.append(((now - os.path.getmtime(f)) / 60.0, b))
    ins = sorted(glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")),
                 key=lambda x: max(os.path.getmtime(x), os.path.getctime(x)))
    last_name = os.path.basename(ins[-1]) if ins else "（无）"
    last_age = (now - max(os.path.getmtime(ins[-1]), os.path.getctime(ins[-1]))) / 60.0 if ins else -1
    oldest = max(pend)[0] if pend else 0.0
    print("待插 %d 枚（最老 %.1f 分）；最后一次代插 %s（%.1f 分前）"
          % (len(pend), oldest, last_name, last_age))
    if pend and last_age >= GAP:
        print("!! 门已停 %.1f 分且队列非空 ⇒ 车道交的活进不了账（cron 11:00 已到期，现在只能号令者手动跑）"
              % last_age)
        for age, b in sorted(pend, reverse=True)[:6]:
            print("   待插 %s  已躺 %.1f 分" % (b, age))
        return 3
    print("OK 无停摆签名（队列为空，或代插在 %.0f 分内跑过）" % GAP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
