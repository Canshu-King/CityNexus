"""Write the #360 ledger block: the refusal-sentence denominator, the synthesised key, one retraction.

Every cited line number is re-read from the artifact at invocation time and a non-unique anchor aborts
the block, because this shift has already had to retract numbers written from memory.  The closing
line is taken verbatim from live_checks/CLOSING_LINE.txt, which is what the applier checks.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
GOZERO = "trial/results/20261026_gozero"
OUT = r"D:\moodle\_qoder_ledger_inbox\494abfd7_0452.md"

CITES = {
    "denom": (GOZERO + "/bw293-bare-english-refusals.txt", "RAISES FOUND"),
    "buckets": (GOZERO + "/bw293-bare-english-refusals.txt", "BUCKETS CODE_ONLY"),
    "shapes": (GOZERO + "/bw293-bare-english-refusals.txt", "PAYLOAD SHAPES"),
    "english_shape": (GOZERO + "/bw293-bare-english-refusals.txt", "ENGLISH SENTENCE BY PAYLOAD SHAPE"),
    "conclusion": (GOZERO + "/bw293-bare-english-refusals.txt", "CONCLUSION of these"),
    "named": (GOZERO + "/bw293-bare-english-refusals.txt", "'Trip Studio requires an active plan' ->"),
    "produced": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "PRODUCED (a literal key"),
    "verdict": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "VERDICT the key is written"),
    "wrapper_src": ("backend/app/main.py", '"message_key": message_key or f"error.{code.lower()}"'),
    "census_rule": ("trial/human_walk/_cmdr_bare_english_refusals_r293.py", "def detail_shape"),
    "origin_rule": ("trial/human_walk/_cmdr_message_key_origin_r296.py", "WRITE_MARKS = "),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.28 补（10-29 午）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.27 补（10-29 午）"),
}


def line_of(rel, needle):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    hits = [index + 1 for index, row in enumerate(
        io.open(path, encoding="utf-8", errors="replace").read().split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

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

    g = GOZERO + "/"
    body = "\n".join([
        "### 494abfd7 交「屏上拿到英文原句」的分母与那条键的真实产地（#360，附一条撤回）",
        "",
        "- 分母：backend/app 下 238 枚模块、HTTPException 共 1187 处，分桶为纯码 738 处、英文句 333 处、"
        "码＋句混写 32 处、运行时拼装 77 处（尺 %s:%d 用 ast 逐枚解析；回执 %s:%d 与 :%d）。"
        % ("trial/human_walk/_cmdr_bare_english_refusals_r293.py", at["census_rule"],
           g + "bw293-bare-english-refusals.txt", at["denom"], at["buckets"]),
        "- 载荷形状：明文串 1110 处、dict 但未带 message_key 6 处、运行时拼 71 处，"
        "**带自己那枚键的 0 处**；333 处英文句里带键的也是 0 处（%s:%d、:%d、:%d）。"
        % (g + "bw293-bare-english-refusals.txt", at["shapes"], at["english_shape"],
           at["conclusion"]),
        "- 屏上那条键的产地（本班先前没查清的一格）：统一出口 backend/app/main.py:%d 写的是 "
        "`message_key or f\"error.{code.lower()}\"`；这类拼键点 %s:%d 列了 23 行，"
        "%s:%d 判「键写在 raise 之外的地方」。尺 trial/human_walk/_cmdr_message_key_origin_r296.py:%d。"
        "后果：前端可本地化的粒度等于 HTTP 状态码、不等于这条拒绝——光 409 就把好几句不同的话并成同一个 "
        "request.conflict（本机真读到的一例在 %s:%d）。"
        % (at["wrapper_src"], g + "bw296-where-the-message-key-comes-from.txt", at["produced"],
           g + "bw296-where-the-message-key-comes-from.txt", at["verdict"], at["origin_rule"],
           g + "bw293-bare-english-refusals.txt", at["named"]),
        "- 一条撤回（按口径发新条、不改旧文）：本班先前在会话里报过「全库带 message_key 的只有 30 处」，"
        "那个数从未落进任何一枚回执，它来自一段被截断的终端回显；落盘重算的真读数是 0 处，先前那句作废。"
        "同一批回显还让我把「尺算了却没打印」当成「尺已发布」，现已把输出行补回并重跑，"
        "回执里那几行是重跑后的读数（分辨不出三桶就不发布数字）。",
        "- 待裁（与 §%d 那三件并成一串，本班 0 改产品字节、不代裁）：要不要让这 333 处英文句在 raise 处"
        "就带上各自的具名键——带上才谈得上中文；现状是按码拼键，同码不同句共用一枚键。"
        % at["prev_section"],
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。" % (at["section"], sha),
        "",
        closing,
        "",
    ])

    pending = [f for f in os.listdir(r"D:/moodle/_qoder_ledger_inbox")
               if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(OUT, encoding="utf-8").read()
    if not back.startswith("### "):
        raise SystemExit("ABORT the block does not open with a heading")
    if closing not in back:
        raise SystemExit("ABORT the closing line did not land")
    print("WROTE %s bytes=%d" % (OUT, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
