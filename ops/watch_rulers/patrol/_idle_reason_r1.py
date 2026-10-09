# -*- coding: utf-8 -*-
"""值守 08:06 · 「这条车道现在为什么没在写字」的分类器（只读流水，快，不起 git）。

用户令：「你检查 qoder 的工人工作要读取他们的任务，看看有没有在干活」——所以判活不能只看进程端口，
要读他们自己最后一句话。类别只四类，且**中英都认**（第一版我只写中文词，结果 S4 用英文交底的
那条被错分成「已交付，无明确下一步」，而它其实卡在热文件裁语上）：
  等裁语 / 等派单 / 自己点名还欠一格 / 在跑
判不准的写「无法判定」，不硬塞——分类器误导过一次敲门，比不分类更糟。
"""
import glob
import io
import json
import os
import re
import sys
import time

PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
TAIL = 500000
RULING = re.compile(u"请裁|待裁|归你|你点|你判|一行授权|放行|等你|请你|需要您|要的一句|裁语|等一句|"
                    u"waiting for (you|the command)|your call|needs? a ruling|awaiting|"
                    u"tell me which|please (rule|decide)|need one line|等号令者|等裁", re.I)
DISPATCH = re.compile(u"待派|不自造活|没有新单|没人给我新单|下次叫我|等派单|"
                      u"awaiting (a )?(new )?(order|dispatch)|no order yet|"
                      u"don'?t invent|assign me|next time you (call|ask)", re.I)
SELF = re.compile(u"没改善|仍欠|下一步|未收口|还没做|没做完|没重跑|本回合没|"
                  u"not re-?run|still owed|left undone|not done|remaining|i did not (run|re-?run)", re.I)
RUN = re.compile(u"先读|现在|接下来|再来|正在|let me|now i|next i'?ll|i'?ll (first|now)", re.I)


def last_assistant(path, n_back=60):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - TAIL))
        blob = f.read().decode("utf-8", "replace")
    rows = []
    for line in blob.split("\n"):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    out = ""
    tools_open = False
    for r in rows[-n_back:]:
        m = r.get("message") or {}
        if m.get("role") == "assistant":
            c = m.get("content")
            if isinstance(c, list):
                txt = " ".join(b.get("text", "") for b in c
                               if isinstance(b, dict) and b.get("type") == "text")
                tools_open = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in c)
            else:
                txt = c if isinstance(c, str) else ""
            if txt.strip():
                out = txt.strip()
    return out, tools_open


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    files = sorted(glob.glob(os.path.join(PROJ, "*.jsonl")), key=os.path.getmtime, reverse=True)
    cnt = {}
    for p in files[:22]:
        sid = os.path.basename(p)[:8]
        idle = (now - os.path.getmtime(p)) / 60.0
        txt, tools_open = last_assistant(p)
        t = txt.replace("\n", " ")
        if not t:
            why = u"读不到正文（流水尾无助手文本）"
        elif idle < 3 and tools_open:
            why = u"在跑（未应答 tool_use + 流水在写）"
        elif idle < 3:
            why = u"在跑（流水在写）"
        elif RULING.search(t):
            why = u"等裁语"
        elif DISPATCH.search(t):
            why = u"等派单"
        elif SELF.search(t):
            why = u"自己点名还欠一格"
        else:
            why = u"无法判定（只按字面，不猜）"
        cnt[why] = cnt.get(why, 0) + 1
        print("   %s 静默%6.1f分  %-28s | %s" % (sid, idle, why, t[:100]))
    print("\n   合计：%s" % ", ".join(u"%s=%d" % kv for kv in sorted(cnt.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
