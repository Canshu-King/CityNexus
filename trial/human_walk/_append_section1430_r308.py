"""Append section 14.30: the traveller-facing short list, and the ruler that must agree with its parent.

Every coordinate is re-read from the artifact while this appender runs; a missing or non-unique anchor
aborts instead of writing a number that cannot be retrieved.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"
BW302 = GOZERO + "/bw302-which-surface-says-it-in-english.txt"

CITES = {
    "same_source": (BW307, "SAME-SOURCE CHECK"),
    "traveller_path": (BW307, "on a traveller path"),
    "jargon": (BW307, "carrying internal vocabulary"),
    "identifier": (BW307, "carrying a bare identifier slot"),
    "bw302_split": (BW302, "ENGLISH SENTENCES 330 split by surface"),
    "collect": ("trial/human_walk/_cmdr_surface_of_english_refusals_r302.py", "def collect"),
    "score": ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", "def score"),
    "start_raise": ("backend/app/main.py", "is not authoritative: {start_authority_blocker}"),
    "select_raise": ("backend/app/main.py", "is not authoritative: {authority_blocker}"),
    "top_row": (BW307, "backend/app/main.py:20046"),
    "key_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.28 补（10-29 午）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.29 补（10-29 午后）"),
}


def line_of(rel, needle):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    hits = [index + 1 for index, row in enumerate(
        io.open(path, encoding="utf-8", errors="replace").read().split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def number_at(rel, line, pattern):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    row = io.open(path, encoding="utf-8", errors="replace").read().split("\n")[line - 1]
    found = re.findall(pattern, row)
    if not found:
        raise SystemExit("ABORT line %d of %s has no number matching %s" % (line, rel, pattern))
    return int(found[-1])


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)
    counts = {
        "reachable": number_at(BW307, at["same_source"], r"= (\d+)"),
        "traveller_path": number_at(BW307, at["traveller_path"], r": (\d+)"),
        "jargon": number_at(BW307, at["jargon"], r": (\d+)"),
        "identifier": number_at(BW307, at["identifier"], r": (\d+)"),
    }
    print("LIVE COUNTS %s" % counts)
    if not (counts["traveller_path"] <= counts["reachable"]):
        raise SystemExit("ABORT the shapes row exceeds the published denominator")

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.30 补" in text:
        print("ABORT the section is already appended")
        return 4

    c = counts
    block = "\n".join([
        "14.30 补（10-29 午后）：把 221 处排了序——屏上最丑的头几条与它们的形状分母",
        "",
        "- 排序尺 %s:%d 不复打口径：它 import §14.29 那把尺抽出来的 %s:%d 走同一份 collect()，"
        "对不上已发布的 221 就 ABORT 不出表（现读为 %d 处、与回执 %s:%d 一字不差）。"
        % ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", at["score"],
           "trial/human_walk/_cmdr_surface_of_english_refusals_r302.py", at["collect"],
           c["reachable"], BW307, at["same_source"]),
        "- 形状分母（回执 %s）：221 处里落在旅客路径（/journeys、/plans、/trips、/travellers）的 %d 处"
        "（:%d），带内部词汇的 %d 处（:%d），带裸 id 槽的 %d 处（:%d）。"
        % (BW307, c["traveller_path"], at["traveller_path"], c["jargon"], at["jargon"],
           c["identifier"], at["identifier"]),
        "- 排在最前的一条就在出发口：POST /api/v1/journeys/{journey_id}/start 拒绝时端给屏上的是 "
        "`PlanVersion {plan.id} is not authoritative: {start_authority_blocker}`"
        "（回执表首行 %s:%d，该 raise 的模板串在 backend/app/main.py:%d）"
        "——类名、裸 id、内部码三样同屏。选用口 "
        "POST /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select 是同一条模板的另一半，"
        "在 backend/app/main.py:%d。"
        % (BW307, at["top_row"], at["start_raise"], at["select_raise"]),
        "- 待裁两刀：甲，这 %d 处带内部词汇与 %d 处带裸 id 的，"
        "是否统一改成「点名地点＋人话＋不端 id」那一形制（本节前半给的是全量分母）；"
        "乙，是否顺手给它们配各自具名键（不配就仍按状态码拼键，中文接不上 —— "
        "那一条已在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d 记过，此处不另开目）。"
        % (c["jargon"], c["identifier"], at["key_section"]),
        "- 本班 0 改产品字节；上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。"
        % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.30 补")
    print("APPENDED bytes_added=%d heading_hits=%d" % (len(block.encode("utf-8")), hits))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
