"""Append section 14.36: the sentences the panels write instead, and where each one is decided.

Figures are parsed from the bw327 receipt while this runs and reconciled inside it (the three sentence axes
must sum to the catch count, and the count must equal bw326's published figure), so this section cannot
quote a number its own artifacts do not carry.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"

CITES = {
    "tally": (BW327, "TALLY catch="),
    "same_source": (BW327, "SAME-SOURCE CHECK catch bodies read here"),
    "reverse": (BW327, "REVERSE_CHECK"),
    "distinct": (BW327, "SENTENCE_DISTINCT"),
    "reused": (BW327, "MOST_REUSED"),
    "rows_head": (BW327, "SAYS_ZH_ROWS the"),
    "coverage": (BW327, "COVERAGE_LIMIT"),
    "counting": (BW327, "COUNTING_RULE"),
    "tally_326": (BW326, "TALLY panels="),
    "ruler": ("trial/human_walk/_cmdr_sentence_shape_r327.py", "def literals"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.35 补（10-29 夜）"),
}


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, row in enumerate(read(rel).split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row(rel, line):
    return read(rel).split("\n")[line - 1]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    caught, zh, en_only, nothing, shape, state, console, nowhere, retry, reads = [
        int(v) for v in re.findall(r"=(\d+)", row(BW327, at["tally"]))]
    if zh + en_only + nothing != caught:
        raise SystemExit("ABORT the sentence axes do not cover the catch count")
    if int(re.search(r"catch=(\d+)", row(BW326, at["tally_326"])).group(1)) != caught:
        raise SystemExit("ABORT bw326 and bw327 do not read the same catch population")
    reverse = [int(v) for v in re.findall(r"= (\d+)", row(BW327, at["reverse"]))]
    if reverse != [0, 0]:
        raise SystemExit("ABORT the reverse sets are not empty, so the section cannot claim one writing "
                         "style: %s" % reverse)
    distinct, occurrences = [int(v) for v in re.findall(r"(\d+)", row(BW327, at["distinct"]))][:2]
    reused = re.search(r"MOST_REUSED (\d+) 处 · (.+?)（首见", row(BW327, at["reused"]))
    if not reused:
        raise SystemExit("ABORT the MOST_REUSED line does not name a reused sentence: %r"
                         % row(BW327, at["reused"])[:120])
    reused_count, reused_text = int(reused.group(1)), reused.group(2).strip()
    listed = len([cell for cell in read(BW327).split("\n")[at["rows_head"]:at["rows_head"] + 60]
                  if re.match(r"^\s{2}\S+?:\d+\s+「", cell)])
    if listed != zh:
        raise SystemExit("ABORT the receipt lists %d per-site rows but says_zh reads %d"
                         % (listed, zh))
    print("LIVE NUMBERS catch=%d zh=%d en_only=%d nothing=%d state=%d console=%d nowhere=%d retry=%d "
          "distinct=%d occurrences=%d" % (caught, zh, en_only, nothing, state, console, nowhere, retry,
                                          distinct, occurrences))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.36 补" in text:
        print("ABORT the section is already appended")
        return 4

    block = "\n".join([
        "14.36 补（10-29 夜）：%d 处面板自己写的句子逐枚点名——不是万能句刷屏，也没有一句带得出理由"
        % zh,
        "",
        "- 这一节补的是 §14.35 之后、也是账本块 #370 指向的那段正文。尺 trial/human_walk/"
        "_cmdr_sentence_shape_r327.py:%d 读的还是 %s:%d 那同批 catch body（对账句在回执 %s:%d）。"
        % (at["ruler"], BW326, at["tally_326"], BW327, at["same_source"]),
        "- 三轴读数（回执 %s:%d）：%d 处 catch 里，说中文 %d 处、只有英文 %d 处、不带任何字面量 %d 处"
        "（三者相加＝%d）；交给组件 state %d 处、交给 console %d 处、两者都不是 %d 处；重试句形 %d 处。"
        % (BW327, at["tally"], caught, zh, en_only, nothing, caught, state, console, nowhere, retry),
        "- 「旅客-facing 的失败话只有一种写法」是量出来的：说中文的 %d 处全都带 `zh ?` 双语形，"
        "而两个反集都为 0（%d 与 %d，回执 %s:%d）——只数正集不能证同一集合，反集才证。"
        % (zh, reverse[0], reverse[1], BW327, at["reverse"]),
        "- 也不是同一句复读：%d 枚不同中文句铺在 %d 次出现上，被重复最多的一句也只落到 %d 处——「%s」"
        "（回执 %s:%d、%s:%d）。这把 §14.35 的结论磨得更利："
        "每处失败都各写了一句像样的话，而其中没有一句能带出服务端给的理由。"
        % (distinct, occurrences, reused_count, reused_text, BW327, at["distinct"], BW327, at["reused"]),
        "- 靶面已逐枚列在回执 %s:%d 起（%d 行，每行一枚 catch 坐标＋该句原文），"
        "账本块 #370 把它整表搬进账本。「这句到底点没点名被拒的那一项」我不做关键词代理——"
        "句子原文都在，请读。极限与判据写在回执 %s:%d 与 %s:%d。"
        % (BW327, at["rows_head"], listed, BW327, at["coverage"], BW327, at["counting"]),
        "- 待裁（不代裁）：#369 那三档里的甲，靶面就是上面这 %d 行（每行一枚 catch、一句话、一个坐标）。"
        "本班 0 改产品字节。" % zh,
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    bare = back.count("\n") - back.count("\r\n")
    hits = back.count("14.36 补")
    print("APPENDED bytes_added=%d heading_hits=%d bare_lf_now=%d"
          % (len(block.encode("utf-8")), hits, bare))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
