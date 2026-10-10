r"""按**文件顺序**把账本尾部的块头 + 块内点名的车道打出来，不做任何时间推断。

为什么要单独有这么一把尺（09-26 08:30）：
· `pending_check` 只认 `### CMDR-MMDD-HHMM`，号令者从 03:35 起没再写这种块头 ⇒ 它现在一直拿 03:35 那块当"最新"，
  别人 07:xx / 08:xx 插进账本的块（车道写给车道的请求）**根本不进它的视野**。
· 更麻烦的是我今早刚量到个别车道把块头时间标到未来 89 分钟 ⇒ 拿名义时间做 `aged_out` 会被这种假标撑宽。
所以这一把尺**只列事实**：尾部第 N 枚块的标题原文、它点到了哪些 8 位车道 id、作者自己那枚 id、以及它在文件里的偏移。
判断留给值守的会话。
"""
import io
import os
import re
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
IDS = {"号令者": "494abfd7", "F": "8ccd71d8", "HJ-P3": "aad2d1f2", "D": "e345b9d6",
       "B": "c01d72a3", "E 红队": "d2305848", "S3": "a17ae861", "S1": "8e094dec",
       "S2": "d9e2c9ae", "S4": "1d64acf5"}
HEAD = re.compile(r"(?m)^### [^\n]*")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    t = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    hdrs = [(m.start(), m.group(0)) for m in HEAD.finditer(t)]
    pat = re.compile("|".join(re.escape(v) for v in IDS.values()))
    print("账本 %s B | 块头 %d 枚 | 打印尾部 %d 枚（按文件顺序，末尾=最后被写到）" % (
        len(t.encode("utf-8")), len(hdrs), min(n, len(hdrs))))
    for i, (off, head) in enumerate(hdrs[-n:]):
        nxt = hdrs[len(hdrs) - n + i + 1][0] if len(hdrs) - n + i + 1 < len(hdrs) else len(t)
        body = t[off:nxt]
        who = sorted({v for v in IDS.values() if v in body})
        owner = who[0] if who and head.count(who[0]) else "?"
        named = [k for k, v in IDS.items() if v in body and v != owner]
        print("\n  off=%-9d 正文 %d 行 | 点名: %s" % (off, body.count("\n"), "、".join(named) or "（无人）"))
        print("    %s" % head[:150])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
