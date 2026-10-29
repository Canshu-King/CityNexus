"""Write ledger block #374: where each read server field actually goes, thirteen handler by handler.

#373 corrected a count; this block answers the question §14.38 promised to answer - reading a server field is
not showing a server sentence - and carries the second, smaller correction that came with the fourth ruler
fault (the block-comment handler that inflated the denominator). Rows are parsed from the bw338 receipt while
this runs and reconciled against its TALLY, against bw326's denominator, and against the bw327/bw328 counts
that #373 published, so a block that quietly describes a different population is impossible.
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
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"
BW328 = GOZERO + "/bw328-is-that-sentence-on-screen.txt"
BW337 = GOZERO + "/bw337-which-chinese-sentence-sits-on-which-refusal.txt"
BW338 = GOZERO + "/bw338-where-a-read-field-actually-goes.txt"
KEPT = ".before_catch_body_fix"

CITES = {
    "same_source": (BW338, "SAME-SOURCE CHECK bodies read here"),
    "tally": (BW338, "TALLY bodies="),
    "controls": (BW338, "text reaches state"),
    "provenance": (BW338, "API_MESSAGE_PROVENANCE"),
    "counting": (BW338, "COUNTING_RULE"),
    "coverage": (BW338, "COVERAGE_LIMIT"),
    "tally_326": (BW326, "TALLY panels="),
    "tally_327": (BW327, "TALLY catch="),
    "tally_328": (BW328, "TALLY rows="),
    "tally_337": (BW337, "TALLY refusals="),
    "ruler": ("trial/human_walk/_cmdr_field_destination_r340.py", "def api_message_recipe"),
    "cutter": ("trial/human_walk/_cmdr_screen_text_r325.py", "def comment_spans"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.39 补（10-30 零点）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.38 补（10-29 深夜）"),
}

ROW = re.compile(r"^\s{2}(\S+?):(\d+)\s+交进 setter 的字段 (.+?)\s+比较行 (\d+) 条\s+该 body 首枚字面量「(.*)」$")
BUCKET_HEAD = re.compile(r"^(\w+) = (\d+)$")


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
            raise SystemExit("ABORT %s carries no %s=" % (rel, key))
        out[key] = int(match.group(1))
    return out


def parsed_rows():
    rows, bucket = [], None
    for index, cell in enumerate(read(BW338).split("\n")):
        head = BUCKET_HEAD.match(cell)
        if head:
            bucket = head.group(1)
            continue
        match = ROW.match(cell)
        if not match:
            continue
        if bucket is None:
            raise SystemExit("ABORT a row appeared before any bucket heading in bw338")
        rows.append({"rel": match.group(1), "line": int(match.group(2)), "field": match.group(3),
                     "compared": int(match.group(4)), "literal": match.group(5), "bucket": bucket,
                     "receipt_line": index + 1})
    if not rows:
        raise SystemExit("ABORT bw338 published no parseable rows")
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    tally = keys(BW338, "TALLY bodies=", ("bodies", "hands_server_text_to_state",
                                          "hands_server_structure_to_state", "compares_only",
                                          "reads_and_leaves_it_unused", "never_reads_a_server_field"))
    rows = parsed_rows()
    listed = tally["hands_server_text_to_state"] + tally["hands_server_structure_to_state"] \
        + tally["compares_only"] + tally["reads_and_leaves_it_unused"]
    old_326 = keys(BW326 + KEPT, "TALLY panels=", ("catch", "reads_the_refusal", "hides_the_refusal"))
    new_326 = keys(BW326, "TALLY panels=", ("catch", "reads_the_refusal", "hides_the_refusal"))
    new_327 = keys(BW327, "TALLY catch=", ("catch", "says_zh"))
    new_328 = keys(BW328, "TALLY rows=", ("rows", "rendered"))
    line_337 = row_at(BW337, at["tally_337"])
    refusals = int(re.search(r"TALLY refusals=(\d+)", line_337).group(1))
    paired_listed = int(re.search(r"listed self-written sentence=(\d+)", line_337).group(1))
    provenance = row_at(BW338, at["provenance"])
    throw = re.search(r"throws at `([^`]+):(\d+)` with its message assembled as: (.*?) - which", provenance)
    counts = re.search(r"of the (\d+) bodies that hand a text field to state, (\d+) sit in a try", provenance)
    print("LIVE NUMBERS tally=%s rows=%d listed=%d old326=%s new326=%s new327=%s new328=%s"
          % (tally, len(rows), listed, old_326, new_326, new_327, new_328))

    if not (tally["bodies"] == new_326["catch"] == new_327["catch"]):
        raise SystemExit("ABORT the three rulers no longer share a denominator: %d / %d / %d"
                         % (tally["bodies"], new_326["catch"], new_327["catch"]))
    if sum(tally[key] for key in ("hands_server_text_to_state", "hands_server_structure_to_state",
                                  "compares_only", "reads_and_leaves_it_unused",
                                  "never_reads_a_server_field")) != tally["bodies"]:
        raise SystemExit("ABORT bw338's buckets do not cover its own bodies")
    if len(rows) != listed:
        raise SystemExit("ABORT parsed %d rows but the buckets list %d" % (len(rows), listed))
    if new_327["says_zh"] != new_328["rows"] != 26:
        raise SystemExit("ABORT the count #373 published no longer holds: %d / %d"
                         % (new_327["says_zh"], new_328["rows"]))
    if new_326["catch"] >= old_326["catch"] or new_326["reads_the_refusal"] > tally["bodies"]:
        raise SystemExit("ABORT the comment fix readings do not line up")
    if not (throw and counts):
        raise SystemExit("ABORT the provenance line in bw338 does not carry its throw site and its counts")
    if int(counts.group(1)) != tally["hands_server_text_to_state"]:
        raise SystemExit("ABORT the provenance line and the TALLY disagree about the text bucket")

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

    labels = {"HANDS_SERVER_TEXT_TO_STATE": "交文本",
              "HANDS_SERVER_STRUCTURE_TO_STATE": "交结构",
              "COMPARES_ONLY": "只比对",
              "READS_AND_LEAVES_IT_UNUSED": "读了不用"}
    listing = ["　%d｜`%s:%d` %s｜setter 里出现的字段 %s｜比较行 %s 条｜该 body 首枚字面量「%s」（回执 %s:%d）"
               % (index + 1, item["rel"], item["line"], labels[item["bucket"]], item["field"],
                  item["compared"], item["literal"], BW338, item["receipt_line"])
               for index, item in enumerate(rows)]

    body = "\n".join([
        "### 494abfd7 交「读到的字段各去了哪」的逐枚靶面：十三处 handler 四档归置，并补一次次轴改口（本块接前两格勘误）",
        "",
        "- 为什么还有这一腿：§14.38 应下「读字段不等于显句子，另开一尺分档」。尺 "
        "trial/human_walk/_cmdr_field_destination_r340.py:%d 现读：字段分文本（detail/message/quote/statusText）"
        "与结构（facts/envelope/body/code/status/data/errors）两组，认一次派生名（`const detail = body?.detail ?? …` "
        "这种写法），再看 setter 的实参与比较行。" % at["ruler"],
        "- 次轴改口（不改主句）：第四处量具错是「catch 正则扫到文档注释里的 `catch {`」——RecoveryRequiredPanel.tsx "
        "的头顶注释自己就引了一段旧写法。切刀补了块注释状态机（trial/human_walk/_cmdr_screen_text_r325.py:%d），"
        "挂载面板分母因此 %d 处→%d 处、读到拒绝句 %d 处→%d 处（回执 trial/results/20261026_gozero/%s:%d 对同目录 "
        "%s 留底）；面板自造中文句仍 %d 处、被标记读到仍 %d 处（回执 trial/results/20261026_gozero/%s:%d 与 "
        "trial/results/20261026_gozero/%s:%d），故上一块「十九→廿六」照旧成立。两次修复之间的中间读数已无工件可查，"
        "本块不引。"
        % (at["cutter"], old_326["catch"], new_326["catch"], old_326["reads_the_refusal"],
           new_326["reads_the_refusal"], BW326, at["tally_326"], KEPT, new_327["says_zh"],
           new_328["rendered"], BW327, at["tally_327"], BW328, at["tally_328"]),
        "- 分母同代对账：回执 %s:%d 与 bw326/bw327 的 catch 数同为 %d；五档相加等于该数（文本 %d＋结构 %d＋"
        "只比对 %d＋读了不用 %d＋没读 %d）。"
        % (BW338, at["tally"], tally["bodies"], tally["hands_server_text_to_state"],
           tally["hands_server_structure_to_state"], tally["compares_only"],
           tally["reads_and_leaves_it_unused"], tally["never_reads_a_server_field"]),
        "- 判别力：三枚从源码取的控制各落不同档（回执 %s:%d 起三行）——DestinationPreparationPanel 那处判交文本、"
        "RealCityDiscoveryPanel 那处判只交结构（它的注释自己写明「匹配的是机器码、丢的是句子」）、LiveRecovery 那处 "
        "`} catch {` 无绑定判没读；任一落进源码不认可的档，尺就 ABORT。" % (BW338, at["controls"]),
        "- 出处是追来的，不是假设的：交文本那 %d 处，其 try 文本里点名的都是 api 层调用（现读 %s/%s），而 api 层在 "
        "%s:%s 抛错时把 message 拼成「%s」。所以这四格里旅客看到的既不是服务端的拒绝句、也不是一句能看懂的话，"
        "是本机拼的诊断串——这是第四档，不在 §14.32 的三档里。"
        % (tally["hands_server_text_to_state"], counts.group(2), counts.group(1),
           throw.group(1), throw.group(2), re.sub(r"\s+", " ", throw.group(3)).strip()),
        "- 下面 %d 行整串由回执解析、非手抄，每行自带 catch 坐标、被交出的字段、比较行数与该 body 的首枚字面量："
        % len(rows),
    ] + listing + [
        "- 这把尺不能说的那句（不替它补）：provenance 只证明该 catch 的 try 文本里出现了 api 层调用名，不证明那次 "
        "message 一定由 api 层那行拼装而来（同一 try 里若有本地 throw 就走别的路径）；要钉死得真按一次把这四格逼到屏上。"
        "它也不看 JSX 插值（归 bw328）、不追跨组件的 prop。极限写在回执 %s:%d，判据写在 %s:%d。"
        % (BW338, at["coverage"], BW338, at["counting"]),
        "- 待裁（不代裁，四档并列）：甲＝改这 %d 处自造句子的 catch（靶面逐枚在回执 "
        "trial/results/20261026_gozero/%s:%d 所列各行）；乙＝按 §14.32 三档先改后端那 %d 句英文（屏读不变——回执 "
        "trial/results/20261026_gozero/%s:%d 量到 %d 条拒绝里只有 %d 条与面板句子配得上）；丙＝甲乙同点；"
        "丁＝先把交文本那 %d 处内部诊断串换成人话（这一档不依赖甲乙的取舍，也不动契约）。本班 0 改产品字节。"
        % (new_327["says_zh"], BW327, at["tally_327"], refusals, BW337, at["tally_337"], refusals,
           paired_listed, tally["hands_server_text_to_state"]),
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；上一节在 "
        "trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；本批工件的提交代次为 git 对象 %s，"
        "可 git cat-file -t 取回。" % (at["section"], at["prev_section"], sha),
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
        if text.count("｜`") != len(rows):
            raise SystemExit("ABORT not every parsed row made it into the block")
        for pointer in ("GO_FROM_BLANK_REPORT.md:%d" % at["section"],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["prev_section"],
                        "bw338-where-a-read-field-actually-goes.txt:%d" % at["tally"],
                        "bw326-what-the-panels-do-with-a-refusal.txt:%d" % at["tally_326"],
                        "bw327-what-the-panels-say-instead.txt:%d" % at["tally_327"],
                        "bw328-is-that-sentence-on-screen.txt:%d" % at["tally_328"],
                        "%s:%s" % (throw.group(1), throw.group(2))):
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
    print("WROTE %s bytes=%d rows=%d" % (out, len(body.encode("utf-8")), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
