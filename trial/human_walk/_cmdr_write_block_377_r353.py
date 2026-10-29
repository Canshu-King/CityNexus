"""Write ledger block #377: four arms against the coordinate door, and the order only the commander can call.

The door is not mine to change, so this block hands over the measurement and three shapes for a ruling
instead of fixing anything.  It carries the path-exists and line-in-range checks inside its own pre-write
gate, because that is the gap this probe just measured: shape is not existence.
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
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
BW341 = "trial/results/20261026_gozero/bw341-what-the-q43-door-accepts-as-a-coordinate.txt"
BW339 = "trial/results/20261026_gozero/bw339-census-window-old-vs-new-vs-narrow.txt"
BW301 = "trial/results/20261026_gozero/bw301-this-sessions-blocks-landed.txt"
BW342 = "trial/results/20261026_gozero/bw342-are-the-report-coordinates-retrievable.txt"
CENSUS = "trial/human_walk/_cmdr_report_coordinate_census_r354.py"
PROBE = "trial/human_walk/_cmdr_q43_shape_probe_r351.py"
BLOCKGEN = "trial/human_walk/_cmdr_write_block_376_r350.py"
SELF = "trial/human_walk/_cmdr_write_block_377_r353.py"
REPORT = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"

CITES = {
    "coord_tally": (BW342, "TALLY coordinates="),
    "coord_missing": (BW342, "BUCKET missing_prefix ="),
    "census_anchor": (CENSUS, "PREFIXES = "),
    "real_head": (BW341, "ARM real_path"),
    "double_head": (BW341, "ARM doubled_directory"),
    "ghost_head": (BW341, "ARM no_such_file"),
    "range_head": (BW341, "ARM line_out_of_range"),
    "read": (BW341, "READ: all"),
    "tally": (BW341, "TALLY arms="),
    "probe_arms": (PROBE, "ARMS = ("),
    "exists_gate": (BLOCKGEN, "which is not on disk"),
    "range_gate": (BLOCKGEN, "line that is not there"),
    "section": (REPORT, "14.41 补（10-30 凌晨）"),
    "prev_section": (REPORT, "14.40 补（10-30 凌晨）"),
}


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, cell in enumerate(read(rel).split("\n")) if needle in cell]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    lines = read(rel).split("\n")
    if line > len(lines):
        raise SystemExit("ABORT %s holds %d lines, so :%d names nothing" % (rel, len(lines), line))
    return lines[line - 1]


def arm_facts(heading_line):
    lines = read(BW341).split("\n")[heading_line:]
    exists = next(cell.split()[-1] for cell in lines if "path on disk here" in cell)
    verdict = next(cell.strip() for cell in lines if "door verdict" in cell)
    claims = int(re.search(r"claims=(\d+)", verdict).group(1))
    return exists, "Q43_GATE_GREEN" in verdict, claims


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    # stitched so the needle cannot match the line in this file that computes it
    at["self_gate"] = line_of(SELF, "unretrievable " + "coordinate")
    print("LIVE ANCHORS %s" % at)

    arms = dict((name, arm_facts(at[key])) for name, key in
                (("real", "real_head"), ("double", "double_head"),
                 ("ghost", "ghost_head"), ("range", "range_head")))
    tally = dict((k, int(v)) for k, v in re.findall(r"(arms|green|red)=(\d+)", row_at(BW341, at["tally"])))
    if tally["arms"] != 4 or tally["green"] != 4 or tally["red"] != 0:
        raise SystemExit("ABORT the receipt does not read as four arms green: %s" % tally)
    if not all(green for _e, green, _c in arms.values()):
        raise SystemExit("ABORT an arm did not come back green: %s" % arms)
    if arms["double"][0] != "False" or arms["ghost"][0] != "False" or arms["real"][0] != "True":
        raise SystemExit("ABORT the existence column no longer matches the shapes described: %s" % arms)
    print("LIVE ARMS %s" % arms)

    coord = dict((key, int(value)) for key, value in re.findall(
        r"(coordinates|distinct|ok|missing_prefix|out_of_range|nowhere)=(\d+)",
        row_at(BW342, at["coord_tally"])))
    if coord["coordinates"] != coord["ok"] + coord["missing_prefix"] + coord["out_of_range"] \
            + coord["nowhere"]:
        raise SystemExit("ABORT the retrievability census does not add up: %s" % coord)
    print("LIVE COORDINATES %s" % coord)

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    closing = io.open(os.path.join(REF, "live_checks", "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    if not closing or "\n" in closing:
        raise SystemExit("ABORT the closing line is unusable")

    now = datetime.now(timezone.utc).astimezone()
    base = now.hour * 60 + now.minute
    out = None
    for offset in range(0, 240):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out = candidate
            break
    if out is None:
        raise SystemExit("ABORT no free inbox name in the next four hours")

    slots = {
        "bw341": BW341, "bw339": BW339, "bw301": BW301, "probe": PROBE, "blockgen": BLOCKGEN, "self": SELF,
        "bw342": BW342, "census": CENSUS, "census_anchor": at["census_anchor"],
        "coord_tally": at["coord_tally"], "coord_missing_head": at["coord_missing"],
        "coord_total": coord["coordinates"], "coord_distinct": coord["distinct"],
        "coord_ok": coord["ok"], "coord_missing": coord["missing_prefix"],
        "coord_range": coord["out_of_range"], "coord_nowhere": coord["nowhere"],
        "real_head": at["real_head"], "double_head": at["double_head"], "ghost_head": at["ghost_head"],
        "range_head": at["range_head"], "read_line": at["read"], "tally_line": at["tally"],
        "probe_arms": at["probe_arms"], "exists_gate": at["exists_gate"], "range_gate": at["range_gate"],
        "self_gate": at["self_gate"], "section": at["section"], "prev_section": at["prev_section"],
        "sha": sha, "closing": closing, "claims_real": arms["real"][2], "claims_double": arms["double"][2],
        "claims_ghost": arms["ghost"][2], "claims_range": arms["range"][2],
        "ledger": "CITYNEXUS_AGENT_CONTROL.md",
    }
    body = "\n".join([
        "### 494abfd7 交「坐标门只认形制」的四档实测与一张三档待点单（本块接上一格）",
        "",
        "- 测法：同一句 claim 配四枚不同坐标目标，各跑一次门。四档定义写在 %(probe)s:%(probe_arms)d；"
        "逐档原判落盘在 %(bw341)s，四枚坐标各写全路径：真路径档 %(bw341)s:%(real_head)d（claims="
        "%(claims_real)d GREEN rc=0）、目录写重档 %(bw341)s:%(double_head)d（claims=%(claims_double)d GREEN "
        "rc=0，盘上实测 False）、文件不存在档 %(bw341)s:%(ghost_head)d（claims=%(claims_ghost)d GREEN rc=0，"
        "盘上实测 False）、真文件越界行档 %(bw341)s:%(range_head)d（claims=%(claims_range)d GREEN rc=0，"
        "行号在文件长度之外）。合计见 %(bw341)s:%(tally_line)d。",
        "- 结论（门自己的话在 %(bw341)s:%(read_line)d）：四档全绿。所以这道门的"
        "坐标臂判的是形制——数字挨着一个像文件名的东西就算落了锚，不问那路径在不在盘上、也不问那文件有没有那么"
        "多行。上一格里 6 枚写重目录的坐标过门时是绿的，不是门漏咬，是它本就不咬这个面。",
        "- 顺手把整份走查报告的坐标取回性扫了一遍：尺 %(census)s:%(census_anchor)d，回执 %(bw342)s:1 自报"
        " TALLY_LINE 与四项计数，现读合计行在 %(bw342)s:%(coord_tally)d——坐标 %(coord_total)d 枚、去重 "
        "%(coord_distinct)d 枚，其中 %(coord_ok)d 枚按所写路径打得开、%(coord_missing)d 枚缺前缀（把 backend/"
        "tests/… 简写成 tests/…、把 frontend/src/trial/mobile/… 简写成 trial/mobile/…，逐枚清单在 "
        "%(bw342)s:%(coord_missing_head)d 起），行号越界 %(coord_range)d 枚、路径完全不在盘上 "
        "%(coord_nowhere)d 枚。这 %(coord_missing)d 枚要不要逐枚勘误回正文，与下面甲/乙/丙同批点，本班不自取。",
        "- 我这边已守的：本班交块脚本落盘前逐枚现读，路径不在盘上就拒（%(blockgen)s:%(exists_gate)d），行号越过"
        "文件末尾就拒（%(blockgen)s:%(range_gate)d）；本块自己也走同一道闸（%(self)s:%(self_gate)d）。对照件与"
        "普查回执的逐枚表在 %(bw339)s 与 %(bw301)s:1（第 1 行自带自指锚，行号不随落块漂）。",
        "- 待点单（三档并列，不代裁，0 改门）：甲＝给坐标门加「路径须在盘上、行号须在界内」的臂——四档样本与原判"
        "都在 %(bw341)s 里，可直接复放；乙＝不加，这条留给各家生成器自查（本班已"
        "按乙执行，代价是每个车道各自装一遍）；丙＝只加「路径在盘上」不加「行号界内」，咬住写重与虚构、放过越界行。",
        "- 落点与代次：正文在 %(report)s:%(section)d，上一节在同文件 %(report)s:%(prev_section)d；本块所在提交"
        "为 git 对象 %(sha)s，可 git cat-file -t 取回。账本 %(ledger)s 现读命中本标题 0 次才落盘。"
        "本班 0 改产品字节、0 点击、0 改门。",
        "",
        "%(closing)s",
        "",
    ]) % dict(slots, report="trial/results/20261026_GO_FROM_BLANK_REPORT.md")

    def check(text):
        if not text.startswith("### "):
            raise SystemExit("ABORT the block does not open with a heading")
        if closing not in text:
            raise SystemExit("ABORT the closing line did not land")
        if "\r\n" in text:
            raise SystemExit("ABORT the inbox block must stay LF-only")
        if "%(" in text or "%d" in text or "%s" in text:
            raise SystemExit("ABORT an unformatted slot survived into the block")
        for pointer in ("%s:%d" % (BW341, at["real_head"]),
                        "%s:%d" % (BW341, at["double_head"]),
                        "%s:%d" % (BW341, at["ghost_head"]),
                        "%s:%d" % (BW341, at["range_head"]),
                        "%s:%d" % (BW341, at["read"]),
                        "%s:%d" % (PROBE, at["probe_arms"]),
                        "%s:%d" % (BLOCKGEN, at["exists_gate"]),
                        "%s:%d" % (BLOCKGEN, at["range_gate"]),
                        "%s:%d" % (SELF, at["self_gate"]),
                        "%s:1" % BW301,
                        "%s:1" % BW342,
                        "%s:%d" % (BW342, at["coord_tally"]),
                        "%s:%d" % (BW342, at["coord_missing"]),
                        "%s:%d" % (CENSUS, at["census_anchor"]),
                        "%s:%d" % (REPORT, at["section"])):
            if pointer not in text:
                raise SystemExit("ABORT the live pointer %r is not in the block" % pointer)
        if sha not in text:
            raise SystemExit("ABORT the generation object did not land in the block")
        # the gap this block measures: a shape gate accepts a coordinate whose file is not on disk, so
        # every path this block cites is re-read here before anything is written
        for path, line in re.findall(r"((?:trial|frontend|backend)/[A-Za-z0-9_./-]+\.(?:txt|md|py)):(\d+)",
                                     text):
            if not os.path.exists(os.path.join(ROOT, path.replace("/", os.sep))):
                raise SystemExit("ABORT the block cites %s, which is not on disk, so the block would ship"
                                 " an unretrievable coordinate" % path)
            if int(line) > len(read(path).split("\n")):
                raise SystemExit("ABORT %s holds %d lines, so %s:%s names nothing"
                                 % (path, len(read(path).split("\n")), path, line))

    check(body)
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    hits = ledger.count("坐标门只认形制")
    if hits:
        raise SystemExit("ABORT a block with this heading is already in the ledger %d times" % hits)
    pending = [cell for cell in os.listdir(INBOX) if cell.endswith(".md") and not cell.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if back != body:
        raise SystemExit("ABORT the block on disk is not the text that passed the checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
