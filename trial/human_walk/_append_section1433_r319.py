"""Append section 14.33: whether anything in the frontend actually asks for those 21 paths.

Every figure is parsed from bw318 while this runs, and the row count is checked against bw313's published
intersection so the two rulers cannot drift apart.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW318 = GOZERO + "/bw318-which-of-these-has-a-button.txt"
BW313 = GOZERO + "/bw313-traveller-side-and-internal-vocabulary.txt"

CITES = {
    "denominator": (BW318, "DENOMINATOR rows read out of bw313"),
    "tally": (BW318, "TALLY caller_found="),
    "negative": (BW318, "NEGATIVE_CONTROL"),
    "counting": (BW318, "COUNTING_RULE"),
    "coverage": (BW318, "COVERAGE_LIMIT"),
    "no_caller": (BW318, "NO_FRONTEND_CALLER"),
    "first_caller": (BW318, "frontend/src/api/citynexus.ts:3457"),
    "ruler": ("trial/human_walk/_cmdr_button_reachability_r318.py", "def tail_segments"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.32 补（10-29 午后）"),
    "bw313_intersection": (BW313, "INTERSECTION the job"),
}


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


def row(rel, line):
    return read(rel).split("\n")[line - 1]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    denominator_row = row(BW318, at["denominator"])
    published_rows = int(re.search(r"bw313 = (\d+)", denominator_row).group(1))
    scanned = int(re.search(r"scanned = (\d+)", denominator_row).group(1))
    caller_found, no_caller, total = [int(v) for v in
                                      re.findall(r"=(\d+)", row(BW318, at["tally"]))]
    intersection_match = re.search(r"would actually touch: (\d+)", row(BW313, at["bw313_intersection"]))
    if not intersection_match:
        raise SystemExit("ABORT the bw313 intersection row does not read as expected")
    intersection = int(intersection_match.group(1))
    if published_rows != intersection or total != intersection:
        raise SystemExit("ABORT bw318 scanned %d rows, bw313 published an intersection of %d"
                         % (total, intersection))
    if caller_found + no_caller != total:
        raise SystemExit("ABORT the tally %d+%d does not cover %d" % (caller_found, no_caller, total))
    no_caller_line = row(BW318, at["no_caller"])
    url_match = re.search(r"(/\S+)", no_caller_line)
    backend_match = re.search(r"(backend/\S+?:\d+)", no_caller_line)
    if not url_match or not backend_match:
        raise SystemExit("ABORT the no-caller row does not read: %r" % no_caller_line[:120])
    print("LIVE NUMBERS rows=%d scanned=%d caller_found=%d no_caller=%d"
          % (total, scanned, caller_found, no_caller))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.33 补" in text:
        print("ABORT the section is already appended")
        return 4

    block = "\n".join([
        "14.33 补（10-29 午后）：%d 处里 %d 处前端确实会问，%d 处没人问——但「会问」不等于「按得到」"
        % (total, caller_found, no_caller),
        "",
        "- 为什么要第四把尺：§14.32 交出 %d 处句子与各自的 URL，却没说旅客按什么键会撞到其中之一。"
        "尺 trial/human_walk/_cmdr_button_reachability_r318.py:%d 读 bw313 的行不重打分母，"
        "在前端手写源码里要求同文件同时出现该路径的最后两段"
        "（拼接 URL 的形制见回执 %s:%d 那一行，所以整串匹配搜不到），"
        "并把生成的 OpenAPI 客户端、测试与 spec 助手排除在外——不排除的话每条路由都会被算成「有按钮」。"
        % (intersection, at["ruler"], BW318, at["first_caller"]),
        "- 读数：前端文件扫 %d 枚（回执 %s:%d 的分母与回执行 %s:%d 同源对账），"
        "%d 处有手写调用者、%d 处没有（回执 :%d 的 TALLY）。"
        "唯一没人问的那处是 %s（%s）——运营口的 replay，不是旅客路径。"
        % (scanned, BW318, at["denominator"], BW313, at["bw313_intersection"],
           caller_found, no_caller, at["tally"], url_match.group(1), backend_match.group(1)),
        "- 反控一格（证这把尺不会什么都说「有」）：拿一条本机不存在的路径同法去查，必须查无命中"
        "（回执 :%d 实测 CLEAN）。口径写在 :%d，能查到的极限写在 :%d。"
        % (at["negative"], at["counting"], at["coverage"]),
        "- 这把尺不能说的那句话（不替它补）：源码里有调用者 ≠ 屏上有一个按得到的按钮——"
        "它只证明「前端某处会发这个请求」。回执里附的中文串取的是同文件 40 行内第一个含汉字的字面量，"
        "可能属于同文件里的另一个控件，所以「屏上会不会被前端自己的中文盖住」这句我没有判，"
        "要判得下一腿走真机或读渲染点。",
        "- 待裁（不代裁）：要不要把这一腿走完——把 %d 处有调用者的接成「哪个面板 / 哪枚按钮 → 哪句英文」，"
        "还是就此按 §14.32 的三档直接点文案刀。本班 0 改产品字节。" % caller_found,
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = back.count("14.33 补")
    print("APPENDED bytes_added=%d heading_hits=%d" % (len(block.encode("utf-8")), hits))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
