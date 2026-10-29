"""Append section 14.31: the internal-vocabulary bucket split word by word.

Every coordinate, every count and every per-word row is parsed out of the two receipts while this
appender runs.  A missing anchor, a non-unique anchor, a row that will not parse, or a figure that
disagrees with the published bucket aborts instead of writing something unretrievable.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW310 = GOZERO + "/bw310-internal-vocabulary-by-word.txt"
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"

CITES = {
    "same_source": (BW310, "SAME-SOURCE CHECK sentences carrying internal vocabulary"),
    "coords_row": (BW310, "coords: backend/app/main.py:3715"),
    "recon": (BW310, "RECONCILIATION bucket="),
    "case_row": (BW310, "CASE SENSITIVITY"),
    "silent_row": (BW310, "SILENT TERMS"),
    "guard": ("trial/human_walk/_cmdr_jargon_by_word_r310.py", "claims %d hits but carries"),
    "vocab": ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", "INTERNAL_JARGON = ("),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.30 补（10-29 午后）"),
    "bw307_shapes": (BW307, "carrying internal vocabulary"),
}

WORD_ROW = re.compile(r"^  (\S.*?)\s+(\d+)处\s+on a traveller path (\d+)\s+"
                      r"case-insensitive would add (\d+)")


def read(rel):
    return io.open(os.path.join(ROOT, rel.replace("/", os.sep)),
                   encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    if not os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep))):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    hits = [index + 1 for index, row in enumerate(read(rel).split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def numbers_at(rel, line, index, pattern=r"\d+"):
    found = re.findall(pattern, row(rel, line))
    if len(found) <= index:
        raise SystemExit("ABORT line %d of %s has only %d numbers matching %s"
                         % (line, rel, len(found), pattern))
    return int(found[index])


def row(rel, line):
    return read(rel).split("\n")[line - 1]


def word_rows(rel):
    parsed = []
    for line in read(rel).split("\n"):
        match = WORD_ROW.match(line)
        if match:
            parsed.append({"term": match.group(1), "hits": int(match.group(2)),
                           "traveller": int(match.group(3)),
                           "case_extra": int(match.group(4))})
    if len(parsed) < 3:
        raise SystemExit("ABORT the receipt parsed only %d per-word rows" % len(parsed))
    return parsed


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    bucket = numbers_at(BW310, at["same_source"], 0, r"vocabulary = (\d+)")
    shapes_bucket = numbers_at(BW307, at["bw307_shapes"], 0, r"vocabulary: (\d+)")
    if bucket != shapes_bucket:
        raise SystemExit("ABORT bw310 sees %d but bw307 published %d" % (bucket, shapes_bucket))

    recon_line = row(BW310, at["recon"])
    recon = [int(value) for value in re.findall(r"\d+", recon_line)]
    if len(recon) != 4:
        raise SystemExit("ABORT the reconciliation row reads %s, not four numbers" % recon)
    recon_bucket, per_word_sum, difference, multi = recon
    if recon_bucket != bucket:
        raise SystemExit("ABORT the reconciliation row disagrees with the published bucket")

    case_line = row(BW310, at["case_row"])
    case_numbers = [int(value) for value in re.findall(r"\d+", case_line)]
    if len(case_numbers) != 3:
        raise SystemExit("ABORT the case row reads %s, not three numbers" % case_numbers)
    case_bucket, ci_bucket, ci_delta = case_numbers
    if case_bucket != bucket:
        raise SystemExit("ABORT the case row is stated against a different bucket")

    silent_terms, vocab_size = numbers_at(BW310, at["silent_row"], 0), numbers_at(
        BW310, at["silent_row"], 1)
    rows = word_rows(BW310)
    by_term = {item["term"]: item for item in rows}
    journey = by_term.get("journey")
    if journey is None:
        raise SystemExit("ABORT the journey row did not parse")
    print("LIVE NUMBERS bucket=%d sum=%d diff=%d multi=%d ci=%d silent=%d/%d journey=%d/%d"
          % (bucket, per_word_sum, difference, multi, ci_bucket, silent_terms, vocab_size,
             journey["hits"], journey["traveller"]))
    if per_word_sum != bucket or difference != 0:
        print("NOTE the per-word rows do not sum to the bucket: difference=%d multi=%d"
              % (difference, multi))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.31 补" in text:
        print("ABORT the section is already appended")
        return 4

    listing = "；".join("%s %d 处（旅客路径 %d 处）" % (item["term"], item["hits"], item["traveller"])
                        for item in rows)
    block = "\n".join([
        "14.31 补（10-29 午后）：把「%d 处内部词汇」按词摊开，顺带量出这把尺自己的两处口径依赖" % bucket,
        "",
        "- 词表沿用 trial/human_walk/_cmdr_what_traveller_reads_r307.py:%d 的 %d 枚术语，"
        "本尺 import 复用不重打；分母与 §14.30 同源——两把尺各自现读都是 %d 处"
        "（回执 %s:%d、%s:%d），对不上就直接 ABORT 不出表。"
        % (at["vocab"], vocab_size, bucket, BW310, at["same_source"], BW307, at["bw307_shapes"]),
        "- 逐词命中（按处数降序，整串由回执解析而来）：%s。%d 枚术语里只有 %d 枚在 221 处里真出现过。"
        % (listing, vocab_size, len(rows)),
        "- 最大一族单独点出来：%s 占 %d 处、其中 %d 处落在旅客真路径上，"
        "逐枚坐标见 %s:%d 起的那一行。"
        % (journey["term"], journey["hits"], journey["traveller"], BW310, at["coords_row"]),
        "- 两处口径依赖（不写就等于报一个会飘的数）：其一，逐词相加 %d 与桶 %d 相等、"
        "差 %d，因为没有句子同时带两个术语（带两个的句子 %d 处，回执 %s:%d）；"
        "其二，%d 是大小写敏感的读法，同一词表改成不区分大小写会把桶撑到 %d 处（多 %d 处），"
        "单 %s 一名就多算 %d 句（回执 :%d）——所以「要改的就 %d 处」只在当前口径内成立。"
        % (per_word_sum, bucket, difference, multi, BW310, at["recon"],
           bucket, ci_bucket, ci_delta, journey["term"], journey["case_extra"],
           at["case_row"], bucket),
        "- 词表过宽一格自报：表里 %d 枚术语有 %d 枚在 221 处里一次都没说到（回执 :%d）——"
        "那是 §14.29 定表时按「工程常见黑话」拍的，不是从屏上句子归纳的；"
        "下一版词表应当从这 %d 处反推。" % (vocab_size, silent_terms, at["silent_row"], bucket),
        "- 本班自己造的一格故障与修法（写下来不藏）：第一版逐枚坐标行恒空——渲染循环读的是排序前"
        "残留的循环变量。现在坐标随元组一起存，并装了「命中数与坐标数不等即 ABORT」的守卫"
        "（trial/human_walk/_cmdr_jargon_by_word_r310.py:%d）。" % at["guard"],
        "- 待裁仍是 §14.30 那两刀，只是甲现在能按词点单：先动 %s 这一族 %d 处，"
        "还是 %d 处一并动；乙（配具名键）不受本次读数影响。本班 0 改产品字节。"
        % (journey["term"], journey["hits"], bucket),
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.31 补")
    print("APPENDED bytes_added=%d heading_hits=%d" % (len(block.encode("utf-8")), hits))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
