# -*- coding: utf-8 -*-
"""值守 15:03 · 「看不见的交付」探测器（只读）。

起因：15:01 我偶然发现车道 N3 在收件口新建了 `_n3_draft_r3.md`（0 字节）。它对入账门是**完全隐形**的：
`ledger_inbox_apply_r2.py:67` 连目录都不看它（下划线开头），`:81` 又要求 `^[A-Za-z0-9._-]+_[0-9]{4}\\.md$`。
车道那边看到的效果是「我交了，没人理」，号令者那边看到的效果是「他没交」——两边都没错，
而没有任何人会报错。夜里也真栽过一次（07:16 那轮 `newlane_0637.md` 改名留痕，靠人记得）。

所以这里每轮主动扫一遍收件口根目录，把三类形状列出来：
  A 命名不合规（门根本不看）；
  B 合规但是 0 字节（写了个空块）；
  C 合规但同族已有更晚一代同名（旧块留在口里会被重复插入，实际不会——插过就移进 _processed，
    这里只报同前缀多枚并存，给人看一眼）。
"""
import glob
import io
import os
import re
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
GATE = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    files = [f for f in os.listdir(INBOX) if f.endswith(".md")]
    invisible, empty_ok, pending = [], [], []
    for name in sorted(files):
        p = os.path.join(INBOX, name)
        size = os.path.getsize(p)
        age = (now - max(os.path.getmtime(p), os.path.getctime(p))) / 60.0
        ok = bool(GATE.match(name)) and not name.startswith("_")
        if not ok:
            invisible.append((name, size, age))
        elif size == 0:
            empty_ok.append((name, age))
        else:
            pending.append((name, size, age))
    print("收件口根目录 %d 枚 .md：%d 枚合规待插、%d 枚合规但空文件、%d 枚**命名不合规（门根本不看）**"
          % (len(files), len(pending), len(empty_ok), len(invisible)))
    for name, size, age in invisible:
        print("  !! A 隐形 %s  %d B  写于 %.1f 分前  ⇒ 门会静默跳过（:67 下划线开头不看 / :81 要求 _4位数字.md）"
              % (name, size, age))
    for name, age in empty_ok:
        print("  !! B 空块 %s  0 B  写于 %.1f 分前  ⇒ 命名合规但没内容，跑门也只会按空文过或拒" % (name, age))
    for name, size, age in sorted(pending, key=lambda x: -x[2])[:6]:
        print("  .  C 待插 %s  %d B  已等 %.1f 分" % (name, size, age))
    stale = [x for x in pending if x[2] > 40]
    if invisible or empty_ok:
        print("结论：有 %d 枚交付正在被门**静默忽略**，需要提醒车道改名（我不改别人的文件）。"
              % (len(invisible) + len(empty_ok)))
    else:
        print("结论：没有隐形交付。%s" % ("（合规待插里最老 %0.0f 分）" % max(x[2] for x in pending) if pending else ""))
    if stale:
        print("  ?? 另有 %d 枚合规块等了 40 分以上（队列问题，归 _door_backlog_r1.py 报）" % len(stale))
    print("边界：只读列目录 + stat，0 次改名、0 次删除、0 次写账本、0 次插块。")
    return 1 if (invisible or empty_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
