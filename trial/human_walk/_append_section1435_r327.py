"""Append section 14.35: whether the traveller-facing English can reach the screen at all.

Every figure is parsed from the bw325 and bw326 receipts while this runs, cross-checked inside each
receipt (verdicts against rows, reads plus hides against catch bodies), so the section cannot repeat a
number its own artifacts do not carry.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW325 = GOZERO + "/bw325-what-the-screen-says.txt"
BW326 = GOZERO + "/bw326-what-the-panels-do-with-a-refusal.txt"

CITES = {
    "tally_325": (BW325, "TALLY shows_server_text="),
    "split_325": (BW325, "MOUNTED_SPLIT of the"),
    "controls_325": (BW325, "CONTROLS"),
    "coverage_325": (BW325, "COVERAGE_LIMIT"),
    "counting_325": (BW325, "COUNTING_RULE"),
    "denom_326": (BW326, "DENOMINATOR the registry imports"),
    "tally_326": (BW326, "TALLY panels="),
    "site_326": (BW326, "READS_THE_REFUSAL_AT"),
    "drops_326": (BW326, "READS_BUT_DROPS"),
    "wide_326": (BW326, "WIDE_PATTERN_CHECK"),
    "nocatch_326": (BW326, "NO_CATCH_AT_ALL"),
    "coverage_326": (BW326, "COVERAGE_LIMIT"),
    "hook_site": ("frontend/src/app/V8Experience.tsx", "useCandidateRejections(data.journey.id"),
    "own_words": ("frontend/src/features/execution/LiveRecovery.tsx", "无法记录这个选择"),
    "shell_throw": ("frontend/src/app/V8Experience.tsx", "rejectionReason(body, response.status)"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.34 补（10-29 午后）"),
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

    shows, owns, nocatch, rows = [int(v) for v in re.findall(r"=(\d+)", row(BW325, at["tally_325"]))]
    if shows + owns + nocatch != rows:
        raise SystemExit("ABORT bw325 verdicts %d+%d+%d do not cover %d" % (shows, owns, nocatch, rows))
    mounted_rows, mounted_shows, mounted_owns, mounted_nocatch = [
        int(v) for v in re.findall(r"(\d+)", row(BW325, at["split_325"]))]
    if mounted_shows + mounted_owns + mounted_nocatch != mounted_rows:
        raise SystemExit("ABORT bw325's mounted split does not cover the mounted rows")

    panels, caught, reads, hides = [int(v) for v in re.findall(r"=(\d+)", row(BW326, at["tally_326"]))]
    if reads + hides != caught:
        raise SystemExit("ABORT bw326 reads %d plus hides %d is not the catch count %d"
                         % (reads, hides, caught))
    denom = row(BW326, at["denom_326"])
    shape = re.search(r"imports (\d+) module\(s\), (\d+) of them rendered.*?so (\d+) mounted files.*?"
                      r"names (\d+) components", denom)
    if not shape:
        raise SystemExit("ABORT the bw326 denominator line does not read: %r" % denom[:120])
    imported, mounted_files, panels_read, jsx_names = [int(v) for v in shape.groups()]
    if mounted_files != panels_read or panels_read != panels:
        raise SystemExit("ABORT bw326 denominator reads %s/%s against a TALLY of %d panels"
                         % (mounted_files, panels_read, panels))
    wide = int(re.search(r"read the refusal (\d+) time", row(BW326, at["wide_326"])).group(1))
    if wide != reads:
        raise SystemExit("ABORT the loose pattern found %d against the strict pattern's %d" % (wide, reads))
    drops = row(BW326, at["drops_326"])
    tells = re.findall(r"the body says at `([^`]+?):(\d+)`", drops)
    if not tells:
        raise SystemExit("ABORT the READS_BUT_DROPS line names no statement coordinate: %r" % drops[:120])
    drop_file, drop_line = tells[0][0], int(tells[0][1])
    no_catch_files = int(re.search(r"NO_CATCH_AT_ALL (\d+) of the", row(BW326, at["nocatch_326"])).group(1))
    live_row = next((index + 1 for index, cell in enumerate(read(BW326).split("\n"))
                     if cell.strip().startswith("frontend/src/features/execution/LiveRecovery.tsx")), 0)
    live_caught = int(re.search(r"catch (\d+) 处", row(BW326, live_row)).group(1))
    print("LIVE NUMBERS rows=%d shows=%d owns=%d nocatch=%d | panels=%d catch=%d reads=%d hides=%d "
          "wide=%d live_catch=%d no_catch_files=%d drop_at=%s:%d"
          % (rows, shows, owns, nocatch, panels, caught, reads, hides, wide, live_caught,
             no_catch_files, drop_file, drop_line))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.35 补" in text:
        print("ABORT the section is already appended")
        return 4

    block = "\n".join([
        "14.35 补（10-29 夜）：那 %d 处旅客面英文在这 %d 条调用路上没有一条已知能上屏——面板先把话换掉了"
        % (reads, rows),
        "",
        "- 为什么要再两把尺：§14.34 说 %d 处挂在注册表渲染的面板上，但「面板会发」不等于「屏上显这句」。"
        "中间那层是 catch。尺 trial/human_walk/_cmdr_screen_text_r325.py 从面板自己的调用处走向接住它的 "
        "catch，看它读不读 error；尺 trial/human_walk/_cmdr_panel_habit_r326.py 不再按请求回答，改成按文件"
        "回答——把注册表 import 且渲染的 %d 枚模块整个读一遍。" % (mounted_rows, panels),
        "- 按请求的读数（回执 %s:%d、%s:%d）：%d 处由面板自己造句子、%d 处窗内没有 catch、%d 处显服务端原文。"
        "只看挂在面板上那 %d 处也是同一个形状：%d 造句子、%d 无 catch、%d 显原文。"
        % (BW325, at["tally_325"], BW325, at["split_325"], owns, nocatch, shows, mounted_rows,
           mounted_owns, mounted_nocatch, mounted_shows),
        "- 按面板的读数（回执 %s:%d）：%d 枚面板共 %d 处 catch，读 error 的 %d 处、从不碰 error 的 %d 处；"
        "单是 `frontend/src/features/execution/LiveRecovery.tsx` 一枚文件就占 %d 处 catch（回执 %s:%d）。"
        "另有 %d 枚面板整个文件没有 catch，拒绝不归它管（回执 %s:%d）。分母同源：注册表 import %d 枚、"
        "其中 %d 枚确被当组件渲染，回执另点明文件里 JSX 组件名共 %d 个，比模块数宽，别再混着念。"
        % (BW326, at["tally_326"], panels, caught, reads, hides, live_caught, BW326, live_row,
           no_catch_files, BW326, at["nocatch_326"], imported, mounted_files, jsx_names),
        "- 唯一读 error 的那处也不算上屏（回执 %s:%d 点名 `%s:%d`）：它在那里读 `cause.message`，而同一文件 :%d "
        "的注释自己写明匹配的是机器码、句子是被丢掉的；回执把这条写成 READS_BUT_DROPS（%s:%d），不是我口头补的。"
        % (BW326, at["site_326"], drop_file, drop_line, drop_line, BW326, at["drops_326"]),
        "- 这数不是我挑正则挑出来的（回执 %s:%d）：把判据放宽成 `.message`/`.detail`/`instanceof Error 或 "
        "V8Rejection`/`String(err)`/`as Error).message`，命中数仍是 %d——与严格判据同数。控制三枚都取自源码本身"
        "（回执 :%d）：一处真读 error 的、一处全文件无 catch 的、一处明知故写自己句子的；任一不合就 ABORT。"
        % (BW326, at["wide_326"], reads, at["controls_325"]),
        "- 我这一腿自己改过三处，都记在回执里而不是私下改：窗口起点原本开在「URL 写在哪一行」，而那行多数在 "
        "frontend/src/api/ 里、后面根本没有调用方的 catch，于是 %d 行报了「窗内无 catch」；控制点原本瞄在一行"
        "已经位于 catch 内部的坐标上，自己把自己 ABORT 掉（rc=7）；bw326 的分母一度写成「渲染 25 中的 33 枚」，"
        "33 其实是文件里 JSX 组件名的数，比模块数宽。站点选取规则见回执 %s:%d。"
        % (nocatch, BW325, at["counting_325"]),
        "- 屏上真正会说什么，举一枚现读的例子：LiveRecovery.tsx:%d 的 catch 不论服务端说了什么都答"
        "「无法记录这个选择，请刷新后重试。」；而 %d 行「无 catch」那几处是渲染期 hook（"
        "frontend/src/app/V8Experience.tsx:%d 的 `data ?? []`），失败时连句子都没有，只剩空列表。"
        % (at["own_words"], nocatch, at["hook_site"]),
        "- 这把尺不能说的那句话（不替它补）：接住不等于显示——读了 error 又丢掉的也算「读」；拒绝若在共用 hook "
        "或应用壳的抛出路径（frontend/src/app/V8Experience.tsx:%d 把 `body.detail` 装进抛出消息）里被处理，"
        "本尺不记在那枚面板头上。极限写在回执 %s:%d 与 %s:%d。"
        % (at["shell_throw"], BW325, at["coverage_325"], BW326, at["coverage_326"]),
        "- 待裁（不代裁，这条改了「先动哪一侧」的算式）：§14.30–§14.32 那 %d 处旅客面英文拒绝句，在本班量到的 "
        "%d 条调用路上没有一条已知能到屏；今天在这些路上可证的是另一件缺陷——面板不论服务端说什么都给同一句"
        "「刷新后重试」，把拒绝理由整条吞掉。要按这条开单（读侧已备：%d 处 catch 具名可查），还是仍按 §14.32 "
        "的三档先动后端文案，请点。本班 0 改产品字节。" % (rows, rows, caught),
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    bare = back.count("\n") - back.count("\r\n")
    hits = back.count("14.35 补")
    print("APPENDED bytes_added=%d heading_hits=%d bare_lf_now=%d"
          % (len(block.encode("utf-8")), hits, bare))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
