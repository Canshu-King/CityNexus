"""Append section 14.28: the refusal-sentence denominator, where the message_key really comes from,
and the retraction of a number that was never on disk."""

import io
import os
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"

# every coordinate below is re-read from the artifact at invocation time; none is written from memory
CITES = {
    "denom": (GOZERO + "/bw293-bare-english-refusals.txt", "RAISES FOUND"),
    "buckets": (GOZERO + "/bw293-bare-english-refusals.txt", "BUCKETS CODE_ONLY"),
    "shapes": (GOZERO + "/bw293-bare-english-refusals.txt", "PAYLOAD SHAPES"),
    "english_shape": (GOZERO + "/bw293-bare-english-refusals.txt", "ENGLISH SENTENCE BY PAYLOAD SHAPE"),
    "conclusion": (GOZERO + "/bw293-bare-english-refusals.txt", "CONCLUSION of these"),
    "named": (GOZERO + "/bw293-bare-english-refusals.txt", "'Trip Studio requires an active plan' ->"),
    "scanned": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "MODULES SCANNED"),
    "produced": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "PRODUCED (a literal key"),
    "wrapper": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "backend/app/main.py:784"),
    "verdict": (GOZERO + "/bw296-where-the-message-key-comes-from.txt", "VERDICT the key is written"),
    "tree_a": (GOZERO + "/bw295-services-across-trees.txt", "head=1d56fad389"),
    "tree_b": (GOZERO + "/bw295-services-across-trees.txt", "head=88b891d22c"),
    "tree_c": (GOZERO + "/bw295-services-across-trees.txt", "head=dea0328e0b"),
    "shape_rule": ("trial/human_walk/_cmdr_bare_english_refusals_r293.py", "def detail_shape"),
    "shape_gate": ("trial/human_walk/_cmdr_bare_english_refusals_r293.py", "cannot separate"),
    "origin_rule": ("trial/human_walk/_cmdr_message_key_origin_r296.py", "WRITE_MARKS = "),
    "wrapper_src": ("backend/app/main.py", '"message_key": message_key or f"error.{code.lower()}"'),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.27 补（10-29 午）"),
}


def line_of(rel, needle):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact does not exist: %s" % rel)
    hits = [index + 1 for index, row in enumerate(
        io.open(path, encoding="utf-8", errors="replace").read().split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s; refusing to write a number "
                         "whose coordinate is not unique" % (needle[:40], len(hits), rel))
    return hits[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.28 补" in text:
        print("ABORT the section is already appended")
        return 4

    g = GOZERO + "/"
    block = "\n".join([
        "14.28 补（10-29 午）：「屏上拿到英文原句」有了分母，而那条键根本不是给句子配的",
        "",
        "- 分母（回执 %s:%d、%s）：backend/app 下 238 枚模块、HTTPException 共 1187 处；"
        "尺 trial/human_walk/_cmdr_bare_english_refusals_r293.py 用 ast 逐枚解析、不靠字面 grep。"
        % (g + "bw293-bare-english-refusals.txt", at["denom"],
           "同回执 :%d 分桶为纯码 738 处、英文句 333 处、码＋句混写 32 处、运行时拼装 77 处、其它 7 处"
           % at["buckets"]),
        "- 载荷形状那一格（%s:%d 与 :%d）：明文串 1110 处、dict 但没带 message_key 6 处、"
        "运行时拼 71 处，**带自己键的 0 处**；333 处英文句里带键的也是 0 处（:%d）。"
        "§14.27 那一格只是这 333 处里被真按到的一例。"
        % (g + "bw293-bare-english-refusals.txt", at["shapes"], at["english_shape"],
           at["english_shape"]),
        "- 屏上那条 key 的真实产地（尺 trial/human_walk/_cmdr_message_key_origin_r296.py:%d）："
        "统一出口 backend/app/main.py:%d 写的是 `message_key or f\"error.{code.lower()}\"` —— "
        "raise 处不传键时按 HTTP 码**拼一个通用键**。回执 %s:%d 列出这类拼键点共 23 行、"
        "%s:%d 判「键写在 raise 之外的地方」。后果是前端可本地化的粒度等于状态码，不等于这条拒绝："
        "光 409 就把好几句不同的话并成同一个 request.conflict（%s:%d 是本机真读到的那一例）。"
        % (at["origin_rule"], at["wrapper_src"],
           g + "bw296-where-the-message-key-comes-from.txt", at["produced"],
           g + "bw296-where-the-message-key-comes-from.txt", at["verdict"],
           g + "bw293-bare-english-refusals.txt", at["named"]),
        "- 一处撤回，按口径发新条不改旧文：本班先前在会话里报过「全库带 message_key 的只有 30 处」，"
        "那个数从未落进任何回执——它来自一段被截断的终端回显。落盘重算的真读数是 0 处"
        "（%s:%d 与 :%d），先前那句作废。同一段回显还让我把「尺算了却没打印」当成「尺已发布」："
        "第一版入库的尺确实算了形状却没输出行，补上输出重跑才落成现在这份回执"
        "（输出闸在 trial/human_walk/_cmdr_bare_english_refusals_r293.py:%d，"
        "分辨不出三桶就不发布数字）。"
        % (g + "bw293-bare-english-refusals.txt", at["shapes"], at["conclusion"], at["shape_gate"]),
        "- 顺带钉住另一处同源误读：先前一段截断输出看着像 backend/app/services.py 的 141-148 行把拒语句"
        "粘进了 docstring。按字节现读三棵现役树（%s:%d、:%d、:%d 三行同为 sha256 前缀 8de56c8e981f、"
        "126757 字节）：拒语句只在 746/782/787/789/799，141-148 行是表名字符串，三棵都能 ast 编译。"
        "文件没坏、也没被本班动过一个字节。"
        % (g + "bw295-services-across-trees.txt", at["tree_a"], at["tree_b"], at["tree_c"]),
        "- 待裁与先前那条并成一串（本班 0 改产品字节、不代裁）：除了 §14.27 那三件，多一件——"
        "要不要让这 333 处英文句在 raise 处就带上各自的具名键（带上才谈得上中文；"
        "现状是按码拼键，同码不同句共用一键）。",
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.28 补")
    print("APPENDED bytes_added=%d heading_hits=%d prev_section_line=%d"
          % (len(block.encode("utf-8")), hits, at["prev_section"]))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
