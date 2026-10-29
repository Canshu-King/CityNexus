"""Append section 14.29: the 333 sentences get a surface split, so the traveller-facing number is 221."""

import io
import os
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"

CITES = {
    "bw302_denom": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "DENOMINATOR this census"),
    "bw302_split": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "ENGLISH SENTENCES 330"),
    "bw302_via": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "ROUTE-REACHABLE SPLIT"),
    "bw302_control": (GOZERO + "/bw302-which-surface-says-it-in-english.txt", "NAMED CONTROL"),
    "rule": ("trial/human_walk/_cmdr_surface_of_english_refusals_r302.py", "def route_paths"),
    "bw293_buckets": (GOZERO + "/bw293-bare-english-refusals.txt", "BUCKETS CODE_ONLY"),
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
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.29 补" in text:
        print("ABORT the section is already appended")
        return 4

    b = GOZERO + "/"
    block = "\n".join([
        "14.29 补（10-29 午后）：那 333 处英文句按「谁的面」拆开——旅客真能撞到的是 221 处",
        "",
        "- §14.28 报了句子的总数，总数不能当成屏的问题：同一桶里混着旅客点得到的路由、只有 Agent 走的工具面、"
        "以及找不到路由的内部函数。尺 trial/human_walk/_cmdr_surface_of_english_refusals_r302.py:%d "
        "按「这处 raise 所在函数自己带不带 @app/@router 装饰器」分面，回执 %s:%d。"
        % (at["rule"], b + "bw302-which-surface-says-it-in-english.txt", at["bw302_split"]),
        "- 分面读数：英文句 330 处里 ROUTE_REACHABLE 221 处、AGENT_SURFACE 91 处、INTERNAL 18 处（%s:%d）。"
        "221 处再按绑定方式分：自带路由装饰器 145 处、函数自己没有装饰器但同模块挂着路由 76 处"
        "（同回执 :%d）。给主人的一句话：**要修屏上中文，先修这 221 处，不是 333 处**。"
        % (b + "bw302-which-surface-says-it-in-english.txt", at["bw302_split"], at["bw302_via"]),
        "- 两把尺的分母不同，写进回执不含糊：本尺读 1113 处（只数函数体内、且 detail 是字面文本的），"
        "%s:%d 那把读 1187 处（还走模块级与 lambda，并记下运行时拼出来的 detail）。"
        "差的 3 处**没有逐枚对账**，这句是边界不是结论（同回执 :%d）。"
        % (b + "bw293-bare-english-refusals.txt", at["bw293_buckets"], at["bw302_denom"]),
        "- 标注诚实性（本班在这格上错过一次，改掉）：第一版把 `_trip_studio_context` 里那句英文标成"
        "「绑在 /api/v1/health 上」——那是同模块的第一条路由，不是这句话的入口。现在具名对照写清"
        "「helper 自己无装饰器、其模块挂 288 条路由、不替它认领某一条 URL」（%s:%d）。"
        % (b + "bw302-which-surface-says-it-in-english.txt", at["bw302_control"]),
        "- 承 §14.28 待裁那条：要让这 221 处在 raise 处带上各自具名键，才谈得上中文；"
        "现状是统一出口 backend/app/main.py:784 按状态码拼键，同码不同句共用一枚。"
        "本班 0 改产品字节、不代裁。",
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.29 补")
    print("APPENDED bytes_added=%d heading_hits=%d prev_line=%d"
          % (len(block.encode("utf-8")), hits, at["prev_section"]))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
