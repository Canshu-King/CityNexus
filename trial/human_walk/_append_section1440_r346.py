"""Append section 14.40: the fifth instrument fault of this shift, in the census that polices the others.

The landed-block census picked its rows by "mtime date == today", so the first minute after midnight it
re-read one of the blocks this shift reported as INSERTED and still closed the sheet green. Every number
here is read out of bw339 and bw301 while this runs, including the old ruler's own filter line, which is
taken out of the parent commit with git show so the defect can be pointed at rather than described.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = os.path.join(ROOT, "trial", "results", "20261026_gozero")
BW301 = "bw301-this-sessions-blocks-landed.txt"
BW339 = "bw339-census-window-old-vs-new-vs-narrow.txt"
REL = "trial/human_walk/_cmdr_blocks_landed_census_r301.py"

CITES = {
    "old_tally": (BW339, "  TALLY checked=1 green="),
    "new_tally": (BW339, "  TALLY checked=44 green="),
    "refused": (BW339, "  refused, verbatim:"),
    "delta": (BW339, "TALLY old_checked="),
    "proves": (BW339, "WHAT THIS PROVES"),
    "old_head": (BW339, "rulers: old generation"),
    "receipt_tally": (BW301, "TALLY checked="),
    "receipt_edge": (BW301, "WINDOW_EDGE first block excluded"),
    "window_def": (REL, "def session_window"),
    "stretches_def": (REL, "def stretches"),
    "edge_print": (REL, 'out.append("WINDOW_EDGE first block excluded'),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.39 补（10-30 零点）"),
}


def read(rel):
    base = GOZERO if rel.startswith("bw") else ROOT
    path = os.path.join(base, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, cell in enumerate(read(rel).split("\n")) if needle in cell]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD~1"],
                         capture_output=True, text=True, check=True).stdout.strip()
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    old_source = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (sha, REL)],
                                capture_output=True, text=True, encoding="utf-8",
                                check=True).stdout.split("\n")
    filter_hits = [index + 1 for index, cell in enumerate(old_source) if "stamp != today" in cell]
    if len(filter_hits) != 1:
        raise SystemExit("ABORT the parent copy of the ruler holds the day filter %d times, not once"
                         % len(filter_hits))
    old_line = filter_hits[0]
    print("OLD FILTER LINE %s:%d in generation %s" % (REL, old_line, sha[:10]))

    old = dict((k, int(v)) for k, v in re.findall(r"(checked|green|red|rc)=(\d+)",
                                                  row_at(BW339, at["old_tally"])))
    new = dict((k, int(v)) for k, v in re.findall(r"(checked|green|red|rc)=(\d+)",
                                                  row_at(BW339, at["new_tally"])))
    delta = dict((k, int(v)) for k, v in re.findall(r"(old_checked|new_checked|delta)=(\d+)",
                                                    row_at(BW339, at["delta"])))
    receipt = dict((k, int(v)) for k, v in re.findall(r"(checked|green|red)=(\d+)",
                                                      row_at(BW301, at["receipt_tally"])))
    stretches = len(re.findall(r"^  stretch \d+:", read(BW301), re.M))
    edge = row_at(BW301, at["receipt_edge"])
    refused = row_at(BW339, at["refused"])
    rulers = row_at(BW339, at["old_head"])
    if not (old["checked"] == delta["old_checked"] and new["checked"] == delta["new_checked"]
            and delta["delta"] == new["checked"] - old["checked"]):
        raise SystemExit("ABORT bw339 does not agree with itself: %s / %s / %s" % (old, new, delta))
    if receipt["checked"] != new["checked"] or receipt["red"] != new["red"]:
        raise SystemExit("ABORT the shipped receipt reads %s while the control reads %s"
                         % (receipt, new))
    if not (old["red"] == 0 and old["rc"] == 0 and new["red"] == 0 and new["rc"] == 0):
        raise SystemExit("ABORT one of the two sheets is not the shape being described")
    print("LIVE NUMBERS old=%s new=%s receipt=%s stretches=%d delta=%s"
          % (old, new, receipt, stretches, delta))

    text = read("trial/results/20261026_GO_FROM_BLANK_REPORT.md")
    if "14.40 补" in text:
        return 4
    slots = {
        "old_sha": sha[:10], "old_line": old_line, "bw339": BW339, "bw301": BW301,
        "old_tally": at["old_tally"], "new_tally": at["new_tally"], "refused": at["refused"],
        "delta": at["delta"], "old_head": at["old_head"], "receipt_tally": at["receipt_tally"],
        "receipt_edge": at["receipt_edge"], "window_def": at["window_def"],
        "stretches_def": at["stretches_def"], "edge_print": at["edge_print"],
        "prev_section": at["prev_section"], "ruler": REL, "stretches": stretches,
        "old_checked": old["checked"], "old_green": old["green"], "old_red": old["red"],
        "old_rc": old["rc"], "new_checked": new["checked"], "new_green": new["green"],
        "new_red": new["red"], "new_rc": new["rc"], "gap": delta["delta"],
        "receipt_checked": receipt["checked"], "receipt_green": receipt["green"],
        "receipt_red": receipt["red"],
    }
    section = "\n".join([
        "",
        "### 14.40 补（10-30 凌晨）：第五处量具错——管别人落地的普查自己跨零点就瞎了",
        "",
        "- 错在哪一行：尺 %(ruler)s 的上一代（git 对象 %(old_sha)s）第 %(old_line)d 行写的是 "
        "`if stamp != today: continue`，取数按「归档文件修改日 == 今天」。00:14 落了最后一格之后时钟进了新的一天，"
        "于是这把尺只看得到 10-30 的归档件。对照回执 trial/results/20261026_gozero/%(bw339)s:%(old_tally)d "
        "现读同一进程里的重放：旧尺 checked=%(old_checked)d green=%(old_green)d red=%(old_red)d rc=%(old_rc)d"
        "——它数到 %(old_checked)d 枚仍把表收尾成「零枚红」，且整张表里没有一行说自己丢了什么。",
        "- 为什么这是第五处而不是第一处：前四处（切刀、字面量、注释里的 catch、坐标漂移）都在「读产品源码」那侧，"
        "这一处在「复核我自己交过的东西」那侧。同一夜我拿它证明过落账复算，那类读数的取数窗口若错了，"
        "绿灯只会比红牌更贵。",
        "- 怎么改的：窗口换成「今天＋前一天」（%(ruler)s:%(window_def)d 的 session_window），并加三道自证："
        "%(ruler)s:%(stretches_def)d 起把窗口内按停顿切成 %(stretches)d 段逐段落表（真歇过的地方要看得见，"
        "不能装作一直在跑）；%(ruler)s:%(edge_print)d 起打印被排除的第一枚归档件与其秒级时刻（现读 "
        "trial/results/20261026_gozero/%(bw301)s:%(receipt_edge)d）；空窗与「边界切在班中」两种情形直接 ABORT。"
        "先试过纯间隙阈值（相邻两块相隔过久即断），它把本班从五小时半的休息处切成两半——那是休息不是换班，所以否了。",
        "- 修后现读：同一份归档、同一本账本、同一进程，尺从数到 %(old_checked)d 枚变成数到 %(new_checked)d 枚"
        "（trial/results/20261026_gozero/%(bw339)s:%(delta)d 那行记 %(new_checked)d-%(old_checked)d=%(gap)d）；"
        "出厂回执 trial/results/20261026_gozero/%(bw301)s:%(receipt_tally)d 为 checked=%(receipt_checked)d "
        "green=%(receipt_green)d red=%(receipt_red)d。负对照（一张从未投过的标题）仍判红，空账本自检仍答"
        "「仪表故障」码而不是「活丢了」。",
        "- 新尺把旧形状关在门外：把 DAYS_BACK 强设回 0（即旧口径）再跑，尺自己拒绝出表，原话见 trial/results/"
        "20261026_gozero/%(bw339)s:%(refused)d 那一行——「窗口外那一枚距窗口内最老一枚只隔一天，这看起来是把一个班"
        "切成了两半」。这条拒绝本身就是对照：同一份数据，旧尺静默数 %(old_checked)d，新尺要么数全要么不作答。",
        "- 该说没工件的地方：00:1x 那一次的原始打印件已被修后回执覆盖，本机只剩会话流水可查。所以本节引的是"
        "「同一进程里重放旧尺得到 checked=%(old_checked)d」（trial/results/20261026_gozero/%(bw339)s:%(old_tally)d，"
        "两代尺的 git 对象见同文件 :%(old_head)d），不引那次已经不在的表。",
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(prev_section)d。本班 0 改产品字节、"
        "0 点击。",
        "",
    ]) % slots
    lines = section.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    section = "\n".join(lines)

    for marker in ("%(old_checked)d", "%(ruler)s"):
        if marker in section:
            raise SystemExit("ABORT the template slot %s survived into the section" % marker)
    with io.open(REPORT, "rb") as handle:
        blob = handle.read()
    crlf = blob.count(b"\r\n")
    bare = blob.count(b"\n") - crlf
    if not blob.endswith(b"\r\n"):
        blob += b"\r\n"
    payload = b"\r\n".join(cell.encode("utf-8") for cell in section.split("\n")) + b"\r\n"
    io.open(REPORT, "wb").write(blob + payload)
    back = io.open(REPORT, "rb").read()
    hits = back.count("14.40 补".encode("utf-8"))
    crlf_after = back.count(b"\r\n")
    bare_after = back.count(b"\n") - crlf_after
    print("APPENDED bytes_added=%d section_lines=%d heading_hits=%d crlf_now=%d bare_lf_now=%d"
          % (len(payload), len(section.split("\n")), hits, crlf_after, bare_after))
    if hits != 1:
        raise SystemExit("ABORT the heading is not unique")
    if crlf_after != crlf + len(section.split("\n")) or bare_after != bare:
        raise SystemExit("ABORT the line endings moved: added %d CRLF and %d bare LF"
                         % (crlf_after - crlf, bare_after - bare))
    return 0


if __name__ == "__main__":
    sys.exit(main())
