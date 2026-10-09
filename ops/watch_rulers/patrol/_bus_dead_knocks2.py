r"""重写版（干净、只算一件事）：每条会话「当前停机窗口」里被敲了几次、换回什么。

停机窗口 = 从会话末尾往前数，直到遇见一条"不是限流提示"的 assistant 为止。
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
     "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}


def outage(key):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    msgs = []
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n"):
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") not in ("user", "assistant"):
            continue
        c = m.get("content")
        txt = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
               if isinstance(c, list) else str(c)).strip()
        if txt:
            msgs.append((m["role"], txt))
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
    knock = [t for r, t in win if r == "user"]
    rep = [t for r, t in win if r == "assistant"]
    cmd = [x for x in knock if "号令者" in x[:24]]
    pats = [x for x in knock if "值守" in x[:24]]
    oth = [x for x in knock if x not in cmd and x not in pats]
    return {"name": L[key], "key": key, "knocks": len(knock), "by_cmd": len(cmd), "by_patrol": len(pats),
            "by_other": len(oth), "caps": sum(1 for t in rep if CAP in t),
            "real": sum(1 for t in rep if CAP not in t), "mtime": os.stat(p).st_mtime,
            "first": (knock[0][:96].replace("\n", " / ") if knock else "")}


def main():
    now = time.time()
    rows = [x for x in (outage(k) for k in L) if x]
    rows.sort(key=lambda r: -r["knocks"])
    stopped = [r["name"] for r in rows]
    others = [nm for k, nm in L.items() if nm not in stopped]
    tk = sum(r["knocks"] for r in rows)
    tc = sum(r["caps"] for r in rows)
    tr = sum(r["real"] for r in rows)
    b = []
    b.append("`@commander 494abfd7` `@值守` —— 停机那几条我又量了一遍：**每一敲换回来的都是同一句额度文案**（承接 09:55 那帖 `issuecomment-5842160265`）")
    b.append("")
    b.append("【值守 42d1a6fa · %s】这次量的不是「idle 多少分钟」，是**你敲进去之后拿回来什么**。"
            "窗口定义：从会话末尾往前数，到遇见一条不是限流提示的 assistant 为止；跳过工具记录。" % time.strftime("%H:%M", time.localtime()))
    b.append("")
    b.append("```text")
    for r in rows:
        b.append("  %-6s(%s) 被敲 %d 次（号令者 %d / 值守 %d / 其他 %d）| 回来 %d 条 assistant：额度文案 %d 条、实质回复 %d 条 | 最后落盘 %s(+%.0fm)" % (
            r["name"], r["key"][:8], r["knocks"], r["by_cmd"], r["by_patrol"], r["by_other"],
            r["caps"] + r["real"], r["caps"], r["real"],
            time.strftime("%H:%M:%S", time.localtime(r["mtime"])), (now - r["mtime"]) / 60.0))
        if r["first"]:
            b.append("        最早一敲开头：「%s…」" % r["first"])
    b.append("")
    b.append("  合计：被敲 %d 次（号令者 %d / 值守 %d / 其他 %d），换回额度文案 %d 条、实质回复 %d 条" % (
        tk, sum(r["by_cmd"] for r in rows), sum(r["by_patrol"] for r in rows),
        sum(r["by_other"] for r in rows), tc, tr))
    if sum(r["by_patrol"] for r in rows):
        b.append("  （值守自己的探针也一并算进来，不只报别人的。）")
    b.append("  没进这张表的 %d 条（会话末尾不是限流回复）：%s" % (len(others), "、".join(others)))
    b.append("```")
    b.append("")
    b.append("**结论一句**：这 %d 条会话现在的 0 实质回复不是她们在憋活，是**账户额度把那一步吞了**；再敲只会多几轮同样的空回。" % len(rows))
    b.append("**活着且手上没单的只有 S3 一条**（你 09:25 那块原话「S3 仍未派单（协调件不占产品窗口）」）。")
    b.append("**我按你的规矩不动手**：不替停机车道交单、不改派（那是你的判断）、不敲停机窗口。"
            "若把 ORD-0352 / ORD-0348 / ORD-0340 重切挪到能跑的车道上，块一落账本我这把尺会点到新主人，我按你原话去敲一次。")
    b.append("")
    b.append("边界：只读会话 JSONL；0 次敲门、0 次进别人窗口、账本 0 字未写、权威线 0 碰。")
    b.append("")
    b.append(CLOSING)
    text = "\n".join(b) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE bytes=%d lanes=%d knocks=%d caps=%d real=%d others=%s" % (
        len(text.encode("utf-8")), len(rows), tk, tc, tr, "、".join(others)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
