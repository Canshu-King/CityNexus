"""Write the #364 ledger block: the internal-vocabulary bucket, word by word.

Every per-word row, every count and the generation object are read out of the artifacts while this
generator runs; a row that will not parse, a bucket that disagrees with bw307, or a non-unique anchor
aborts the block instead of shipping a figure somebody else cannot retrieve.
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
BW310 = GOZERO + "/bw310-internal-vocabulary-by-word.txt"
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"

CITES = {
    "same_source": (BW310, "SAME-SOURCE CHECK sentences carrying internal vocabulary"),
    "recon": (BW310, "RECONCILIATION bucket="),
    "case_row": (BW310, "CASE SENSITIVITY"),
    "silent_row": (BW310, "SILENT TERMS"),
    "journey_coords": (BW310, "coords: backend/app/main.py:3715"),
    "guard": ("trial/human_walk/_cmdr_jargon_by_word_r310.py", "claims %d hits but carries"),
    "key_synthesiser": ("backend/app/main.py", '"message_key": message_key or'),
    "vocab": ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", "INTERNAL_JARGON = ("),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.31 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.30 补（10-29 午后）"),
    "bw307_shapes": (BW307, "carrying internal vocabulary"),
}

WORD_ROW = re.compile(r"^  (\S.*?)\s+(\d+)处\s+on a traveller path (\d+)\s+"
                      r"case-insensitive would add (\d+)\s+representative (\S+):(\d+)")


def read(rel):
    return io.open(os.path.join(ROOT, rel.replace("/", os.sep)),
                   encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    if not os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep))):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    hits = [index + 1 for index, row in enumerate(read(rel).split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def numbers(rel, line, index, pattern=r"\d+"):
    found = re.findall(pattern, row_at(rel, line))
    if len(found) <= index:
        raise SystemExit("ABORT line %d of %s has no number %d matching %s"
                         % (line, rel, index, pattern))
    return int(found[index])


def word_rows():
    parsed = []
    for line in read(BW310).split("\n"):
        match = WORD_ROW.match(line)
        if match:
            parsed.append({"term": match.group(1), "hits": int(match.group(2)),
                           "traveller": int(match.group(3)), "case_extra": int(match.group(4)),
                           "file": match.group(5), "line": int(match.group(6))})
    if len(parsed) < 5:
        raise SystemExit("ABORT only %d per-word rows parsed, the receipt shape changed" % len(parsed))
    return parsed


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    bucket = numbers(BW310, at["same_source"], 0, r"vocabulary = (\d+)")
    shapes_bucket = numbers(BW307, at["bw307_shapes"], 0, r"vocabulary: (\d+)")
    if bucket != shapes_bucket:
        raise SystemExit("ABORT bw310 sees %d but bw307 published %d" % (bucket, shapes_bucket))
    recon = [int(v) for v in re.findall(r"\d+", row_at(BW310, at["recon"]))]
    if len(recon) != 4:
        raise SystemExit("ABORT the reconciliation row reads %s" % recon)
    case_numbers = [int(v) for v in re.findall(r"\d+", row_at(BW310, at["case_row"]))]
    if len(case_numbers) != 3:
        raise SystemExit("ABORT the case row reads %s" % case_numbers)
    silent_terms, vocab_size = numbers(BW310, at["silent_row"], 0), numbers(BW310,
                                                                           at["silent_row"], 1)
    rows = word_rows()
    if sum(item["hits"] for item in rows) != recon[1]:
        raise SystemExit("ABORT the parsed rows sum to %d but the receipt reconciles to %d"
                         % (sum(item["hits"] for item in rows), recon[1]))
    print("LIVE NUMBERS bucket=%d rows=%d sum=%d ci=%d silent=%d/%d"
          % (bucket, len(rows), recon[1], case_numbers[1], silent_terms, vocab_size))

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

    listing = ["　%s｜%d 处（其中旅客真路径 %d 处）代表 %s:%d"
               % (item["term"], item["hits"], item["traveller"], item["file"], item["line"])
               for item in rows]

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
        "### 494abfd7 交「%d 处内部词汇」的逐词分布与各自坐标（#364，接 §14.31 那条待裁）" % bucket,
        "",
        "- 为什么再拆：§14.30 给的是一整桶，「把内部词汇改成人话」这句话没有对象——"
        "要按词点单，得先知道是哪些词、各占几处。尺 trial/human_walk/"
        "_cmdr_jargon_by_word_r310.py:%d 复用 §14.29 那把尺的词表（trial/human_walk/"
        "_cmdr_what_traveller_reads_r307.py:%d 的 %d 枚术语），import 不重打。"
        % (at["guard"], at["vocab"], vocab_size),
        "- 同源校验：本尺 %d 处与 §14.30 那把尺各自现读一致"
        "（回执 %s:%d、%s:%d），对不上就 ABORT 不出表。" % (bucket, BW310, at["same_source"],
                                                        BW307, at["bw307_shapes"]),
        "- 逐词命中（按处数降序，整串由回执解析，非手抄；共 %d 枚术语命中）：" % len(rows),
    ] + listing + [
        "- 两处口径依赖（报数不带就等于报一个会飘的数）：其一，逐词相加 %d 与桶 %d 相等、"
        "差 %d，因为没有句子同时带两个术语（回执 %s:%d）——所以这一族不能按「词数」估工时，"
        "要按处数。其二，%d 是大小写敏感的读法，同一词表改成不区分大小写会把桶撑到 %d 处（多 %d 处），"
        "同回执 :%d。" % (recon[1], recon[0], recon[2], BW310, at["recon"],
                        case_numbers[0], case_numbers[1], case_numbers[2], at["case_row"]),
        "- 词表过宽一格自报：%d 枚术语里 %d 枚在这 %d 处里一次都没说到（回执 :%d）——"
        "那是 §14.29 定表时按「工程常见黑话」拍的，不是从屏上句子归纳的；下一版应当从屏上这 %d 处反推。"
        % (vocab_size, silent_terms, bucket, at["silent_row"], bucket),
        "- 本班自造的一格故障（写下来不藏）：第一版逐枚坐标行恒空——渲染循环读的是排序前残留的循环变量。"
        "现在坐标随元组一起存，并装了「命中数与坐标数不等即 ABORT」的守卫（尺 :%d）。" % at["guard"],
        "- 待裁（不代裁）：甲，先只动最大那一族（见上表第一行），还是 %d 处一并动；"
        "乙，是否给这些 raise 配各自具名键（统一出口 backend/app/main.py:%d 仍按状态码拼键）。"
        "本班 0 改产品字节。" % (bucket, at["key_synthesiser"]),
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
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
