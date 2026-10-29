"""Write ledger block #375: the fifth instrument fault, this one in the ruler that polices the others.

The census that re-reads this session's own landed blocks selected its rows by "mtime date == today", so
after midnight it counted one block and still closed the sheet green.  The block carries the control
receipt (old ruler, new ruler, and the new ruler narrowed back until it refuses) rather than a promise,
and reads every coordinate - including the old generation's filter line, pulled out of git - live.
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
GOZERO = "trial/results/20261026_gozero"
BW301 = GOZERO + "/bw301-this-sessions-blocks-landed.txt"
BW339 = GOZERO + "/bw339-census-window-old-vs-new-vs-narrow.txt"
REL = "trial/human_walk/_cmdr_blocks_landed_census_r301.py"
REPORT = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"

CITES = {
    "old_tally": (BW339, "  TALLY checked=1 green="),
    "new_tally": (BW339, "  TALLY checked=44 green="),
    "refused": (BW339, "  refused, verbatim:"),
    "delta": (BW339, "TALLY old_checked="),
    "generations": (BW339, "rulers: old generation"),
    "receipt_tally": (BW301, "TALLY checked="),
    "receipt_edge": (BW301, "WINDOW_EDGE first block excluded"),
    "negative": (BW301, "NEGATIVE_CONTROL unseen title"),
    "first_stretch": (BW301, "  stretch 1:"),
    "window_def": (REL, "def session_window"),
    "stretches_def": (REL, "def stretches"),
    "edge_print": (REL, 'out.append("WINDOW_EDGE first block excluded'),
    "section": (REPORT, "14.40 补（10-30 凌晨）"),
    "prev_section": (REPORT, "14.39 补（10-30 零点）"),
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
    return read(rel).split("\n")[line - 1]


def numbers(line):
    found = dict((key, int(value)) for key, value in re.findall(r"(checked|green|red|rc|delta|old_checked"
                                                                 r"|new_checked)=(\d+)", line))
    if not found:
        raise SystemExit("ABORT no machine numbers on %r" % line[:60])
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    old_sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD~1"],
                             capture_output=True, text=True, check=True).stdout.strip()
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    for obj in (old_sha, sha):
        kind = subprocess.run(["git", "-C", ROOT, "cat-file", "-t", obj], capture_output=True, text=True,
                              check=True).stdout.strip()
        if kind != "commit":
            raise SystemExit("ABORT cited object %s is %s, not a commit" % (obj[:12], kind))

    old_source = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (old_sha, REL)],
                                capture_output=True, text=True, encoding="utf-8", check=True).stdout
    filter_hits = [index + 1 for index, cell in enumerate(old_source.split("\n"))
                   if "stamp != today" in cell]
    if len(filter_hits) != 1:
        raise SystemExit("ABORT the old generation holds the day filter %d times" % len(filter_hits))
    old_line = filter_hits[0]

    old = numbers(row_at(BW339, at["old_tally"]))
    new = numbers(row_at(BW339, at["new_tally"]))
    delta = numbers(row_at(BW339, at["delta"]))
    shipped = numbers(row_at(BW301, at["receipt_tally"]))
    stretches = len([cell for cell in read(BW301).split("\n") if cell.startswith("  stretch ")])
    refused_line = row_at(BW339, at["refused"])
    if not (old["checked"] < new["checked"] == shipped["checked"] == delta["new_checked"]):
        raise SystemExit("ABORT the counts disagree: old %d new %d shipped %d control %d"
                         % (old["checked"], new["checked"], shipped["checked"], delta["new_checked"]))
    if delta["delta"] != new["checked"] - old["checked"]:
        raise SystemExit("ABORT the control's own delta does not match its two counts")
    if shipped["red"] or new["rc"]:
        raise SystemExit("ABORT the fixed sheet is not clean, so this block would be describing "
                         "a different run")
    if "sits a day away" not in refused_line:
        raise SystemExit("ABORT the narrow-window refusal line does not carry the wording quoted here")
    print("LIVE NUMBERS old=%s new=%s shipped=%s delta=%s stretches=%d old_line=%d"
          % (old, new, shipped, delta, stretches, old_line))

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
        "rel": REL, "old_line": old_line, "old_sha": old_sha[:10], "bw339": BW339, "bw301": BW301,
        "at_old_tally": at["old_tally"], "at_new_tally": at["new_tally"], "at_delta": at["delta"],
        "at_refused": at["refused"], "at_generations": at["generations"],
        "at_receipt_tally": at["receipt_tally"], "at_receipt_edge": at["receipt_edge"],
        "at_negative": at["negative"], "at_first_stretch": at["first_stretch"],
        "at_window_def": at["window_def"], "at_stretches_def": at["stretches_def"],
        "at_edge_print": at["edge_print"], "at_section": at["section"], "at_prev": at["prev_section"],
        "old_checked": old["checked"], "old_green": old["green"], "new_checked": new["checked"],
        "gap": delta["delta"], "stretches": stretches, "sha": sha, "closing": closing,
    }
    body = "\n".join([
        "### 494abfd7 交「管落地的普查自己跨零点数不到全」这第五处量具错的对照与改法（本块接前两格）",
        "",
        "- 错在哪一行：尺 %(rel)s 的上一代（git 对象 %(old_sha)s）第 %(old_line)d 行是 "
        "`if stamp != today: continue`——按「归档件修改日 == 今天」取数。时钟过零点后它只看得到新那天的归档件。"
        "同一进程里重放那代尺，读数落盘在 trial/results/20261026_gozero/%(bw339)s:%(at_old_tally)d："
        "checked=%(old_checked)d green=%(old_green)d red=0 rc=0——数到 %(old_checked)d 枚仍收绿，"
        "且整张表里没有一行说自己丢了什么。",
        "- 为什么值得单独落账：本班前四处量具错都在读产品源码那侧，这处在「复核我自己交过的东西」那侧。"
        "落地复算这类读数若取数窗口错了，绿灯比红牌更贵——它会把「已经入账」变成未经复核的话。",
        "- 改法与三道自证：窗口换成今天加前一天（%(rel)s:%(at_window_def)d 的 session_window）；窗口内按停顿"
        "切成 %(stretches)d 段逐段落表（%(rel)s:%(at_stretches_def)d，段首见 trial/results/20261026_gozero/"
        "%(bw301)s:%(at_first_stretch)d 起），真歇过的地方要看得见；打印被排除的第一枚及其秒级时刻"
        "（%(rel)s:%(at_edge_print)d，落地行 trial/results/20261026_gozero/%(bw301)s:%(at_receipt_edge)d）；"
        "空窗与「边界切在班中」两形直接 ABORT。纯间隙阈值先试过，它把本班从五小时半的休息处切成两半——"
        "休息不是换班，所以否了。",
        "- 修后现读：同一份归档、同一本账本，尺从数到 %(old_checked)d 枚变成数到 %(new_checked)d 枚，"
        "差值 %(gap)d 记在 trial/results/20261026_gozero/%(bw339)s:%(at_delta)d；出厂回执 "
        "trial/results/20261026_gozero/%(bw301)s:%(at_receipt_tally)d 为 checked=%(new_checked)d 全绿；"
        "负对照（一张从未投过的标题）仍判红（同文件 :%(at_negative)d）；把 DAYS_BACK 强设回 0 复现旧口径，"
        "尺自己拒答（原话 trial/results/20261026_gozero/%(bw339)s:%(at_refused)d）；空账本自检仍答"
        "「仪表故障」码而不是「活丢了」。",
        "- 该说没工件的地方：零点左右那回的原始打印件已被修后回执覆盖，本机只剩会话流水。本块不引它，"
        "只引同一进程重放旧尺的读数（trial/results/20261026_gozero/%(bw339)s:%(at_old_tally)d），"
        "两代尺的 git 对象列在同文件 :%(at_generations)d 且都可 cat-file 取回。",
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(at_section)d；上一节在 "
        "trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(at_prev)d；本批工件的提交代次为 git 对象 %(sha)s。"
        "本班 0 改产品字节、0 点击。",
        "",
        "%(closing)s",
        "",
    ]) % slots

    def check(text):
        if not text.startswith("### "):
            raise SystemExit("ABORT the block does not open with a heading")
        if closing not in text:
            raise SystemExit("ABORT the closing line did not land")
        if "\r\n" in text:
            raise SystemExit("ABORT the inbox block must stay LF-only")
        if "%(" in text:
            raise SystemExit("ABORT an unfilled slot survived into the block")
        if "未执行" in text or "TODO" in text:
            raise SystemExit("ABORT the block carries a placeholder instead of a reading")
        for pointer in ("GO_FROM_BLANK_REPORT.md:%d" % at["section"],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["prev_section"],
                        "bw301-this-sessions-blocks-landed.txt:%d" % at["receipt_tally"],
                        "bw301-this-sessions-blocks-landed.txt:%d" % at["receipt_edge"],
                        "bw339-census-window-old-vs-new-vs-narrow.txt:%d" % at["old_tally"],
                        "bw339-census-window-old-vs-new-vs-narrow.txt:%d" % at["delta"],
                        "%s:%d" % (REL, at["window_def"]),
                        "%s:%d" % (REL, at["edge_print"])):
            if pointer not in text:
                raise SystemExit("ABORT the live pointer %r is not in the block" % pointer)
        if sha not in text:
            raise SystemExit("ABORT the generation object did not land in the block")

    check(body)
    ledger = read_ledger()
    hits = ledger.count("管落地的普查自己跨零点数不到全")
    if hits:
        raise SystemExit("ABORT a block with this heading is already in the ledger %d times" % hits)
    pending = [name for name in os.listdir(INBOX) if name.endswith(".md") and not name.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if back != body:
        raise SystemExit("ABORT the block on disk is not the text that passed the checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


def read_ledger():
    return io.open(LEDGER, encoding="utf-8", errors="replace").read()


if __name__ == "__main__":
    sys.exit(main())
