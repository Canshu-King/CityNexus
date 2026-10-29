"""Write the #366 ledger block: the 21 traveller-facing refusals, and who in the frontend asks for each.

Rows are parsed from bw318 while this runs; the row count is reconciled against bw313's published
intersection and against the receipt's own TALLY, so the block cannot list a different set than the ruler.
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
BW318 = GOZERO + "/bw318-which-of-these-has-a-button.txt"
BW313 = GOZERO + "/bw313-traveller-side-and-internal-vocabulary.txt"

CITES = {
    "denominator": (BW318, "DENOMINATOR rows read out of bw313"),
    "tally": (BW318, "TALLY caller_found="),
    "negative": (BW318, "NEGATIVE_CONTROL"),
    "counting": (BW318, "COUNTING_RULE"),
    "coverage": (BW318, "COVERAGE_LIMIT"),
    "intersection": (BW313, "INTERSECTION the job"),
    "ruler": ("trial/human_walk/_cmdr_button_reachability_r318.py", "def tail_segments"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.33 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.32 补（10-29 午后）"),
}

ROW = re.compile(r"^\s*(\d+)\.\s+(\S+)\s+\(backend (\S+), terms=(.*?)\)\s+->\s+(\S+)(.*)$")


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
    lines = read(BW318).split("\n")
    rows = []
    for index, line in enumerate(lines):
        match = ROW.match(line)
        if not match:
            continue
        verdict = match.group(5)
        caller = ""
        if verdict.startswith("CALLER_FOUND"):
            for following in lines[index + 1:index + 5]:
                found = re.search(r"(frontend/\S+?:\d+)", following)
                if found:
                    caller = found.group(1)
                    break
            if not caller:
                raise SystemExit("ABORT row %s says caller found but no frontend coordinate follows"
                                 % match.group(1))
        rows.append({"rank": int(match.group(1)), "url": match.group(2), "backend": match.group(3),
                     "terms": match.group(4), "verdict": verdict, "caller": caller})
    if not rows:
        raise SystemExit("ABORT bw318 published no parseable rows")
    if rows[0]["rank"] != 1:
        raise SystemExit("ABORT the row list does not start at one")
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    denominator = row_at(BW318, at["denominator"])
    scanned = int(re.search(r"scanned = (\d+)", denominator).group(1))
    published_rows = int(re.search(r"bw313 = (\d+)", denominator).group(1))
    intersection = int(re.search(r"would actually touch: (\d+)",
                                 row_at(BW313, at["intersection"])).group(1))
    caller_found, no_caller, total = [int(v) for v in re.findall(r"=(\d+)", row_at(BW318, at["tally"]))]
    rows = parsed_rows()
    print("LIVE NUMBERS rows=%d scanned=%d caller_found=%d no_caller=%d intersection=%d"
          % (len(rows), scanned, caller_found, no_caller, intersection))
    if not (published_rows == intersection == total == len(rows)):
        raise SystemExit("ABORT the denominators disagree: bw318 %s/%s, bw313 %d, parsed %d"
                         % (published_rows, total, intersection, len(rows)))
    if caller_found + no_caller != total:
        raise SystemExit("ABORT the tally does not cover every row")
    if sum(1 for item in rows if item["verdict"].startswith("CALLER_FOUND")) != caller_found:
        raise SystemExit("ABORT the parsed verdicts disagree with the tally")

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
        listing.append("　%d｜`%s` → %s（后端 %s，术语 %s）"
                       % (item["rank"], item["url"],
                          ("前端会问 " + item["caller"]) if item["caller"] else "前端没人问",
                          item["backend"], item["terms"]))

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
        "### 494abfd7 交「%d 处里哪几处前端会问」的逐枚映射（#366，接 §14.33）" % total,
        "",
        "- 为什么还要这一腿：§14.32 交出 %d 处的 URL 与句子，但没说旅客按什么键会撞到。"
        "尺 trial/human_walk/_cmdr_button_reachability_r318.py:%d 在前端手写源码里要求同文件同时出现"
        "该路径的最后两段（拼接 URL 的形制见回执 %s:%d），并把生成的 OpenAPI 客户端、测试与 spec 助手"
        "排除——不排除的话每条路由都会被算成「有按钮」。"
        % (total, at["ruler"], BW318, at["denominator"]),
        "- 分母同代对账：bw318 读入 %d 行、bw313 发布交集 %d 处、TALLY 合计 %d 处、本块解析 %d 行，"
        "四者相等才继续（回执 %s:%d、%s:%d）；前端被扫文件 %d 枚。"
        % (published_rows, intersection, total, len(rows), BW318, at["denominator"],
           BW313, at["intersection"], scanned),
        "- 读数：%d 处前端会问、%d 处没人问（回执 :%d 的 TALLY）。下面 %d 行整串由回执解析，非手抄："
        % (caller_found, no_caller, at["tally"], len(rows)),
    ] + listing + [
        "- 反控（证这把尺不会什么都说「有」）：拿一条本机不存在的路径同法去查，必须查无命中"
        "（回执 :%d 实测 CLEAN）；口径写在 :%d，能查到的极限写在 :%d。"
        % (at["negative"], at["counting"], at["coverage"]),
        "- 这把尺不能说的那句（不替它补）：源码里有调用者 ≠ 屏上有一枚按得到的按钮，"
        "它只证明「前端某处会发这个请求」；回执附的中文串取同文件 40 行内第一个含汉字的字面量，"
        "可能属于同文件另一个控件——「屏上会不会被前端自己的中文盖住」这句我没判，"
        "要判得走真机或读渲染点。本班 0 改产品字节。",
        "- 待裁（不代裁）：要不要把这一腿走完（把会问的那 %d 处接成「哪枚面板 / 哪枚按钮 → 哪句英文」"
        "并上真机），还是就此按 §14.32 的三档直接点文案刀。" % caller_found,
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
