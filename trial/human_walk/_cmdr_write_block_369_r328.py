"""Write the #369 ledger block: whether the traveller-facing English can reach the screen at all.

Rows and totals are parsed from the bw325 and bw326 receipts while this runs and reconciled inside each
receipt (verdicts against rows, reads plus hides against the catch count), so the block cannot say a number
its own artifacts do not carry.  Every listing line carries a file:line coordinate because the coordinate
gate will not accept a number that rests on a bare file name.
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
BW325 = GOZERO + "/bw325-what-the-screen-says.txt"
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"

CITES = {
    "tally_325": (BW325, "TALLY shows_server_text="),
    "split_325": (BW325, "MOUNTED_SPLIT of the"),
    "controls_325": (BW325, "CONTROLS"),
    "counting_325": (BW325, "COUNTING_RULE"),
    "coverage_325": (BW325, "COVERAGE_LIMIT"),
    "denom_326": (BW326, "DENOMINATOR the registry imports"),
    "tally_326": (BW326, "TALLY panels="),
    "site_326": (BW326, "READS_THE_REFUSAL_AT"),
    "drops_326": (BW326, "READS_BUT_DROPS"),
    "wide_326": (BW326, "WIDE_PATTERN_CHECK"),
    "nocatch_326": (BW326, "NO_CATCH_AT_ALL"),
    "coverage_326": (BW326, "COVERAGE_LIMIT"),
    "hook_site": ("frontend/src/app/V8Experience.tsx", "useCandidateRejections(data.journey.id"),
    "ruler_325": ("trial/human_walk/_cmdr_screen_text_r325.py", "def classify_first"),
    "ruler_326": ("trial/human_walk/_cmdr_panel_habit_r326.py", "def bodies"),
    "own_words": ("frontend/src/features/execution/LiveRecovery.tsx", "无法记录这个选择"),
    "shell_throw": ("frontend/src/app/V8Experience.tsx", "rejectionReason(body, response.status)"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.35 补（10-29 夜）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.34 补（10-29 午后）"),
}

ROW325 = re.compile(r"^\s*(\d+)\.\s+(\S+)\s+站 `(\S+?):(\d+)`（bw322 判 (\w+)）→ (\w+)；调用处 (\S+?):(\d+)"
                    r"，接住处 (\S+?):(\d+)；那句起手 (.*)$")
FILE_ROW = re.compile(r"^\s{2}(frontend/\S+)\s+catch (\d+) 处，读服务端原文 (\d+) 处，吞掉 (\d+) 处")

VERDICT_CN = {"SHOWS_SERVER_TEXT": "显服务端原文",
              "OWNS_ITSOWN_TEXT": "面板自造句子",
              "NO_CATCH_IN_WINDOW": "窗内无 catch"}


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


def parsed_325():
    rows = []
    for index, cell in enumerate(read(BW325).split("\n")):
        match = ROW325.match(cell)
        if match:
            rows.append({"rank": int(match.group(1)), "url": match.group(2), "site": match.group(3),
                         "site_line": int(match.group(4)), "panel": match.group(5),
                         "verdict": match.group(6), "call": match.group(7),
                         "call_line": int(match.group(8)), "caught": match.group(9),
                         "caught_line": int(match.group(10)), "receipt_line": index + 1})
    if not rows:
        raise SystemExit("ABORT bw325 published no parseable rows")
    return rows


def parsed_326():
    rows = []
    for index, cell in enumerate(read(BW326).split("\n")):
        match = FILE_ROW.match(cell)
        if match:
            rows.append({"rel": match.group(1), "catch": int(match.group(2)),
                         "reads": int(match.group(3)), "hides": int(match.group(4)),
                         "receipt_line": index + 1})
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    shows, owns, nocatch, rows_published = [int(v) for v in
                                            re.findall(r"=(\d+)", row_at(BW325, at["tally_325"]))]
    if shows + owns + nocatch != rows_published:
        raise SystemExit("ABORT bw325 verdicts do not cover its rows")
    rows = parsed_325()
    if len(rows) != rows_published:
        raise SystemExit("ABORT parsed %d bw325 rows against a published %d"
                         % (len(rows), rows_published))
    counted = {key: sum(1 for item in rows if item["verdict"] == key) for key in VERDICT_CN}
    if (counted["SHOWS_SERVER_TEXT"], counted["OWNS_ITSOWN_TEXT"],
            counted["NO_CATCH_IN_WINDOW"]) != (shows, owns, nocatch):
        raise SystemExit("ABORT the parsed verdicts disagree with the TALLY: %s" % counted)

    panels, caught, reads, hides = [int(v) for v in re.findall(r"=(\d+)", row_at(BW326, at["tally_326"]))]
    if reads + hides != caught:
        raise SystemExit("ABORT bw326 reads %d plus hides %d is not catch %d" % (reads, hides, caught))
    panel_rows = parsed_326()
    if len(panel_rows) != panels or sum(item["catch"] for item in panel_rows) != caught:
        raise SystemExit("ABORT bw326's per-file table (%d files, %d catches) disagrees with its TALLY "
                         "(%d panels, %d catches)"
                         % (len(panel_rows), sum(item["catch"] for item in panel_rows), panels, caught))
    if sum(item["reads"] for item in panel_rows) != reads:
        raise SystemExit("ABORT the per-file reads do not add up to the TALLY")
    wide = int(re.search(r"read the refusal (\d+) time", row_at(BW326, at["wide_326"])).group(1))
    if wide != reads:
        raise SystemExit("ABORT the loose pattern (%d) disagrees with the strict pattern (%d)"
                         % (wide, reads))
    shape = re.search(r"imports (\d+) module\(s\), (\d+) of them rendered",
                      row_at(BW326, at["denom_326"]))
    if not shape:
        raise SystemExit("ABORT the bw326 denominator line does not read as import and rendered counts")
    imported, mounted_read = [int(value) for value in shape.groups()]
    if mounted_read != panels:
        raise SystemExit("ABORT the denominator reads %d rendered panels against a TALLY of %d"
                         % (mounted_read, panels))
    no_catch_files = int(re.search(r"NO_CATCH_AT_ALL (\d+) of the",
                                   row_at(BW326, at["nocatch_326"])).group(1))
    tells = re.findall(r"the body says at `([^`]+?):(\d+)`", row_at(BW326, at["drops_326"]))
    if not tells:
        raise SystemExit("ABORT the READS_BUT_DROPS line names no coordinate")
    drop_file, drop_line = tells[0][0], int(tells[0][1])
    busiest = max(panel_rows, key=lambda item: item["catch"])
    print("LIVE NUMBERS rows=%d shows=%d owns=%d nocatch=%d | panels=%d catch=%d reads=%d hides=%d "
          "no_catch_files=%d busiest=%s" % (rows_published, shows, owns, nocatch, panels, caught, reads,
                                            hides, no_catch_files, busiest["rel"]))

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

    listing = []
    for item in rows:
        listing.append("　%d｜`%s` → %s；拼串处 `%s:%d`；调用处 `%s:%d`；接住处 `%s:%d`（回执 %s:%d）"
                       % (item["rank"], item["url"], VERDICT_CN[item["verdict"]], item["site"],
                          item["site_line"], item["call"], item["call_line"], item["caught"],
                          item["caught_line"], BW325, item["receipt_line"]))
    table = []
    for item in sorted(panel_rows, key=lambda cell: -cell["catch"])[:5]:
        table.append("　`%s`：catch %d 处，读原文 %d 处，不碰 error %d 处（回执 %s:%d）"
                     % (item["rel"], item["catch"], item["reads"], item["hides"], BW326,
                        item["receipt_line"]))

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

    body = "\n".join([
        "### 494abfd7 交「旅客面英文拒绝句到不了屏：面板层把话换掉了」的逐枚读数（#369，接 §14.35）",
        "",
        "- 尺 trial/human_walk/_cmdr_screen_text_r325.py:%d 按请求回答，尺 "
        "trial/human_walk/_cmdr_panel_habit_r326.py:%d 按文件回答（把注册表 import 且渲染的模块整读）。"
        "这一腿问的是 §14.34 之后剩下的最后一环：面板会发这句请求，不等于屏上显这句英文——中间那层是 catch。"
        % (at["ruler_325"], at["ruler_326"]),
        "- 按请求的读数（回执 %s:%d）：%d 行里 %d 处由面板自造句子、%d 处窗内没有 catch、%d 处显服务端原文。"
        "单看挂在面板上那批也是同一形状（回执 %s:%d）。"
        % (BW325, at["tally_325"], rows_published, owns, nocatch, shows, BW325, at["split_325"]),
        "- 按面板的读数（回执 %s:%d）：%d 枚面板共 %d 处 catch，读 error 的 %d 处、从不碰 error 的 %d 处；"
        "另有 %d 枚面板整个文件没 catch（回执 %s:%d）。分母同源（回执 %s:%d）：import %d 枚、渲染其中 %d 枚。"
        % (BW326, at["tally_326"], panels, caught, reads, hides, no_catch_files, BW326, at["nocatch_326"],
           BW326, at["denom_326"], imported, mounted_read),
        "- catch 最多的五枚面板逐枚点名（整表 %d 行自回执 %s:%d 起）：\n%s"
        % (len(panel_rows), BW326, min(item["receipt_line"] for item in panel_rows), "\n".join(table)),
        "- 唯一读 error 的那处也不上屏：它读 `cause.message`，同一文件 `%s:%d` 的注释自己写明匹配的是机器码、"
        "句子是被丢掉的（回执 %s:%d 写成 READS_BUT_DROPS，坐标现读自该行）。"
        % (drop_file, drop_line, BW326, at["drops_326"]),
        "- 这数不是我挑正则挑出来的：把判据放宽成 `.message`/`.detail`/`instanceof Error` 或 `V8Rejection`/"
        "`String(err)`/`as Error).message`，命中数仍 %d，与严格判据同数（回执 %s:%d）。三枚控制点全部取自源码"
        "本身（回执 %s:%d）：一处真读 error、一处整文件无 catch、一处明知故写自己的句子；任一不合尺就 ABORT。"
        % (reads, BW326, at["wide_326"], BW325, at["controls_325"]),
        "- 自报三处我自己先量错、后来改对的（不是私下改口，都留在这次提交里）：窗口起点开在「URL 写在哪一行」，"
        "而那行多半在 frontend/src/api/ 里、后面没有调用方的 catch，于是 %d 行误报「窗内无 catch」；"
        "pass-through 控制点瞄在一行已位于 catch 内部的位置，把尺自己 ABORT 成 rc=7；"
        "bw326 分母一度写成「渲染 25 中的 33 枚」，33 是文件里 JSX 组件名的数、比模块数宽。"
        "现规则写在回执 %s:%d。" % (nocatch, BW325, at["counting_325"]),
        "- 下面 %d 行整串由回执解析、非手抄，每行自带拼串处、调用处与接住处坐标：" % len(rows),
    ] + listing + [
        "- 这把尺不能说的那句（不替它补）：接住不等于显示——读了 error 又丢掉的也算「读」；拒绝若在共用 hook "
        "或应用壳抛出路径（frontend/src/app/V8Experience.tsx:%d 把 `body.detail` 装进抛出消息）里被处理，"
        "本尺不记在那枚面板头上。极限写在回执 %s:%d 与 %s:%d。"
        % (at["shell_throw"], BW325, at["coverage_325"], BW326, at["coverage_326"]),
        "- 这条改动「先动哪一侧」的算式，请点单（不代裁）：§14.30–§14.32 那批旅客面英文拒绝句，在本班量到的 "
        "%d 条调用路上没有一条已知能到屏。今天在这些路上可证的是另一件缺陷——面板不论服务端说了什么都答同一句"
        "（frontend/src/features/execution/LiveRecovery.tsx:%d 的「无法记录这个选择，请刷新后重试」），"
        "把拒绝理由整条吞掉；另有 %d 行是渲染期 hook，失败时连句子都没有、只剩空列表"
        "（frontend/src/app/V8Experience.tsx:%d 的 `data ?? []`）。"
        "甲＝按这批 catch 开「点名阻塞者与可点操作」的单（读侧已逐枚具名，可直接派）；"
        "乙＝仍按 §14.32 三档先动后端文案，屏读不变；"
        "丙＝两批同点。本班 0 改产品字节。" % (rows_published, at["own_words"], nocatch, at["hook_site"]),
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
    if back.count("｜`") != len(rows):
        raise SystemExit("ABORT not every parsed row made it into the block")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
