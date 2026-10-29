"""Write the #367 ledger block: the re-count, and the false alarm I caused while fixing a gate.

Figures are re-read from the census receipt and its selftest receipt while this runs; the green count
must equal the tally, the tally must cover every checked block, and the instrument-fault sentinel must
have been proven to bite, or the block aborts rather than asserting a clean sheet.
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
BW301 = GOZERO + "/bw301-this-sessions-blocks-landed.txt"
SELFTEST = "trial/human_walk/_bw301_selftest.txt"
CENSUS = "trial/human_walk/_cmdr_blocks_landed_census_r301.py"
GATE = "trial/human_walk/_cmdr_ledger_landing_check_r300.py"

CITES = {
    "tally": (BW301, "TALLY checked="),
    "fault_line": (BW301, "INSTRUMENT_FAULT no"),
    "negative": (BW301, "NEGATIVE_CONTROL"),
    "selftest": (SELFTEST, "SELFTEST_OK"),
    "gate_tuple": (GATE, "return 0 if green else 7, hinted"),
    "census_unpack": (CENSUS, "rc, _hinted = gate.check(heading)"),
    "census_bogus_unpack": (CENSUS, "bogus_rc, _bogus_hinted = gate.check(bogus)"),
    "census_fault": (CENSUS, "INSTRUMENT_FAULT %s"),
    "census_return": (CENSUS, "return 8 if fault else"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.33 补（10-29 午后）"),
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


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def green_count(rel):
    lines = read(rel).split("\n")
    return sum(1 for line in lines if line.strip().startswith("gate: GREEN"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)
    checked, green, red = [int(v) for v in re.findall(r"=(\d+)", row_at(BW301, at["tally"]))]
    fault_shown = int(re.findall(r"(\d+) of", row_at(BW301, at["fault_line"]))[0])
    counted_green = green_count(BW301)
    archived = [int(v) for v in re.findall(r"\d+", row_at(SELFTEST, at["selftest"]))]
    bitten = next((value for value in archived if value > checked), None)
    print("LIVE NUMBERS checked=%d green=%d red=%d counted=%d archived_in_selftest=%s"
          % (checked, green, red, counted_green, bitten))
    if green != counted_green:
        raise SystemExit("ABORT the tally says %d green but %d rows read gate: GREEN"
                         % (green, counted_green))
    if green + red != checked:
        raise SystemExit("ABORT the tally %d+%d does not cover %d" % (green, red, checked))
    if fault_shown != red:
        raise SystemExit("ABORT the fault line states %d red, the tally states %d"
                         % (fault_shown, red))
    if bitten is None:
        raise SystemExit("ABORT the selftest receipt does not show a wider archive sweep")

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

    now = datetime.now(timezone.utc).astimezone()
    base = now.hour * 60 + now.minute
    out_path = None
    for offset in range(0, 180):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out_path = candidate
            break
    if out_path is None:
        raise SystemExit("ABORT no free inbox name in the next three hours")

    body = "\n".join([
        "### 494abfd7 复算「本班报过的 %d 笔插入」账账相符 %d/%d，并自报一格我自己造成的假红灯（#367）"
        % (checked, green, checked),
        "",
        "- 假红灯先认：上一格我把落地门 trial/human_walk/_cmdr_ledger_landing_check_r300.py:%d 的 "
        "check() 从「返回一个退出码」改成「返回（退出码，是否给了候选提示）」，"
        "只跑了门自己的 --selftest 与一次真 --title 命令，没同拍 grep 调用点——"
        "复算尺 trial/human_walk/_cmdr_blocks_landed_census_r301.py 有两处在拿返回值与 0 比，"
        "元组永不等于 0，于是把 %d 枚其实都在账上的块全报成丢失。"
        "两处解包现已对齐（尺 :%d、:%d）。"
        % (at["gate_tuple"], checked, at["census_unpack"], at["census_bogus_unpack"]),
        "- 复算读数（回执 %s:%d 的 TALLY 那一行现读）：账账相符 %d 笔、%d 笔 GREEN、%d 笔 RED，"
        "逐行数出的 gate: GREEN 也是 %d 行，两把尺一致；"
        "负控仍会咬：一枚从未发布的标题读 RED（同回执 :%d）。"
        % (BW301, at["tally"], checked, green, red, counted_green, at["negative"]),
        "- 机制这一格装进门里，不靠我记得：整表同时全红被单独定性为仪器故障而非丢工"
        "（尺 :%d 的哨兵、:%d 的第三退出码），"
        "--selftest 用「把账本换成一个空文件」复现该形状：%d 枚归档全红时尺答 8 而不报「丢了 %d 枚」"
        "（回执 %s:%d）。"
        % (at["census_fault"], at["census_return"], bitten, bitten, SELFTEST, at["selftest"]),
        "- 这条对主上的意义：本班此前所有「INSERTED」的复算仍成立（%d/%d 在账），"
        "但任何一把尺整表翻红时，先按 :%d 那行的第三方读数复核再动手重插——"
        "我这一班次就差点按一张假清单去重插 %d 枚已在账的块。本班 0 改产品字节。"
        % (green, checked, at["fault_line"], checked),
        "- 落点与代次：正文最后一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。" % (at["section"], sha),
        "",
        closing,
        "",
    ])

    pending = [f for f in os.listdir(INBOX) if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out_path, encoding="utf-8").read()
    if not back.startswith("### "):
        raise SystemExit("ABORT the block does not open with a heading")
    if closing not in back:
        raise SystemExit("ABORT the closing line did not land")
    if "\r\n" in back:
        raise SystemExit("ABORT the inbox block must stay LF-only")
    print("WROTE %s bytes=%d" % (out_path, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
