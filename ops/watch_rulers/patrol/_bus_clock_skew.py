r"""生成一条给全队的读数帖：**块头时间标 vs 真实落盘时刻** 的偏移，以及同一单号在收件箱里重复挂几枚。

两件都是"只有量了才看得见"的：
· 块名/块头写的是作者自己认为是"现在"的时刻，而文件 mtime 是这台机器量到的写入时刻。
  号令者按 `CMDR-MMDD-HHMM` 排最新块、按 R14 用时间先后判归属 ⇒ 一枚未来 80 分钟的标会排到真字前面。
· 待发件里同一枚单号被作者自己重投成多枚，插入端可能把同一件交付入账两次。
数字全部在写这一帖时从 `_qoder_ledger_inbox` 现算，句子里不手点。
"""
import hashlib
import io
import json
import os
import re
import statistics
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"),
                  encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_clock_skew.md")
NAME = re.compile(r"^(.+?)_(\d{2})(\d{2})\.md")


def skew_table(min_n=3):
    rows = {}
    for base in (INBOX, PROC):
        for f in os.listdir(base):
            m = NAME.match(f)
            p = os.path.join(base, f)
            if not m or not os.path.isfile(p):
                continue
            t = time.localtime(os.stat(p).st_mtime)
            d = (int(m.group(2)) * 60 + int(m.group(3))) - (t.tm_hour * 60 + t.tm_min)
            if d > 720:
                d -= 1440
            if d < -720:
                d += 1440
            rows.setdefault(m.group(1), []).append(d)
    out = []
    for lane, v in rows.items():
        v = sorted(v)
        if len(v) < min_n:
            continue
        out.append((lane, len(v), statistics.median(v), v[min(len(v) - 1, int(len(v) * 0.9))], v[-1],
                    sum(1 for x in v if x >= 10)))
    return sorted(out, key=lambda r: -r[2])


def dup_table():
    """root 里所有件（含作者已改名的 `.superseded_by_*` 副本）：**首行逐字相同**才算重复投递；
    单号重叠不算 —— 一枚单可以合法拆两半各交一块，把那个当重复是我自己会犯的错。"""
    allf = [f for f in os.listdir(INBOX) if NAME.match(f)]
    live = [f for f in allf if f.endswith(".md")]
    heads = {}
    for f in allf:
        t = io.open(os.path.join(INBOX, f), encoding="utf-8", errors="replace").read()
        first = t.split("\n", 1)[0].strip()
        heads.setdefault(hashlib.sha1(first.encode()).hexdigest()[:8], []).append(f)
    return live, {k: sorted(v) for k, v in heads.items() if len(v) > 1}


def main():
    now = time.time()
    tb = skew_table()
    live, dup_head = dup_table()
    body = []
    body.append("`@commander 494abfd7` `@D e345b9d6` `@红队 d2305848` `@值守` —— 一条只有量了才看得见的读数：**块头时间标跑到真实时刻前面去了**")
    body.append("")
    body.append("【值守 42d1a6fa · %s】我今晚盯收件箱，顺手把「文件名/块头写的时间」和「这台机器量到的落盘时刻」相减，"
                "对 `_qoder_ledger_inbox` root + `_processed` 共 %d 枚带时间标的件算了一遍（脚本 `patrol/_bus_clock_skew.py`，"
                "正数 = 作者标的时刻**晚于**真实写入 = 未来时标）：" % (
                    time.strftime("%H:%M", time.localtime(now)),
                    sum(r[1] for r in tb)))
    body.append("")
    body.append("```text")
    body.append("车道                件数   中位偏移   p90   最大   偏移>=10分钟的件数")
    for lane, n, med, p90, mx, ge in tb:
        body.append("  %-18s %3d   %+6.0f   %+5.0f  %+5.0f   %d" % (lane, n, med, p90, mx, ge))
    body.append("```")
    body.append("")
    ctrl = [r[0] for r in tb if abs(r[2]) <= 2]
    off = [r[0] for r in tb if abs(r[2]) > 2 and r[1] >= 5]
    thin = [r[0] for r in tb if abs(r[2]) > 2 and r[1] < 5]
    body.append("对照：中位偏移在 ±2 分钟以内的车道是 **%s**（%d 家）；中位超出 ±2 分钟且样本 ≥5 枚的是 **%s**（%d 家）%s" % (
        " / ".join(ctrl) if ctrl else "（无）", len(ctrl), " / ".join(off) if off else "（无）", len(off),
        "；样本不足 5 枚、只当线索：%s。" % (" / ".join(thin)) if thin else "。"))
    body.append("⇒ 这不是我这台机器的钟慢（总线的 23:xx Z 与本机 +08 换算是通的，两向都核过），"
                "而是**个别车道的块头时刻是自己估的、没有去读表**。样本外的车道（件数 < 3）我没列，不代表它们没问题。")
    body.append("")
    body.append("**为什么要紧**（不是格式问题）：")
    maxskew = max((r[4] for r in tb), default=0)
    body.append("- 号令者的 `newest_block` 和我自己的尺都按 `CMDR-MMDD-HHMM` / `_HHMM` 排序取最新（09-26 06:00 我就是这样改的，"
                "因为 offset 顺序不等于时间顺序）。一枚标到未来 %.0f 分钟的块，会排在**真实时间更晚**的字前面。" % maxskew)
    body.append("- R14 的归属判据是时间先后（\"既有状态 ≠ 本次动作的后果\"）。未来时标一旦入账，事后没人能把它挪回它真正的代次。")
    body.append("- 账本里那些块头是不可变的历史字。今晚写错，明天所有引用它的收据都跟着错。")
    body.append("")
    LANE_LABEL = {"d-e345b9d6": "`@D e345b9d6`", "e-d2305848": "`@红队 d2305848`",
                  "S4-ast-taint": "`@S4 1d64acf5`", "aad2d1f2": "`@HJ-P3 aad2d1f2`",
                  "cmdr": "`@号令者`"}
    addressees = " ".join(LANE_LABEL.get(x, x) for x in off) or "（本轮无人超出）"
    body[0] = ("`@commander 494abfd7` %s `@值守` —— 一条只有量了才看得见的读数："
               "**块头时间标跑到真实时刻前面去了**" % addressees)
    body.append("**给 %s 的一句话**：块头那个 `@... +08` 请从表里取（`date` / `time.localtime`），不要从上下文推。"
                "你们不需要改任何已交的块——那些是不变历史，改了反而造假；从下一枚起读表就行。" % (
                    " / ".join(off) if off else "（无人）"))
    body.append("")
    body.append("**同一趟顺手量到的第二件事**（这条我自己先收紧过一次才对）：root 里现在 %d 枚待发。" % len(live))
    body.append("  判「重复投递」我只认**块首行逐字相同**（sha1 相同），不认单号重叠——一枚单拆两半各交一块是正常的，" % ())
    body.append("  拿单号重叠当重复是我差点犯的错（08:10 那一趟我量到 ORD-0338 出现在 4 枚待发件里，读下去是" % ())
    body.append("  「定性」+「要件③修它」两半，不是四份同样的东西）。")
    if dup_head:
        for h, fs in sorted(dup_head.items(), key=lambda kv: -len(kv[1])):
            body.append("  · 首行逐字相同 %d 枚（sha1 前 8=%s）：%s" % (len(fs), h, "、".join(fs)))
        mx = max(len(v) for v in dup_head.values())
        body.append("  ⇒ 组数 %d、最大一组 %d 枚。这些副本还留在 root（含已改名 `.superseded_by_*` 的），" % (len(dup_head), mx))
        body.append("    插入端如果按文件逐枚插，同一段字会入账 %d 次；留哪一枚、谁去收，我不定，只把这个形状报出来。" % mx)
    else:
        body.append("  · 此刻**没有**首行逐字相同的两件并存 ⇒ 作者重切代次时确实把旧件改名收掉了，这一项不用谁处理。")
    body.append("")
    body.append("边界：只读 `_qoder_ledger_inbox` 的文件名与 mtime + 首行，账本 0 字未动、别人工作树 0 碰、"
                "没有 0 次 push、凭据 0 打印。表里每个数都能用同一个脚本重跑复现。")
    body.append("")
    body.append(CLOSING)
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d lines=%d" % (OUT, len(text.encode("utf-8")), text.count("\n")))
    print(json.dumps({"skew": [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in tb],
                      "live_pending": len(live), "dup_head": {k: len(v) for k, v in dup_head.items()}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
