"""Append section 14.32: the sentence-level intersection, which is the actual size of the job.

Anchors and numbers are re-read from bw313 while this appender runs; each figure is taken by position in
its own line, and the two parent buckets are re-read from bw307 so the section cannot cite a number that
a published ruler no longer agrees with.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW313 = GOZERO + "/bw313-traveller-side-and-internal-vocabulary.txt"
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"

CITES = {
    "same_source": (BW313, "SAME-SOURCE CHECK route-reachable"),
    "intersection": (BW313, "INTERSECTION the job"),
    "first_row": (BW313, "1. backend/app/main.py:1932"),
    "rest": (BW313, "WHERE THE REST SITS"),
    "case": (BW313, "CASE SENSITIVITY"),
    "counting": (BW313, "COUNTING_RULE"),
    "control": (BW313, "NAMED CONTROL"),
    "score": ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", "def score"),
    "collect": ("trial/human_walk/_cmdr_surface_of_english_refusals_r302.py", "def collect"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.31 补（10-29 午后）"),
    "bw307_shapes": (BW307, "carrying internal vocabulary"),
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


def numbers(rel, line, count):
    found = [int(value) for value in re.findall(r"\d+", read(rel).split("\n")[line - 1])]
    if len(found) != count:
        raise SystemExit("ABORT line %d of %s reads %s, expected %d numbers"
                         % (line, rel, found, count))
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)
    reachable, traveller, jargon = numbers(BW313, at["same_source"], 3)
    intersection = numbers(BW313, at["intersection"], 1)[0]
    outside = numbers(BW313, at["rest"], 1)[0]
    case_intersection, case_delta, case_bucket, case_parent = numbers(BW313, at["case"], 4)
    parent_bucket = numbers(BW307, at["bw307_shapes"], 1)[0]
    first_rank, first_line = numbers(BW313, at["first_row"], 2)
    if first_rank != 1:
        raise SystemExit("ABORT the first listed row is ranked %d, not one" % first_rank)
    print("LIVE NUMBERS reachable=%d traveller=%d jargon=%d intersection=%d outside=%d"
          % (reachable, traveller, jargon, intersection, outside))
    if jargon != parent_bucket:
        raise SystemExit("ABORT bw313 sees jargon %d but bw307 published %d" % (jargon, parent_bucket))
    if intersection + outside != jargon:
        raise SystemExit("ABORT %d + %d does not reconcile with the bucket %d"
                         % (intersection, outside, jargon))
    if not (intersection <= min(traveller, jargon)):
        raise SystemExit("ABORT the intersection exceeds one of its parents")

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.32 补" in text:
        print("ABORT the section is already appended")
        return 4

    block = "\n".join([
        "14.32 补（10-29 午后）：真正要动的最小集是 %d 处——旅客面 ∩ 内部词汇的句子级交集" % intersection,
        "",
        "- 为什么前两节都不够用：§14.30 报 %d 处（旅客路径），§14.31 报 %d 处（内部词汇），"
        "两把尺各按各的口径数句子，逐词相加还会把同一句数两次。要改文案的人需要的是「既在旅客面上、"
        "又端出内部词汇」那一部分。尺 trial/human_walk/_cmdr_smallest_fix_set_r313.py 复用同一份 "
        "collect()（trial/human_walk/_cmdr_surface_of_english_refusals_r302.py:%d）与同一份旅客面判定"
        "（trial/human_walk/_cmdr_what_traveller_reads_r307.py:%d），三枚同源读数现读一致："
        "%d / %d / %d（回执 %s:%d，父回执 %s:%d）。"
        % (traveller, jargon, at["collect"], at["score"], reachable, traveller, jargon,
           BW313, at["same_source"], BW307, at["bw307_shapes"]),
        "- 交集 %d 处，另有 %d 处内部词汇落在非旅客面（Agent 或管理面），%d + %d = %d 对账闭合"
        "（回执 :%d、:%d）。行身份取 (文件, 行)，模块级 helper 按自己那枚 raise 计、不替它编 URL"
        "（回执 :%d）。逐枚清单在 %s:%d 起，第一枚是 backend/app/main.py:%d"
        "（回执具名对照 :%d 同时证明它落在旅客面且带词表术语）。"
        % (intersection, outside, intersection, outside, jargon, at["intersection"], at["rest"],
           at["counting"], BW313, at["first_row"], first_line, at["control"]),
        "- 这一格也带口径（与 §14.31 同一毛病，先自己说清）：%d 是大小写敏感的读法，"
        "同一词表改成不区分大小写会把交集撑到 %d 处（多 %d 处）——回执 :%d。"
        "所以「就 %d 处」这句话在当前口径内成立。"
        % (intersection, case_intersection, case_delta, at["case"], intersection),
        "- 待裁（并入 §14.31 那两刀，不另开新目）：甲的可选面现在有了第三档——只动这 %d 处、"
        "动 %d 处全桶、或动 %d 处旅客面全量；乙不受影响。本班 0 改产品字节。"
        % (intersection, jargon, traveller),
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.32 补")
    print("APPENDED bytes_added=%d heading_hits=%d" % (len(block.encode("utf-8")), hits))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
