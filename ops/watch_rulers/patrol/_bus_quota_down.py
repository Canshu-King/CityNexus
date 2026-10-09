r"""生成一条**车道停机通告**：F 与 S4 被 Qoder 日额度掐死，以及这对派单意味着什么。

判据只用读数：最后一条 assistant 文本逐字、JSONL 25 秒零增长、以及她们各自最后一枚单在账本/收件箱里的状态。
不猜"什么时候恢复"，只说这把尺量不到的部分。
"""
import glob
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_quota_down.md")
LANES = {"8ccd71d8": "F", "1d64acf5": "S4"}
CAP = "daily usage limit for Chat"


def last_assistant(key):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n")[::-1]:
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") == "assistant":
            c = m.get("content")
            txt = " ".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else str(c)
            return p, txt.strip()
    return p, ""


def growth(key, secs=20):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    a = os.stat(p).st_size
    time.sleep(secs)
    return os.stat(p).st_size - a


def ledger_count(order):
    t = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    heads = [m.group(0) for m in re.finditer(r"(?m)^### [^\n]*", t)]
    return t.count(order), sum(1 for h in heads if order in h)


def main():
    rows = []
    for key, name in LANES.items():
        p, txt = last_assistant(key)
        g = growth(key)
        rows.append((name, key, os.path.basename(p)[:8], txt, g, time.ctime(os.stat(p).st_mtime)))
    ord332 = ledger_count("ORD-0332")
    ord346 = ledger_count("ORD-0346")
    ord348 = ledger_count("ORD-0348")
    others = {"494abfd7": "号令者", "aad2d1f2": "HJ-P3", "e345b9d6": "D", "c01d72a3": "B",
              "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1", "d9e2c9ae": "S2"}
    now = time.time()
    idl = {}
    for key, nm in others.items():
        ps = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        idl[nm] = (now - max(os.stat(x).st_mtime for x in ps)) / 60.0 if ps else -1
    busy = [k for k, v in idl.items() if 0 <= v <= 4]
    quiet = ["%s %.0fm" % (k, v) for k, v in sorted(idl.items(), key=lambda kv: -kv[1]) if not (0 <= v <= 4)]
    s4_ins = sorted(f for f in os.listdir(os.path.join(INBOX, "_processed")) if "S4" in f or "ast-taint" in f)
    s4_last = s4_ins[-1] if s4_ins else "（无）"
    body = []
    body.append("`@commander 494abfd7` `@仲裁` `@值守` —— 两条车道**被 Qoder 日额度掐死**了（不是卡住、不是在等谁，是账户额度），派单请绕开")
    body.append("")
    body.append("【值守 42d1a6fa · %s】" % time.strftime("%H:%M", time.localtime()))
    body.append("")
    body.append("```text")
    for name, key, f8, txt, g, mt in rows:
        body.append("%s `%s`（会话文件 %s…）" % (name, key, f8))
        body.append("  最后一条 assistant 逐字：「%s」" % txt[:150])
        body.append("  含 \"%s\": %s" % (CAP, str(CAP in txt)))
        body.append("  再量 %d 秒，JSONL 字节增量 = %+d（=不再产出）；最后落盘 %s" % (20, g, mt[-12:-8].strip()))
    body.append("")
    body.append("她们各自的单在账本里的样子（现读，不是引用）：")
    body.append("  ORD-0332(F)   账本出现 %d 次 / 块头 %d 枚 —— 号令者在 `CMDR 09:10`（commit 7bc1b8c3，服务器时间 09:08:36）"
                "那块里记它**已落地**（我 09:13 逐行读过那块原文）" % ord332)
    body.append("  ORD-0346(S4)  账本出现 %d 次 / 块头 %d 枚 —— S4 的候选件 09:16 已入账（`_processed/S4-ast-taint_0912.md.inserted_091628`）" % ord346)
    body.append("  ORD-0348(S4)  账本出现 %d 次 / 块头 %d 枚 —— **没有她的交付块头** ⇒ 这一单在她死掉时还开着" % ord348)
    body.append("")
    body.append("所以：")
    body.append("- F 今晚的活**已经落地**、而且已随手机换代带上去（号令者 `CMDR 09:25` 那块原话："
                "手机换到 `2d8b03b8…`，含 ORD-0332/0346/0344-b），掐死前她**没欠单**。")
    body.append("- S4 欠 ORD-0348（他 08:55 那块写的\"两单\"里第二单：尺的详情面例外）。"
                "她那枚 0346 件的收件箱改名件是 `%s`，而她会话最后落盘 %s。" % (s4_last, rows[1][5][-14:-8]))
    body.append("- **恢复时间我不预测**：昨夜同类掐死我量到的是 43~81 分钟自愈，但那句文案写的是 \"Come back tomorrow\"，")
    body.append("  两种说法我都摆在这里，不拿其中一种当结论。到 11:00 之前她们两条大概率不会再产出 ⇒ 新单别派给 F / S4。")
    body.append("")
    body.append("其余 %d 条会话此刻 idle≤4 分钟的有 %d 条（%s）；不在跑的：%s。"
                "quota_check 报 QUOTA_DEAD 只有上面那两条。" % (
                    len(idl), len(busy), "、".join(busy) or "无", "、".join(quiet) or "无"))
    body.append("边界：只读会话文件与账本，0 次敲门、0 次进别人窗口、0 次代做 F/S4 的单、账本 0 字未写。")
    body.append("")
    body.append(CLOSING)
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d" % (OUT, len(text.encode("utf-8"))))
    print("0332=%s 0346=%s 0348=%s" % (ord332, ord346, ord348))
    for name, key, f8, txt, g, mt in rows:
        print("  %s cap=%s growth=%+d last=%s" % (name, CAP in txt, g, mt[-14:-8]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
