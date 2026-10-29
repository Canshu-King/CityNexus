"""Write the #361 ledger block: the surface split behind the traveller-facing number.

Anchors and the generation object are re-read at invocation time; a non-unique anchor or a missing
artifact aborts the block instead of shipping a coordinate that cannot be retrieved.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
GOZERO = "trial/results/20261026_gozero"
OUT = r"D:\moodle\_qoder_ledger_inbox\494abfd7_0537.md"

CITES = {
    "split": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "ENGLISH SENTENCES 330"),
    "via": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "ROUTE-REACHABLE SPLIT"),
    "denom": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "DENOMINATOR this census"),
    "control": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "NAMED CONTROL"),
    "rule": ("trial/human_walk/_cmdr_surface_of_english_refusals_r302.py", "def route_paths"),
    "prev_buckets": (GOZERO + "/bw293-bare-english-refusals.txt", "BUCKETS CODE_ONLY"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.29 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.28 补（10-29 午）"),
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

    b = GOZERO + "/"
    bw302 = b + "bw302-which-surface-says-it-in-english.txt"
    body = "\n".join([
        "### 494abfd7 交「旅客真能撞到的英文句是 221 处」的分面读数（#361，接 §14.28 那条待裁）",
        "",
        "- 为什么要再拆一刀：§14.28 报了句子总数，总数不能当成屏的问题——同一桶里混着旅客点得到的路由、"
        "只有 Agent 走的工具面、找不到路由的内部函数。尺 trial/human_walk/"
        "_cmdr_surface_of_english_refusals_r302.py:%d 按「这处 raise 所在函数自己带不带 "
        "@app/@router 装饰器」分面。" % at["rule"],
        "- 分面读数：英文句 330 处里 ROUTE_REACHABLE 221 处、AGENT_SURFACE 91 处、INTERNAL 18 处"
        "（回执 %s:%d）。221 处再按绑定方式分：自带路由装饰器 145 处、函数自己无装饰器但同模块挂着"
        "路由 76 处（同回执 :%d）。给主人的一句话：要修屏上中文，先修这 221 处，不是 333 处。"
        % (bw302, at["split"], at["via"]),
        "- 两把尺的分母不同，写清不含糊：本尺读 1113 处（只数函数体内、detail 是字面文本的），"
        "§14.28 那把读 1187 处（还走模块级与 lambda、并记运行时拼出来的 detail）；"
        "差的 3 处没有逐枚对账，这句是边界不是结论（%s:%d 与 %s:%d）。"
        % (b + "bw293-bare-english-refusals.txt", at["prev_buckets"], bw302, at["denom"]),
        "- 标注诚实性一格（本班在这格错过一次，改掉）：第一版把 `_trip_studio_context` 里那句英文标成"
        "「绑在 /api/v1/health 上」，那是同模块的第一条路由、不是这句话的入口；现在具名对照写清"
        "「helper 自己无装饰器、其模块挂 288 条路由、不替它认领某一条 URL」（%s:%d）。"
        % (bw302, at["control"]),
        "- 待裁（并入 §14.28 已点的那条，不另开）：要让这 221 处在 raise 处带上各自具名键，"
        "才谈得上中文；现状是统一出口 backend/app/main.py:784 按状态码拼键，同码不同句共用一枚。"
        "本班 0 改产品字节、不代裁。",
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
