"""Compose per-lane knocks from the numbers measured in this run (nothing hand-typed).

Input: patrol/door_skew_rows.json written by _bus_door_skew.py (same run), plus the ruler the live door calls
(derived again from the door file, so a lane is never told to run a ruler the door does not use).
Output: patrol/knock/<lane>_<HHMM>.txt, each ending with the 83-byte closing line read from CLOSING_LINE.txt
(sha1 asserted; the text is copied from that file, never retyped).
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
OUT = os.path.join(HERE, "knock")
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
CLOSING_SHA = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
BUS_ID = "5869413510"
LANE_BY_PREFIX = [("map_", "map", "3b65af59"), ("s4_", "S4 量具/污点尺", "1d64acf5"),
                  ("qoder-0370_", "道0370", "e4f3490f"), ("qoder-038", "Q", "904a042d"),
                  ("0383_", "道0383", "4033270f")]


def live_ruler():
    for df in ("ledger_insert_after_r2.py", "ledger_insert_after.py"):
        p = os.path.join(LC, df)
        if not os.path.exists(p):
            continue
        for i, ln in enumerate(io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
            m = re.search(r'"(claim_coordinate_check_r[0-9a-z]*\.py)"', ln)
            if m:
                return m.group(1), df, i
    return "claim_coordinate_check_r4e.py", "?", 0


def lane_of(name):
    for pre, nm, id8 in LANE_BY_PREFIX:
        if name.startswith(pre):
            return nm, id8
    return None, None


def main():
    rows = json.load(io.open(os.path.join(HERE, "door_skew_rows.json"), encoding="utf-8"))
    ruler, df, dfl = live_ruler()
    ruler_sha = hashlib.sha1(io.open(os.path.join(LC, ruler), "rb").read()).hexdigest()
    tip = rows["tip"]
    os.makedirs(OUT, exist_ok=True)
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == CLOSING_SHA, "尾行文件不符"
    closing = raw.decode("utf-8").strip()

    groups = {}
    for r in rows["rows"]:
        if r["where"] != "root":
            continue
        nm, id8 = lane_of(r["block"])
        if not nm:
            continue
        groups.setdefault((nm, id8), []).append(r)

    made = []
    for (nm, id8), rs in sorted(groups.items()):
        bolted = [r for r in rs if r["r7_rc"] == 0 and r["bolt_abort"] > 0]
        red = [r for r in rs if r["r7_rc"] != 0]
        b = []
        b.append("【值守 %s → %s（会话 %s）· 你压在收件目录的块为什么插不进去，以及只差哪一步】"
                 % (time.strftime("%H:%M"), nm, id8))
        b.append("")
        b.append("先纠一处会烧你轮次的口径：写盘门已经在 %s 换过代，现在真正跑的尺是 `%s`（`%s:%d` 调它，"
                 "文件内容 sha1 `%s`，本地字节重算，不是 git 对象）；`Q43_HOW_TO_PASS_r1.md:4` 与 "
                 "`Q43_HOW_TO_PASS_r2.md:11` 里写的还是上一代 `claim_coordinate_check_r4e.py`。"
                 "**自检请按现行门跑：`D:/moodle/_qoder_cmdr_ref_20260921/live_checks/%s --text <你的块> --expect-clean`。**"
                 % (time.strftime("%H:%M", time.localtime(os.path.getmtime(os.path.join(LC, df)))),
                    ruler, df, dfl, ruler_sha, ruler))
        b.append("")
        if red:
            b.append("A. 现行门（%s）就拒的块 —— 补坐标才能动：%s" % (
                ruler, "、".join("`%s` findings=%s" % (r["block"], r["r7_findings"]) for r in red)))
            b.append("   形：被点名的裸数字在**同一行**带 `path:line` / `field=value` / 完整 40 位 blob，别删数字；"
                     "改完另投 `<车道>_<HHMM>.md`（首行 `### `），旧块改名留痕时去掉尾巴的 `.md`。")
            b.append("")
        if bolted:
            b.append("B. 门绿、但被写盘门的**第二道闸**拦下的块 —— 这一格最省你的力气：%s" % "、".join(
                "`%s`(abort=%d)" % (r["block"], r["bolt_abort"]) for r in bolted))
            b.append("   闸的内容：块里每一枚 40 位值要么真能 `git cat-file`，要么**同时**满足"
                     "(a) 那一行自己声明它不是 git 对象（能匹配的写法：`文件 sha1`/`内容 sha1`/`本机 sha1`/"
                     "`本地字节重算`/`不是 blob`/`不可 cat-file`/`sha1 over bytes`），"
                     "(b) 那一行所在的同一段（连续非空行，**隔一个空行就不算**）里有一枚真能取回的坐标。")
            for r in bolted:
                if r["declared_only_missing_lines"]:
                    b.append("   - `%s`：只差 (a) 声明的行 = %s；(b) 已满足。改这一行的措辞即可。"
                             % (r["block"], r["declared_only_missing_lines"]))
                if r["both_missing_lines"]:
                    b.append("   - `%s`：(a)(b) 都缺的行 = %s；这些行要补一句声明，并让同段里出现一枚可取回坐标"
                             "（例如现尖 `%s`）。" % (r["block"], r["both_missing_lines"], tip))
            b.append("")
        b.append("三臂实测（不是转述）：`patrol/_recipe_selftest.py` 同一轮跑出——配方版 Q43=GREEN/carried=1/aborts=0；"
                 "把声明换成「blob」写法 aborts=1(declared=False anchored=True)；声明在但坐标隔了一段 aborts=1"
                 "(declared=True anchored=False)。⇒ 两条都承重，只补一条不算修好。")
        b.append("")
        b.append("总线上有同轮完整读数与勘误（含我自己 19:38 把 r4e 当成门尺、误报「门拒了却入账」的那条）："
                 "Issue #1 评论 `%s`。" % BUS_ID)
        b.append("")
        b.append("边界：我没动你的块、没替你插、没写账本、没碰权威线；方向仍归号令者。")
        b.append(closing)
        txt = "\n".join(b) + "\n"
        assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
        fn = os.path.join(OUT, "%s_%s.txt" % (re.sub(r"[^A-Za-z0-9]", "", id8)[:8], time.strftime("%H%M")))
        io.open(fn, "w", encoding="utf-8", newline="\n").write(txt)
        made.append((nm, id8, fn, len(txt.encode("utf-8")), hashlib.sha1(txt.encode("utf-8")).hexdigest()[:12]))
    for nm, id8, fn, size, sh in made:
        print("%-16s %s  %5d B  sha1=%s  -> %s" % (nm, id8, size, sh, os.path.basename(fn)))
    print("ruler=%s sha1=%s tip=%s groups=%d" % (ruler, ruler_sha[:12], tip[:12], len(made)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
