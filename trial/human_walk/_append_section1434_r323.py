"""Append section 14.34: which of bw318's 20 caller rows sit on a panel the registry actually mounts.

Every figure, including the ruler's own two earlier readings, is parsed out of the bw322 receipt while
this runs, and the row count is checked against bw318's published caller_found, so this section cannot
describe a different set than the ruler above it or flatter its own history.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW322 = GOZERO + "/bw322-which-panel-asks.txt"
BW318 = GOZERO + "/bw318-which-of-these-has-a-button.txt"

CITES = {
    "same_source": (BW322, "SAME-SOURCE CHECK caller rows read from bw318"),
    "tally": (BW322, "TALLY on_a_mounted_panel="),
    "mount_table": (BW322, "MOUNT_TABLE the registry imports"),
    "concentration": (BW322, "MOUNTED_CONCENTRATION"),
    "match": (BW322, "REGISTRY_MATCH"),
    "revision": (BW322, "REVISION this ruler was published"),
    "counting": (BW322, "COUNTING_RULE"),
    "coverage": (BW322, "COVERAGE_LIMIT"),
    "control": (BW322, "NEGATIVE_CONTROL"),
    "uniqueness": (BW322, "NAME_UNIQUENESS"),
    "row_self_mounted": (BW322, "此行构建的文件本身就被注册表渲染"),
    "row_moved": (BW322, "stay-options/{option_id}/mode"),
    "bw318_tally": (BW318, "TALLY caller_found="),
    "ruler": ("trial/human_walk/_cmdr_panel_ask_r322.py", "def registry_panels"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.33 补（10-29 午后）"),
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

    tally = row(BW322, at["tally"])
    slots = re.findall(r"=(\d+)", tally)
    if len(slots) != 6:
        raise SystemExit("ABORT the bw322 TALLY does not read as six numbers: %r" % tally)
    mounted, shell, off, shared, none, rows = [int(value) for value in slots]
    caller_found = int(re.findall(r"=(\d+)", row(BW318, at["bw318_tally"]))[0])
    if rows != caller_found:
        raise SystemExit("ABORT bw322 covers %d rows against bw318's caller_found of %d"
                         % (rows, caller_found))
    if mounted + shell + off + shared + none != rows:
        raise SystemExit("ABORT the verdicts %d+%d+%d+%d+%d do not cover %d"
                         % (mounted, shell, off, shared, none, rows))

    table = row(BW322, at["mount_table"])
    imported, rendered = [int(value) for value in
                          re.search(r"imports (\d+) module\(s\) and renders (\d+)", table).groups()]
    conc = row(BW322, at["concentration"])
    files_on_panel = int(re.search(r"rest on (\d+) distinct", conc).group(1))
    pairs = re.findall(r"([\w/.-]+)=(\d+)", conc)
    carried = sum(int(value) for _, value in pairs)
    if carried != mounted:
        raise SystemExit("ABORT the concentration line carries %d rows against a mounted count of %d"
                         % (carried, mounted))
    if len(pairs) != files_on_panel:
        raise SystemExit("ABORT the concentration line names %d files against its own count of %d"
                         % (len(pairs), files_on_panel))

    revision = row(BW322, at["revision"])
    history = re.search(r"a mount and read (\d+); v2 .*?themselves and read (\d+); v3 .*?"
                        r"itself mounted, reading (\d+); v4 moved row\(s\) ([\w, ]+?) out of", revision)
    if not history:
        raise SystemExit("ABORT the REVISION line does not read as the three earlier counts: %r"
                         % revision[:120])
    v1, v2, v3, moved = history.group(1), history.group(2), int(history.group(3)), history.group(4).strip()
    if v3 != mounted:
        raise SystemExit("ABORT REVISION says v3 read %d while the TALLY reads %d mounted" % (v3, mounted))

    unique = row(BW322, at["uniqueness"])
    shared_name, named_rows = [int(value) for value in re.search(r"^NAME_UNIQUENESS (\d+) of (\d+)",
                                                                 unique).groups()]
    if named_rows != rows:
        raise SystemExit("ABORT NAME_UNIQUENESS counts %d rows against the TALLY's %d"
                         % (named_rows, rows))
    print("LIVE NUMBERS rows=%d mounted=%d shell=%d off=%d shared=%d none=%d imported=%d rendered=%d "
          "history=%s>%s>%s moved=%s"
          % (rows, mounted, shell, off, shared, none, imported, rendered, v1, v2, v3, moved))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.34 补" in text:
        print("ABORT the section is already appended")
        return 4

    named = "、".join("`%s`（%s 处）" % (rel, value) for rel, value in pairs)
    block = "\n".join([
        "14.34 补（10-29 午后）：%d 处调用者里 %d 处落在注册表渲染的面板上，而它们只集中在 %d 枚面板"
        % (rows, mounted, files_on_panel),
        "",
        "- 这一腿接 §14.33 留下的那句待裁（其正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d）："
        "把 %d 处有调用者的接成「哪个面板会发这一句」。尺 trial/human_walk/_cmdr_panel_ask_r322.py:%d "
        "里「挂上面板」的定义是注册表 import 了该模块、且把它当 JSX 组件渲染，两条都要成立；"
        "只看使用者不够——该行构建文件自己就是被渲染的那个组件时也算"
        "（回执 %s:%d 那一行标了这种行）。"
        % (at["prev_section"], rows, at["ruler"], BW322, at["row_self_mounted"]),
        "- 读数（回执 %s:%d，行数与 %s:%d 的 caller_found 同源对账）：%d 处落在挂得上注册表的面板、"
        "%d 处由 app/ 壳自己发、%d 处由注册表从不渲染的组件发、%d 处只剩共用 API 层、%d 处无人问。"
        % (BW322, at["tally"], BW318, at["bw318_tally"], mounted, shell, off, shared, none),
        "- 集中度才是这一格要看的数（回执 %s:%d）：%d 处只压在 %d 枚文件上——%s。"
        "注册表 import %d 枚模块、渲染其中 %d 枚（回执 %s:%d），所以面板名录本身比行数更有用。"
        % (BW322, at["concentration"], mounted, files_on_panel, named, imported, rendered,
           BW322, at["mount_table"]),
        "- 同一把尺改了四遍，读数跟着动（回执 %s:%d 逐档写明原因）：%s→%s→%s，第四遍把第 %s 行从「无人问」"
        "改判成应用壳。第一版把注册表里任何文字（含注释）当挂载；第二版只认 import 边、"
        "漏掉「构建文件本身就是被渲染的组件」；第三版要求 import 加 JSX；第四版承认"
        "「路径在 app/ 文件里就地拼出来，别处永远不可能提到那个局部名字」这种沉默不说明没人问。"
        "定义写在回执 %s:%d，所以这几个数必须连着定义读。被改判那行见回执 %s:%d。"
        % (BW322, at["revision"], v1, v2, v3, moved, BW322, at["counting"], BW322, at["row_moved"]),
        "- 另有一条判别臂专治「文字算成挂载」（回执 %s:%d）：注册表文字里出现、却没有 import 边的模块"
        "被点名剔掉，import 了却从不渲染的也算不上面板。自疑两臂（回执 %s:%d、%s:%d）：整名搜索换一个"
        "谁都没定义的名字必须命中 0 枚文件；%d 行共用同一个函数名是实测数，不是我把共用对象当成了调用者。"
        % (BW322, at["match"], BW322, at["control"], BW322, at["uniqueness"], shared_name),
        "- 这把尺不能说的那句话（不替它补）：注册表渲染 ≠ 旅客会打开那一屏，整名命中 ≠ 真发生了调用"
        "（注释与再导出都算）。极限写在回执 %s:%d——它只把「哪几屏可能显出这句英文」收窄，"
        "代替不了真走一遍。" % (BW322, at["coverage"]),
        "- 待裁（不代裁）：文案刀由此多了一档切法——按面板切，先切承载这 %d 处的那两枚"
        "（见上行具名文件），还是照 §14.32 的三档按 21 / 45 / 132 处切；两档都要先定 §14.31 那句"
        "大小写口径。本班 0 改产品字节。" % mounted,
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    crlf = back.count("\r\n")
    hits = back.count("14.34 补")
    print("APPENDED bytes_added=%d heading_hits=%d crlf_lines_now=%d" % (
        len(block.encode("utf-8")), hits, crlf))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
