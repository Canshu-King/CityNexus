"""Write the #372 ledger block: each of the 19 panel catch sites whose own sentence markup reads.

#370 listed the 19 sentences and stopped at "written into a state".  Whether anything renders that state was
the one open link, and bw328 measured it: the setter behind each literal, the state name it fills, and the
lines where markup reads that name.  Rows are parsed from the bw328 receipt while this runs, reconciled
against its TALLY, and cross-checked against bw327's own row list in both directions, so this block cannot
list a different set of sites than the two rulers agree on.  Nothing here is a click on a real screen.
"""

import io
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
GOZERO = "trial/results/20261026_gozero"
BW328 = GOZERO + "/bw328-is-that-sentence-on-screen.txt"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"

CITES = {
    "same_source": (BW328, "SAME-SOURCE CHECK rows read from bw327"),
    "controls": (BW328, "CONTROLS the LiveRecovery handler"),
    "tally": (BW328, "TALLY rows="),
    "counting": (BW328, "COUNTING_RULE"),
    "coverage": (BW328, "COVERAGE_LIMIT"),
    "tally_327": (BW327, "TALLY catch="),
    "rows_head_327": (BW327, "SAYS_ZH_ROWS the"),
    "ruler": ("trial/human_walk/_cmdr_render_check_r328.py", "def render_sites"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.37 补（10-29 夜）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.36 补（10-29 夜）"),
    "plan_cmp": ("frontend/src/features/planning/PlanComparison.tsx", "{error && ("),
    "live_msg": ("frontend/src/features/execution/LiveRecovery.tsx", "{message && ("),
}

ROW328 = re.compile(r"^\s{2}(\S+?):(\d+)\s+(\d+) 枚中文句子.*?→ (\S+?)；(.*)$")
PAIR = re.compile(r"「(.*?)」state=(\w+) 渲染点=([\d, ]+)")
ROW327 = re.compile(r"^\s{2}(\S+?):(\d+)\s+「(.+?)」\s+交state=(是|否)\s+重试句=(是|否)\s+双语形=(是|否)$")


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
    for index, line in enumerate(read(BW328).split("\n")):
        match = ROW328.match(line)
        if not match:
            continue
        pairs = PAIR.findall(match.group(5))
        if not pairs:
            raise SystemExit("ABORT row %s carries a verdict but no sentence-to-state pair"
                             % match.group(1))
        rows.append({"rel": match.group(1), "line": int(match.group(2)),
                     "cjk": int(match.group(3)), "verdict": match.group(4),
                     "pairs": [{"text": t, "state": s, "sites": sites.strip().rstrip(",")}
                               for t, s, sites in pairs],
                     "receipt_line": index + 1})
    if not rows:
        raise SystemExit("ABORT bw328 published no parseable rows")
    return rows


def says_zh_keys():
    keys = set()
    for line in read(BW327).split("\n"):
        match = ROW327.match(line)
        if match:
            keys.add((match.group(1), int(match.group(2))))
    if not keys:
        raise SystemExit("ABORT bw327's says_zh list parsed to nothing")
    return keys


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    rows_n, rendered, not_rendered, no_setter = [int(v) for v in
                                                 re.findall(r"=(\d+)", row_at(BW328, at["tally"]))]
    rows = parsed_rows()
    keys328 = set((item["rel"], item["line"]) for item in rows)
    keys327 = says_zh_keys()
    only_327 = len(keys327 - keys328)
    only_328 = len(keys328 - keys327)
    pairs_n = sum(len(item["pairs"]) for item in rows)
    state_rows = Counter(state for item in rows for state in
                         set(pair["state"] for pair in item["pairs"]))
    top_state, top_rows = state_rows.most_common(1)[0]
    say327 = int(re.search(r"says_zh=(\d+)", row_at(BW327, at["tally_327"])).group(1))
    print("LIVE NUMBERS rows=%d rendered=%d not_rendered=%d no_setter=%d pairs=%d "
          "only_327=%d only_328=%d states=%d top=%s:%d says_zh_327=%d"
          % (rows_n, rendered, not_rendered, no_setter, pairs_n, only_327, only_328,
             len(state_rows), top_state, top_rows, say327))

    if len(rows) != rows_n:
        raise SystemExit("ABORT parsed %d rows but bw328 publishes %d" % (len(rows), rows_n))
    if rendered + not_rendered + no_setter != rows_n:
        raise SystemExit("ABORT bw328's verdicts do not cover its rows")
    if sum(1 for item in rows if item["verdict"] == "RENDERED") != rendered:
        raise SystemExit("ABORT the parsed verdicts disagree with the TALLY")
    if rows_n != say327:
        raise SystemExit("ABORT bw328 has %d rows, bw327 lists %d sites" % (rows_n, say327))
    if only_327 or only_328:
        raise SystemExit("ABORT the two receipts disagree on the set: %d only in bw327, %d only in bw328"
                         % (only_327, only_328))
    control = row_at(BW328, at["controls"])
    found = re.search(r"state '(\w+)', read at lines ([\d, ]+);", control)
    if not found:
        raise SystemExit("ABORT the positive control sentence did not parse out of the CONTROLS line")
    control_state, control_sites = found.group(1), found.group(2).strip().rstrip(",")
    if "yields 0 render sites" not in control:
        raise SystemExit("ABORT the negative control is not stated in the CONTROLS line")

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
    out = None
    for offset in range(0, 240):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out = candidate
            break
    if out is None:
        raise SystemExit("ABORT no free inbox name in the next four hours")

    listing = []
    for index, item in enumerate(rows):
        first = item["pairs"][0]
        listing.append("　%d｜`%s:%d` → %s｜state `%s` 被标记读于 :%s｜首句「%s」（回执 %s:%d）"
                       % (index + 1, item["rel"], item["line"], item["verdict"],
                          first["state"], first["sites"], first["text"], BW328, item["receipt_line"]))

    body = "\n".join([
        "### 494abfd7 交「面板自造的话句句被标记读到」的逐枚闭链：十九处 catch 各自的 state 与渲染行（#372，接 #370）",
        "",
        "- #370 停在「写进 state」，没证有东西把它读出来。这一格补最后那一环。尺 "
        "trial/human_walk/_cmdr_render_check_r328.py:%d 从 catch body 取字面量、认包着它的那次 setXxx(...)、"
        "推出 state 名，再在本文件找该名字出现在 `{…}` 内或 `&&`/`?`/`||` 条件位的行。" % at["ruler"],
        "- 分母同代对账：回执 %s:%d 发布 rows=%d，本块解析 %d 行；与回执 %s:%d 的 says_zh=%d 同数；"
        "两把尺列出的 (文件,行) 集合互差 空集（只在 bw327 %d 处、只在 bw328 %d 处）。"
        % (BW328, at["tally"], rows_n, len(rows), BW327, at["tally_327"], say327, only_327, only_328),
        "- 读数（回执 %s:%d）：%d 处全部 RENDERED；存了没人读 %d 处；句子不在任何 setter 里 %d 处。"
        "三种判据相加＝全数，故不存在「判不出」那一档。" % (BW328, at["tally"], rendered, not_rendered, no_setter),
        "- 一句 state 承接了多少处：渲染映射共 %d 枚（一行 catch 里可含多枚句子），落在 %d 个 state 名上；"
        "其中 `%s` 被 %d 处 catch 共用（回执 %s:%d 的行序解析）。这就是「旅客看到的其实是同一条提示带」的形制。"
        % (pairs_n, len(state_rows), top_state, top_rows, BW328, at["tally"]),
        "- 判别力在两处控制（回执 %s:%d）：正控制——LiveRecovery 那句交给 state `%s`，本尺读出它在 :%s；"
        "反控——一个谁都没定义的 state 名必须给 0 个渲染点，回执同句实测 0。另有一处我自己造的假阴性已修："
        "第一版拿 bw327 的显示串去匹配，而它把同 body 的多枚字面量并成一串，于是整行被判「不在 setter 里」；"
        "改成直接从 catch body 取字面量才回到现读数。" % (BW328, at["controls"], control_state, control_sites),
        "- 两处手工复核（不靠正则自证）：frontend/src/features/planning/PlanComparison.tsx:%d 与 "
        "frontend/src/features/execution/LiveRecovery.tsx:%d——两枚都带 role，是给人看的东西，不是调试残留。"
        % (at["plan_cmp"], at["live_msg"]),
        "- 下面 %d 行整串由回执解析、非手抄，每行自带 catch 坐标、state 名与读到它的标记行：" % len(rows),
    ] + listing + [
        "- 这把尺不能说的那句（不替它补）：被标记读到 ≠ 旅客当时站在那一屏；句子若经共用组件当 prop 传下去，"
        "本尺只走同文件的 state 这条路。它也不判这句话对不对——只判它显不显。极限写在回执 %s:%d，"
        "判据写在 %s:%d。" % (BW328, at["coverage"], BW328, at["counting"]),
        "- 待裁（不代裁）：链既然闭上，甲单就是上面这 %d 行——改法是让 catch 读回端的 `detail`/`message_key` "
        "而不是自造一句；乙仍是按 §14.32 三档先改后端文案（屏读不变，因 #369 已量到这批句子不来自服务端）；"
        "丙两批同点。本班 0 改产品字节。" % len(rows),
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。"
        % (at["section"], at["prev_section"], sha),
        "",
        closing,
        "",
    ])

    # Everything is checked against the in-memory text first: a block that fails its own shape checks
    # must never reach the inbox, because an aborted write used to leave a draft there for the next round
    # to trip over.
    def check(text):
        if not text.startswith("### "):
            raise SystemExit("ABORT the block does not open with a heading")
        if closing not in text:
            raise SystemExit("ABORT the closing line did not land")
        if "\r\n" in text:
            raise SystemExit("ABORT the inbox block must stay LF-only")
        if text.count("｜`") != len(rows):
            raise SystemExit("ABORT not every parsed row made it into the block")
        if "%d" in text or "%s" in text:
            raise SystemExit("ABORT an unformatted slot survived into the block")
        for pointer in ("GO_FROM_BLANK_REPORT.md:%d" % at["section"],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["prev_section"],
                        "bw328-is-that-sentence-on-screen.txt:%d" % at["tally"],
                        "%s:%d" % ("frontend/src/features/planning/PlanComparison.tsx", at["plan_cmp"]),
                        "%s:%d" % ("frontend/src/features/execution/LiveRecovery.tsx", at["live_msg"])):
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
