"""Write ledger block #373: the correction that voids the "nineteen sites" counts in blocks #370 and #372.

Three faults in my own rulers were found while building the refusal-to-sentence pairing, and every number
this shift published off bw326/bw327/bw328 came from them. Old posts are not edited in this ledger, so the
correction is a new block, and it re-reads the two landed headings it corrects, the corrected totals from
the live receipts, and the superseded totals from the `.before_catch_body_fix` copies instead of quoting
any of them from memory. If the two sets do not reconcile, it aborts before writing anything.
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
BW325 = GOZERO + "/bw325-what-the-screen-says.txt"
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"
BW328 = GOZERO + "/bw328-is-that-sentence-on-screen.txt"
BW337 = GOZERO + "/bw337-which-chinese-sentence-sits-on-which-refusal.txt"
KEPT = ".before_catch_body_fix"

VOIDED = ["交「屏上改写成什么话」的逐枚靶面：十九处自造句子的 catch",
          "交「面板自造的话句句被标记读到」的逐枚闭链：十九处 catch 各自的 state 与渲染行"]

CITES = {
    "revision": (BW325, "CATCH_BODY_REVISION"),
    "tally_326": (BW326, "TALLY panels="),
    "tally_327": (BW327, "TALLY catch="),
    "control_327": (BW327, "LITERAL_SCANNER_CONTROL"),
    "tally_328": (BW328, "TALLY rows="),
    "tally_337": (BW337, "TALLY refusals="),
    "reverse_337": (BW337, "REVERSE_CHECK"),
    "ruler_325": ("trial/human_walk/_cmdr_screen_text_r325.py", "def catch_body"),
    "ruler_327": ("trial/human_walk/_cmdr_sentence_shape_r327.py", "def strip_comments"),
    "ruler_328": ("trial/human_walk/_cmdr_render_check_r328.py", "left these unread"),
    "ruler_337": ("trial/human_walk/_cmdr_pair_refusal_to_sentence_r337.py", "def scan_catches"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.38 补（10-29 深夜）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.37 补（10-29 夜）"),
}


def read(rel):
    base = os.path.join(ROOT, "trial", "results", "20261026_gozero") if rel.startswith("bw") else ROOT
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


def keys(rel, needle, wanted):
    line = next((cell for cell in read(rel).split("\n") if cell.startswith(needle)), "")
    if not line:
        raise SystemExit("ABORT no %r line in %s" % (needle, rel))
    out = {}
    for key in wanted:
        match = re.search(r"%s=(\d+)" % key, line)
        if not match:
            raise SystemExit("ABORT %s has no %s= on its tally line" % (rel, key))
        out[key] = int(match.group(1))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    new_327 = keys(BW327, "TALLY catch=", ("says_zh", "into_state", "nowhere", "retry_shaped"))
    old_327 = keys(BW327 + KEPT, "TALLY catch=", ("says_zh", "into_state", "nowhere", "retry_shaped"))
    new_326 = keys(BW326, "TALLY panels=", ("reads_the_refusal", "hides_the_refusal"))
    old_326 = keys(BW326 + KEPT, "TALLY panels=", ("reads_the_refusal", "hides_the_refusal"))
    new_328 = keys(BW328, "TALLY rows=", ("rows", "rendered", "no_setter_for_text"))
    old_328 = keys(BW328 + KEPT, "TALLY rows=", ("rows", "rendered", "no_setter_for_text"))
    new_337 = keys(BW337, "TALLY refusals=", ("refusals", "unpaired"))
    line = row_at(BW337, at["tally_337"])
    new_337["listed"] = int(re.search(r"listed self-written sentence=(\d+)", line).group(1))
    new_337["unlisted"] = int(re.search(r"unlisted catch sentence=(\d+)", line).group(1))
    reached, never = [int(v) for v in re.search(r"reached by this join: (\d+).*refusals: (\d+)",
                                                row_at(BW337, at["reverse_337"])).groups()]
    shape = dict((k, int(v)) for k, v in re.findall(r"(files|bodies|median|longest)=(\d+)",
                                                    row_at(BW325, at["revision"])))
    scanner = re.search(r"says_zh=(\d+) instead of (\d+)", row_at(BW327, at["control_327"]))
    scanner_site = re.search(r"is/are (\S+?:\d+)", row_at(BW327, at["control_327"])).group(1)

    print("LIVE CORRECTION old327=%s new327=%s old328=%s new328=%s old326=%s new326=%s 337=%s "
          "reached=%d never=%d shape=%s scanner=%s" % (old_327, new_327, old_328, new_328, old_326,
                                                        new_326, new_337, reached, never, shape,
                                                        scanner.groups()))
    if new_337["listed"] + new_337["unlisted"] + new_337["unpaired"] != new_337["refusals"]:
        raise SystemExit("ABORT bw337's buckets do not cover its own refusal count")
    if reached + never != new_327["says_zh"]:
        raise SystemExit("ABORT bw337's reverse check does not cover the corrected sentence set")
    if new_327["says_zh"] != new_328["rows"] or new_328["no_setter_for_text"] != 0:
        raise SystemExit("ABORT the corrected sets are not one set: bw327 %d, bw328 %d"
                         % (new_327["says_zh"], new_328["rows"]))
    if not (old_327["says_zh"] == old_328["rows"] == 19):
        raise SystemExit("ABORT the kept receipts do not carry the 19 this block is correcting")
    if scanner is None or int(scanner.group(1)) <= int(scanner.group(2)):
        raise SystemExit("ABORT the scanner control does not show a decrease")
    if int(scanner.group(1)) <= new_327["says_zh"] or int(scanner.group(2)) != new_327["says_zh"]:
        raise SystemExit("ABORT the scanner control does not end on the number this block publishes: "
                         "control says %s instead of %s, live tally %d"
                         % (scanner.group(1), scanner.group(2), new_327["says_zh"]))

    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    hits = [(heading, ledger.count(heading)) for heading in VOIDED]
    ledger_lines = []
    for heading in VOIDED:
        where = [index + 1 for index, cell in enumerate(ledger.splitlines()) if heading in cell]
        if len(where) != 1:
            raise SystemExit("ABORT the heading I am voiding sits on %d lines of the ledger" % len(where))
        ledger_lines.append(where[0])
    for heading, found in hits:
        if found != 1:
            raise SystemExit("ABORT the block I am voiding reads %d times in the ledger, not once: %s"
                             % (found, heading[:24]))

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("ABORT HEAD is not a forty-character object")
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

    body = "\n".join([
        "### 494abfd7 勘误：前两格交靶面与闭链时用的「十九处」读数作废，改口为廿六处（本块源于三把我自己的尺量错过）",
        "",
        "- 作废哪两格：标题含「%s」的那格（D:/moodle/CITYNEXUS_AGENT_CONTROL.md:%d）与标题含「%s」的那格"
        "（同账本 D:/moodle/CITYNEXUS_AGENT_CONTROL.md:%d），账本现读各命中 %s 次、各占一行。两格里的「十九处」"
        "以及正文 §14.36、§14.37 同数的读数一并作废，改口见下。旧帖不改，本块自行为证。"
        % (VOIDED[0], ledger_lines[0], VOIDED[1], ledger_lines[1], ["零", "一"][hits[0][1]]),
        "- 我错在哪（三处，都是量具不是产品）：其一，catch 体的花括号配平按整行数，而本仓写 `} catch {`，"
        "行首那个 `}` 收的是 try、整行净值成 0，于是每段 body 只收到第一条语句就返回——尺在 "
        "trial/human_walk/_cmdr_screen_text_r325.py:%d，改后现读 %d 枚 body 的中位长度 %d 行、最长 %d 行"
        "（回执 %s:%d）。其二，字符串扫描器的字符类吃换行，文档注释里一左一右两个引号被当成一枚字面量——尺在 "
        "trial/human_walk/_cmdr_sentence_shape_r327.py:%d（def strip_comments），对照就在回执 %s:%d："
        "旧口径 says_zh=%s、修后 %s，多出的那枚出自 %s。其三，回执 %s:%d 那把尺把解析不动的行直接跳过还照报 "
        "no_setter=%d——闸门现在装在 trial/human_walk/_cmdr_render_check_r328.py:%d。"
        % (at["ruler_325"], shape["bodies"], shape["median"], shape["longest"], BW325, at["revision"],
           at["ruler_327"], BW327, at["control_327"], scanner.group(1), scanner.group(2), scanner_site,
           BW328, at["tally_328"], old_328["no_setter_for_text"], at["ruler_328"]),
        "- 改口后的数（每格都从现回执重算，旧数取自同目录 %s 留底）：面板自造中文句 %d 处→%d 处（回执 %s:%d）；"
        "交给 state %d 处→%d 处、两头都不是 %d 处→%d 处、带重试句形 %d 处→%d 处（同回执 :%d）；读到拒绝句 "
        "%d 处→%d 处、藏起来 %d 处→%d 处（回执 %s:%d）；被标记读到 %d 处→%d 处、句子不在任何 setter 里仍 "
        "%d 处（回执 %s:%d）。"
        % (KEPT, old_327["says_zh"], new_327["says_zh"], BW327, at["tally_327"], old_327["into_state"],
           new_327["into_state"], old_327["nowhere"], new_327["nowhere"], old_327["retry_shaped"],
           new_327["retry_shaped"], at["tally_327"], old_326["reads_the_refusal"],
           new_326["reads_the_refusal"], old_326["hides_the_refusal"], new_326["hides_the_refusal"],
           BW326, at["tally_326"], old_328["rows"], new_328["rows"], new_328["no_setter_for_text"],
           BW328, at["tally_328"]),
        "- 顺带补上的一格（新尺 trial/human_walk/_cmdr_pair_refusal_to_sentence_r337.py:%d 的全文 catch 跨度"
        "扫描）：%d 条旅客面英文拒绝里，配得上列表内自造句的是 %d 条、只配到列表外某枚 catch 句的 %d 条、"
        "配不上任何一句的 %d 条（回执 %s:%d）；反过来 %d 枚自造句 catch 被这些拒绝走到的是 %d 枚、没走到的 "
        "%d 枚（回执 :%d）。这一格把「甲刀」「乙刀」的重叠面量清了：几乎不重叠。"
        % (at["ruler_337"], new_337["refusals"], new_337["listed"], new_337["unlisted"],
           new_337["unpaired"], BW337, at["tally_337"], new_327["says_zh"], reached, never,
           at["reverse_337"]),
        "- 这把新尺也不能说的那句（不替它补）：bw318 每条拒绝最多印三枚调用处，排第四的面板调用处会被判成"
        "「配不上」而真机上可能配得上；它全程只读源码、没有一次点击，也不判旅客当时站不站在那一屏。"
        "另欠一把尺：判「读没读拒绝」的正则只认 detail/message/response/data/statusText，而现读到的真实写法是 "
        "`cause.body as { detail?... }`、`refusalReasonCode(cause)`、`cause.facts`——读了字段不等于把那句显出来，"
        "这条我另开一尺分三档，不在勘误里顺手改判。",
        "- 落点与代次：更正后的正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d（§14.38 补）；"
        "上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；本批工件的提交代次为 git 对象 %s，"
        "可 git cat-file -t 取回。本班 0 改产品字节，改的全是我自己的尺。"
        % (at["section"], at["prev_section"], sha),
        "",
        closing,
        "",
    ])

    def check(text):
        if not text.startswith("### "):
            raise SystemExit("ABORT the block does not open with a heading")
        if closing not in text:
            raise SystemExit("ABORT the closing line did not land")
        if "\r\n" in text:
            raise SystemExit("ABORT the inbox block must stay LF-only")
        if "%d" in text or "%s" in text:
            raise SystemExit("ABORT an unformatted slot survived into the block")
        for pointer in ("CITYNEXUS_AGENT_CONTROL.md:%d" % ledger_lines[0],
                        "CITYNEXUS_AGENT_CONTROL.md:%d" % ledger_lines[1],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["section"],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["prev_section"],
                        "bw327-what-the-panels-say-instead.txt:%d" % at["tally_327"],
                        "bw328-is-that-sentence-on-screen.txt:%d" % at["tally_328"],
                        "bw337-which-chinese-sentence-sits-on-which-refusal.txt:%d" % at["tally_337"]):
            if pointer not in text:
                raise SystemExit("ABORT the live pointer %r is not in the block" % pointer)
        if sha not in text:
            raise SystemExit("ABORT the generation object did not land in the block")

    check(body)
    pending = [f for f in os.listdir(INBOX) if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if back != body:
        raise SystemExit("ABORT the block on disk is not the text that passed the checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
