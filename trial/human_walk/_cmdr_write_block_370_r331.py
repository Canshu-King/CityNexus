"""Write the #370 ledger block: the 19 catch sites that write their own sentence, each with its words.

#369 said 0 of 20 calls show the server's sentence.  This block answers the only question that is left
before a work order can be pointed: what does the traveller get instead, and at which line does the panel
decide that.  Rows are parsed from the bw327 receipt while this runs and reconciled against its TALLY, so
the list cannot drift from the count it reports.
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
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"

CITES = {
    "same_source": (BW327, "SAME-SOURCE CHECK catch bodies read here"),
    "tally": (BW327, "TALLY catch="),
    "reverse": (BW327, "REVERSE_CHECK"),
    "distinct": (BW327, "SENTENCE_DISTINCT"),
    "reused": (BW327, "MOST_REUSED"),
    "rows_head": (BW327, "SAYS_ZH_ROWS the"),
    "counting": (BW327, "COUNTING_RULE"),
    "coverage": (BW327, "COVERAGE_LIMIT"),
    "tally_326": (BW326, "TALLY panels="),
    "ruler": ("trial/human_walk/_cmdr_sentence_shape_r327.py", "def literals"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.35 补（10-29 夜）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.34 补（10-29 午后）"),
}

ROW = re.compile(r"^\s{2}(\S+?):(\d+)\s+「(.+?)」\s+交state=(是|否)\s+重试句=(是|否)\s+双语形=(是|否)$")


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


def parsed_rows():
    rows = []
    for index, cell in enumerate(read(BW327).split("\n")):
        match = ROW.match(cell)
        if match:
            rows.append({"rel": match.group(1), "line": int(match.group(2)), "text": match.group(3),
                         "state": match.group(4) == "是", "retry": match.group(5) == "是",
                         "shape": match.group(6) == "是", "receipt_line": index + 1})
    if not rows:
        raise SystemExit("ABORT bw327 published no parseable per-site rows")
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    tally = row_at(BW327, at["tally"])
    caught, zh, en_only, nothing, shape, state, console, nowhere, retry, reads = [
        int(v) for v in re.findall(r"=(\d+)", tally)]
    if zh + en_only + nothing != caught:
        raise SystemExit("ABORT bw327's sentence axes do not cover its catch count")
    both = state + console + nowhere - caught
    if both < 0 or caught - nowhere - console > state:
        raise SystemExit("ABORT the destination axes do not reconcile: state=%d console=%d nowhere=%d "
                         "against catch=%d" % (state, console, nowhere, caught))
    rows = parsed_rows()
    if len(rows) != zh:
        raise SystemExit("ABORT parsed %d per-site rows against says_zh=%d" % (len(rows), zh))
    if sum(1 for item in rows if not item["shape"]) != 0:
        raise SystemExit("ABORT a row printed as says_zh lacks the bilingual shape, which the "
                         "REVERSE_CHECK arm says cannot happen")
    reverse = row_at(BW327, at["reverse"])
    zh_no_shape, shape_no_zh = [int(v) for v in re.findall(r"= (\d+)", reverse)]
    if (zh_no_shape, shape_no_zh) != (0, 0):
        raise SystemExit("ABORT the reverse sets are not empty, so zh and shape are not the same %d rows"
                         % zh)
    distinct_line = row_at(BW327, at["distinct"])
    distinct, occurrences = [int(v) for v in re.findall(r"(\d+)", distinct_line)][:2]
    if occurrences < len(rows):
        raise SystemExit("ABORT %d occurrences cannot cover %d rows" % (occurrences, len(rows)))
    catch_326 = int(re.search(r"catch=(\d+)", row_at(BW326, at["tally_326"])).group(1))
    if catch_326 != caught:
        raise SystemExit("ABORT bw326 counts %d catch bodies, bw327 counts %d" % (catch_326, caught))
    print("LIVE NUMBERS catch=%d says_zh=%d shape=%d into_state=%d nowhere=%d retry=%d distinct=%d "
          "occurrences=%d" % (caught, zh, shape, state, nowhere, retry, distinct, occurrences))

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

    listing = ["　%d｜`%s:%d` 交state=%s 重试句=%s 双语形=%s｜「%s」（回执 %s:%d）"
               % (index + 1, item["rel"], item["line"], "是" if item["state"] else "否",
                  "是" if item["retry"] else "否", "是" if item["shape"] else "否", item["text"],
                  BW327, item["receipt_line"])
               for index, item in enumerate(rows)]

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
        "### 494abfd7 交「屏上改写成什么话」的逐枚靶面：十九处自造句子的 catch（#370，接 #369）",
        "",
        "- #369 说这 %d 条路上 0 条显服务端原文。这一格答剩下那一问：旅客拿到的是什么话、在哪一行被决定。"
        "尺 trial/human_walk/_cmdr_sentence_shape_r327.py:%d 读的是 %s:%d 那同批 catch body。"
        % (zh, at["ruler"], BW326, at["tally_326"]),
        "- 分母同代对账：本尺读到 catch body %d 处＝bw326 发布 catch=%d（回执 %s:%d）；"
        "三轴相加覆盖全数（说中文 %d ＋ 只说英文 %d ＋ 不带字面量 %d ＝ %d，回执 :%d）；"
        "本块解析 %d 行＝says_zh %d。" % (caught, catch_326, BW326, at["tally_326"], zh, en_only,
                                            nothing, caught, at["tally"], len(rows), zh),
        "- 三轴读数（回执 %s:%d）：说中文 %d 处、只英文 %d 处、无字面量 %d 处；双语形 %d 处；"
        "交给 state %d 处、交给 console %d 处、两者都不是 %d 处；重试句形 %d 处；两旗皆有的 %d 处。"
        % (BW327, at["tally"], zh, en_only, nothing, shape, state, console, nowhere, retry, both),
        "- 两向反集都空才算同一集合（回执 %s:%d）：说中文却不带 `zh ?` 形 = %d，带形却无中文 = %d。"
        "所以「旅客-facing 的失败话只有一种写法」这句是量出来的，不是看出来的。"
        % (BW327, at["reverse"], zh_no_shape, shape_no_zh),
        "- 也不是万能句刷屏（回执 %s:%d、%s:%d）：%d 处句子共 %d 枚不同，只有一句被用了两次——"
        "「连不上服务器，请重试。」。也就是说：每处失败都各写了一句像样话，而其中 %d 句没有一句能带出"
        "服务端给的理由。" % (BW327, at["distinct"], BW327, at["reused"], occurrences, distinct, zh),
        "- 下面 %d 行整串由回执解析、非手抄，每行自带 catch 坐标、三轴旗与该句原文：" % len(rows),
    ] + listing + [
        "- 这把尺不能说的那句（不替它补）：交 state 只证明这句话进了组件状态，不证明有东西把它渲染出来；"
        "一处 catch 里也可能同时有 setter 与一句无关字面量。「这句到底点没点名被拒的那一项」我不做关键词代理，"
        "句子已逐枚原文列出，请读。极限写在回执 %s:%d 与判据在 %s:%d。"
        % (BW327, at["coverage"], BW327, at["counting"]),
        "- 待裁（不代裁）：#369 那三档里的甲单，靶面就是上面这 %d 行——每行一枚 catch、一句话、一个坐标，"
        "可逐枚点；乙仍是按 §14.32 三档先改后端文案（屏读不变，因 #369 已量到这批句子不来自服务端）；"
        "丙两批同点。本班 0 改产品字节。" % zh,
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
    if back.count("｜「") != len(rows):
        raise SystemExit("ABORT not every parsed row made it into the block")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
