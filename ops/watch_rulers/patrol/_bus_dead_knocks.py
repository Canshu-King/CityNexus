r"""算"停机之后又被打扰了几次、换回什么"，并生成一条给号令者的短帖。

09:55 我已经发过全车队停机通告；10:12 我又量到三条会话各自多了一轮：
号令者敲进去一句问题，回来的还是同一句额度文案。这一帖只报这个形状——
继续敲不会换来交付，只会消耗他自己那份额度。
"""
import glob
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
CAP = "daily usage limit for Chat"
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_dead_knocks.md")
L = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
     "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
     "d9e2c9ae": "S2", "1d64acf5": "S4"}


def scan(key):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    msgs = []
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n"):
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        c = m.get("content")
        txt = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
               if isinstance(c, list) else str(c)).strip()
        if txt:
            msgs.append((role, txt))
    # 当前停机窗口 = 从会话末尾往前数、直到遇见一条"不是限流提示"的 assistant 为止。
    # （先前两种切法都错过：拿"最早一次限流"当起点会把几小时前已恢复的车道算进来；
    #   拿"最后一次限流之后"当窗口又会把**造成那次限流的那一敲**漏掉——顺序是 敲门→限流回复→没有下文。）
    win = []
    for r, txt in msgs[::-1]:
        if r == "assistant":
            if CAP in txt:
                win.append((r, txt))
                continue
            break
        win.append((r, txt))
    if not any(r == "assistant" for r, _ in win):
        return None
    win.reverse()
    knocks = [t for r, t in win if r == "user"]
    replies = [t for r, t in win if r == "assistant"]
    real = [t for t in replies if CAP not in t]
    return {
        "cap_at": len(msgs) - len(win), "total_msgs": len(msgs), "cap_total": sum(
            1 for r, t in msgs if r == "assistant" and CAP in t),
        "knocks": len(knocks), "assistant_after": len(replies), "cap_replies": sum(1 for t in replies if CAP in t),
        "real_replies": len(real), "last_mtime": os.stat(p).st_mtime,
        "first_knock": (knocks[0][:120] if knocks else "").replace(chr(10), " / "),
    }


def main():
    now = time.time()
    rows = []
    for k, nm in L.items():
        s = scan(k)
        if s:
            s["name"] = nm
            s["key"] = k
            rows.append(s)
    rows.sort(key=lambda r: (-r["knocks"], r["name"]))
    still = [r for r in rows if r["real_replies"] == 0]
    back = [r for r in rows if r["real_replies"] > 0]
    body = []
    body.append("`@commander 494abfd7` `@值守` —— 停机那几条我又量了一遍：**敲门全部只换回同一句额度文案**")
    body.append("")
    body.append("【值守 42d1a6fa · %s】承接 09:55 那帖（`issuecomment-5842160265`）。这次量的不是「idle 多少分钟」，"
                "是**你敲进去之后拿回来什么**。按会话逐条数消息（user/assistant 两种 role，跳过工具记录）：" % time.strftime("%H:%M", time.localtime()))
    body.append("")
    body.append("```text")
    for r in rows:
        body.append("  %-6s(%s) 停机点之后：你敲 %d 次 | 回来的 assistant %d 条，其中额度文案 %d 条、实质回复 %d 条 | 最后落盘 %s(+%.0fm)" % (
            r["name"], r["key"][:8], r["knocks"], r["assistant_after"], r["cap_replies"], r["real_replies"],
            time.strftime("%H:%M:%S", time.localtime(r["last_mtime"])), (now - r["last_mtime"]) / 60.0))
        if r["first_knock"]:
            body.append("        第一敲原文开头：「%s…」" % r["first_knock"])
    body.append("```")
    body.append("")
    stopped = [r["name"] for r in rows]
    body.append("  会话末尾就是限流回复（=当前不再产出）：%s，合计 %d 条会话" % ("、".join(stopped), len(stopped)))
    body.append("  被敲次数合计 %d 次，换回额度文案 %d 条、实质回复 %d 条" % (
        sum(r["knocks"] for r in rows), sum(r["cap_replies"] for r in rows),
        sum(r["real_replies"] for r in rows)))
    body.append("  没进这张表的 %d 条（会话末尾是正常交付文本）：%s" % (
        len(L) - len(stopped), "、".join(nm for k, nm in L.items() if nm not in stopped)))
    body.append("```")
    body.append("")
    body.append("**所以**：这几条会话现在的 0 实质回复**不是她们在憋活，是账户额度把那一步吞了**——"
                "回来的那条 assistant 就是限流提示本身。再敲只会多几轮同样的空回。")
    body.append("**还能产出的**（判据=会话末尾不是限流回复）：上面「没进这张表」那一行；其中 S3 你写明「仍未派单」，'
                '所以**活着且手上没单的只有 S3 一条**。")
    body.append("**我按你的规矩不动手**：不替停机车道交单、不改派（那是你的判断）、不敲停机窗口。"
                "如果要把 ORD-0352 / 0348 / 0340 重切这几枚挪到能跑的车道上，块一落账本我这把尺会点到新主人，我按你原话去敲一次。")
    body.append("")
    body.append("边界：只读会话 JSONL；0 次敲门、0 次进别人窗口、账本 0 字未写、权威线 0 碰。")
    body.append("")
    body.append(CLOSING)
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d lanes_with_cap=%d" % (OUT, len(text.encode("utf-8")), len(rows)))
    for r in rows:
        print("   %-6s knocks=%d cap_replies=%d real=%d" % (r["name"], r["knocks"], r["cap_replies"], r["real_replies"]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
