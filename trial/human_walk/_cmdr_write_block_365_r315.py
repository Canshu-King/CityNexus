"""Write the #365 ledger block: the traveller-facing workload, row by row.

The rows are parsed out of bw313 while this generator runs and each figure is re-derived from that same
artifact, so the block cannot cite a row the ruler did not publish or a bucket the parents moved.
"""

import io
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
GOZERO = "trial/results/20261026_gozero"
BW313 = GOZERO + "/bw313-traveller-side-and-internal-vocabulary.txt"
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"
BW310 = GOZERO + "/bw310-internal-vocabulary-by-word.txt"

CITES = {
    "same_source": (BW313, "SAME-SOURCE CHECK route-reachable"),
    "intersection": (BW313, "INTERSECTION the job"),
    "rest": (BW313, "WHERE THE REST SITS"),
    "case": (BW313, "CASE SENSITIVITY"),
    "counting": (BW313, "COUNTING_RULE"),
    "control": (BW313, "NAMED CONTROL"),
    "ruler": ("trial/human_walk/_cmdr_smallest_fix_set_r313.py", "def published"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.32 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.31 补（10-29 午后）"),
    "bw307_shapes": (BW307, "carrying internal vocabulary"),
    "bw310_case": (BW310, "CASE SENSITIVITY"),
}

HEAD_ROW = re.compile(r"^\s*(\d+)\.\s+(\S+):(\d+)\s+terms=(.*)\s*$")


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


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def numbers(rel, line, count):
    found = [int(value) for value in re.findall(r"\d+", row_at(rel, line))]
    if len(found) != count:
        raise SystemExit("ABORT line %d of %s reads %s, expected %d numbers"
                         % (line, rel, found, count))
    return found


def listed_rows(rel):
    lines = read(rel).split("\n")
    rows = []
    for index, line in enumerate(lines):
        head = HEAD_ROW.match(line)
        if not head:
            continue
        route = lines[index + 1].split("route:", 1)
        screen = lines[index + 2].split("screen:", 1)
        if len(route) < 2 or len(screen) < 2:
            raise SystemExit("ABORT receipt row %s has an unexpected shape" % head.group(1))
        rows.append({"rank": int(head.group(1)), "file": head.group(2), "line": int(head.group(3)),
                     "terms": head.group(4), "route": route[1].strip(),
                     "screen": screen[1].strip()})
    if not rows:
        raise SystemExit("ABORT the receipt published no rows")
    if rows[0]["rank"] != 1:
        raise SystemExit("ABORT the row list does not start at one")
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    reachable, traveller, jargon = numbers(BW313, at["same_source"], 3)
    intersection = numbers(BW313, at["intersection"], 1)[0]
    outside = numbers(BW313, at["rest"], 1)[0]
    case_intersection, case_delta, current_intersection, case_parent = numbers(BW313, at["case"], 4)
    if current_intersection != intersection:
        raise SystemExit("ABORT the case row states the intersection as %d, not %d"
                         % (current_intersection, intersection))
    parent_bucket = numbers(BW307, at["bw307_shapes"], 1)[0]
    parent_case = re.search(r"published (\d+) .* would put (\d+) sentences in the bucket \((\d+) more",
                            row_at(BW310, at["bw310_case"]))
    if not parent_case:
        raise SystemExit("ABORT the bw310 case row does not read as expected")
    parent_now, parent_ci, parent_delta = [int(v) for v in parent_case.groups()]
    if parent_now != jargon:
        raise SystemExit("ABORT bw310 states the parent bucket as %d, not %d" % (parent_now, jargon))
    rows = listed_rows(BW313)
    print("LIVE NUMBERS reachable=%d traveller=%d jargon=%d intersection=%d outside=%d rows=%d"
          % (reachable, traveller, jargon, intersection, outside, len(rows)))
    if jargon != parent_bucket:
        raise SystemExit("ABORT bw313 sees jargon %d but bw307 published %d" % (jargon, parent_bucket))
    if intersection + outside != jargon:
        raise SystemExit("ABORT %d + %d does not reconcile with %d" % (intersection, outside, jargon))
    if len(rows) != intersection:
        raise SystemExit("ABORT the receipt lists %d rows but publishes an intersection of %d"
                         % (len(rows), intersection))

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("ABORT HEAD is not a forty-character object")
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha],
                      capture_output=True, text=True, check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    closing = io.open(os.path.join(REF, "live_checks", "CLOSING_LINE.txt"),
                      encoding="utf-8").read().strip()
    if not closing or "\n" in closing:
        raise SystemExit("ABORT the closing line is unusable")

    listing = ["　%d｜%s:%d 路由 `%s` 端给屏上的是「%s」——术语 %s"
               % (item["rank"], item["file"], item["line"], item["route"], item["screen"],
                  item["terms"]) for item in rows]

    now = datetime.now(timezone.utc).astimezone()
    base = now.hour * 60 + now.minute
    out = None
    for offset in range(0, 180):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out = candidate
            break
    if out is None:
        raise SystemExit("ABORT no free inbox name in the next three hours")

    body = "\n".join([
        "### 494abfd7 交「旅客面 ∩ 内部词汇」= %d 处的逐枚清单（#365，接 §14.32）" % intersection,
        "",
        "- 前两节各数各的：§14.30 报 %d 处（旅客路径），§14.31 报 %d 处（内部词汇），"
        "要改文案的人真正要的是「既在旅客面上、又端出内部词汇」那一部分。"
        "尺 trial/human_walk/_cmdr_smallest_fix_set_r313.py:%d 复用同一份 collect() 与同一份旅客面判定，"
        "三枚读数与父回执现读一致：%d / %d / %d（回执 %s:%d、父回执 %s:%d）。"
        % (traveller, jargon, at["ruler"], reachable, traveller, jargon,
           BW313, at["same_source"], BW307, at["bw307_shapes"]),
        "- 交集 %d 处，另有 %d 处落在非旅客面（Agent 或管理面），%d + %d = %d 对账闭合；"
        "行身份取 (文件, 行)，模块级 helper 按自己那枚 raise 计、不替它编 URL（回执 :%d、:%d、:%d）。"
        % (intersection, outside, intersection, outside, jargon,
           at["intersection"], at["rest"], at["counting"]),
        "- 下面 %d 行整串由回执解析，不是手抄：" % len(rows),
    ] + listing + [
        "- 这一格同样带口径（先自己说清）：%d 处是大小写敏感的读法，同一词表改成不区分大小写会把交集撑到 "
        "%d 处（多 %d 处，回执 %s:%d）；父桶也从 %d 处撑到 %d 处（多 %d 处，回执 %s:%d）。"
        "所以「就 %d 处」在当前口径内成立。"
        % (intersection, case_intersection, case_delta, BW313, at["case"],
           parent_now, parent_ci, parent_delta, BW310, at["bw310_case"], intersection),
        "- 待裁三档（不代裁）：甲一，只动这 %d 处；甲二，动 %d 处全桶（含 Agent 面）；"
        "甲三，动 %d 处旅客面全量（含不带内部词汇的那些）。乙（给 raise 配各自具名键）三档都要。"
        "本班 0 改产品字节。" % (intersection, jargon, traveller),
        "- 具名对照：回执 :%d 那一行同时验过第一枚既在旅客面又带词表术语。" % at["control"],
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。"
        % (at["section"], at["prev_section"], sha),
        "",
        closing,
        "",
    ])

    pending = [f for f in os.listdir(INBOX) if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if not back.startswith("### "):
        raise SystemExit("ABORT the block does not open with a heading")
    if closing not in back:
        raise SystemExit("ABORT the closing line did not land")
    if "\r\n" in back:
        raise SystemExit("ABORT the inbox block must stay LF-only")
    if back.count("路由 `") != len(rows):
        raise SystemExit("ABORT not every parsed row made it into the block")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
