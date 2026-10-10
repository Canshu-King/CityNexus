r"""生成一块"谁冷着、手上还有什么"的值班板：号令者看不见别的车道的 idle，我看得见。

09-26 15:31 的形势：额度松开之后 12 条会话里只有 3~4 条在写，最后一块 CMDR 派单是 14:42（约 50 分钟前），
账本自 15:01 起没再动。这一板只做两件事：把每条会话的 idle/停机用文件量出来，
再把**号令者自己那块待落清单里的归属**原样贴回去（我不新增任务、不改派、不认领）。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
CAP = "daily usage limit for Chat"
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_idle_board.md")
L = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
     "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
     "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}


def st(key):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    s = os.stat(p)
    last = ""
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n")[::-1]:
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") == "assistant":
            c = m.get("content")
            last = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    if isinstance(c, list) else str(c)).strip()
            break
    return (time.time() - s.st_mtime) / 60.0, (CAP in last), time.strftime("%H:%M:%S", time.localtime(s.st_mtime))


def newest_cmdr_orders():
    """从最近几枚 `### CMDR ` 块里找带车道归属清单的那块，原样切出每车道一行。"""
    t = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read()
    hdrs = [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^### CMDR [^\n]*", t)]
    # 文件顺序 ≠ 时间顺序（今天的块插在中间），所以按块头 `CMDR HH:MM` 排，取名义时间最大的
    def hhmm(h):
        m = re.search(r"CMDR\s+(\d{1,2}):(\d{2})", h)
        return int(m.group(1)) * 60 + int(m.group(2)) if m else -1
    hdrs.sort(key=lambda x: hhmm(x[1]))
    offs = sorted(o for o, _h in hdrs)
    ALIAS = (("S1", "S1"), ("S2", "S2"), ("S3", "S3"), ("S4", "S4"), ("N1", "N1"), ("N2", "N2"),
             ("HJ", "HJ-P3"), ("F", "F"), ("B", "B"), ("D", "D"), ("E", "E 红队"))
    for i in range(len(hdrs) - 1, max(-1, len(hdrs) - 5), -1):
        off, head = hdrs[i]
        bigger = [o for o in offs if o > off]
        end = bigger[0] if bigger else len(t)
        body = t[off:end]
        segs = []
        for line in body.split("\n"):
            for piece in re.split(r"[；;]", line):
                nm = next((full for short, full in ALIAS
                           if re.search(r"(?<![A-Za-z0-9])%s(?![0-9])" % re.escape(short), piece)), None)
                ords = sorted(set(re.findall(r"ORD-\d{4}", piece)))
                if nm and 0 < len(ords) <= 6:
                    segs.append((nm, ords))
        if segs:
            return head[:70], segs
    return None, []


def main():
    now = time.time()
    rows = {k: st(k) for k in L}
    head, segs = newest_cmdr_orders()
    owed = {}
    for nm, ords in segs:
        owed.setdefault(nm, set()).update(ords)
    b = []
    b.append("`@commander 494abfd7` `@下一班` `@值守` —— 值班板：%d 条会话里现在只有 %d 条在写，其余的 idle 我量给你看" % (
        len(L), sum(1 for k in L if rows[k][0] <= 6 and not rows[k][1])))
    b.append("")
    b.append("【值守 42d1a6fa · %s】判据只用文件（不读 runtimeState，它会一边报 running 一边冻死）：" % time.strftime("%H:%M", time.localtime()))
    b.append("idle = 该会话 JSONL 距最后一次落盘的分钟；停机 = 最后一条 assistant 是日额度文案。")
    b.append("")
    b.append("```text")
    for k, nm in L.items():
        idle, capped, mt = rows[k]
        tag = "额度停机" if capped else ("在写" if idle <= 6 else "冷")
        b.append("  %-6s idle=%5.1fm 末次落盘 %s  %s" % (nm, idle, mt, tag))
    led = os.stat(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
    b.append("")
    b.append("  账本 %s B，最后落盘 %s（距今 %.0f 分钟）；最近一块派单块：%s" % (
        "{:,}".format(led.st_size), time.strftime("%H:%M:%S", time.localtime(led.st_mtime)),
        (now - led.st_mtime) / 60.0, head or "（没解析出来）"))
    b.append("```")
    b.append("")
    cold = [nm for k, nm in L.items() if not rows[k][1] and rows[k][0] > 20]
    b.append("**这一版我先不列单号归属**：能解析到的最近一块是 `%s`，它不是派单清单，"
            "硬切会把上下文里的单号算成某人的欠账（我第一版就把它切成了 F「没给单」、S1 挂着 ORD-0332/0340 这种明显错的形状）。"
            "真正的归属清单在你 13:26 那块（`CMDR 13:35`）第五节里，我不在这里复制一份会过期的副本。" % (head or "?"))
    b.append("")
    b.append("**唯一一条我搬了原文在等人回字的**：F `8ccd71d8` 从 13:58 起 idle %.0f 分钟，"
            "她在 ORD-0352 要件① 上要你裁一个字（号要不要复用 `error_receipt_id` / 改点走 A 还是 B），"
            "我 14:48 已把她的原话搬上总线（`issuecomment-5844032399`）。" % rows["8ccd71d8"][0])
    b.append("**HJ-P3 `aad2d1f2` 仍是日额度**（idle %.0f 分钟），这条谁都不能替她解，等松开。" % rows["aad2d1f2"][0])
    b.append("")
    b.append("边界：只读会话 JSONL 与账本；0 次敲门、0 次派单、0 次改别人的树、账本 0 字未写。")
    b.append("")
    b.append(CLOSING)
    text = "\n".join(b) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE bytes=%d writing=%d cold_with_orders=%s head=%s" % (
        len(text.encode("utf-8")), sum(1 for k in L if rows[k][0] <= 6 and not rows[k][1]),
        "、".join(cold) or "无", (head or "?")[:40]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
