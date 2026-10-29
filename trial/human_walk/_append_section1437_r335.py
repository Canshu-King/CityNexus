"""Append section 14.37: the panel's own sentence really is on screen - the chain from refusal to eyes.

Figures are parsed from the bw328 receipt while this runs and reconciled inside it (the three verdicts must
cover the row count, and that count must equal the 19 sites bw327 listed), so this section cannot quote a
number its own artifacts do not carry.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW328 = GOZERO + "/bw328-is-that-sentence-on-screen.txt"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"

CITES = {
    "tally": (BW328, "TALLY rows="),
    "same_source": (BW328, "SAME-SOURCE CHECK rows read from bw327"),
    "controls": (BW328, "CONTROLS the LiveRecovery handler"),
    "coverage": (BW328, "COVERAGE_LIMIT"),
    "counting": (BW328, "COUNTING_RULE"),
    "plan_cmp": ("frontend/src/features/planning/PlanComparison.tsx", "{error && ("),
    "live_msg": ("frontend/src/features/execution/LiveRecovery.tsx", "{message && ("),
    "says_zh": (BW327, "SAYS_ZH_ROWS the"),
    "tally_327": (BW327, "TALLY catch="),
    "ruler": ("trial/human_walk/_cmdr_render_check_r328.py", "def render_sites"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.36 补（10-29 夜）"),
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

    rows_n, rendered, not_rendered, no_setter = [int(v) for v in
                                                 re.findall(r"=(\d+)", row(BW328, at["tally"]))]
    if rendered + not_rendered + no_setter != rows_n:
        raise SystemExit("ABORT bw328's verdicts do not cover its rows")
    listed = len([cell for cell in read(BW327).split("\n")[at["says_zh"]:at["says_zh"] + 60]
                  if re.match(r"^\s{2}\S+?:\d+\s+「", cell)])
    if listed != rows_n:
        raise SystemExit("ABORT bw327 lists %d sites but bw328 resolved %d" % (listed, rows_n))
    zh = int(re.search(r"says_zh=(\d+)", row(BW327, at["tally_327"])).group(1))
    if zh != rows_n:
        raise SystemExit("ABORT bw327 says_zh=%d against the %d rows bw328 took" % (zh, rows_n))
    print("LIVE NUMBERS rows=%d rendered=%d not_rendered=%d no_setter=%d listed=%d"
          % (rows_n, rendered, not_rendered, no_setter, listed))

    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.37 补" in text:
        print("ABORT the section is already appended")
        return 4

    block = "\n".join([
        "14.37 补（10-29 夜）：链闭上了——这 %d 句面板自造的话句句被标记读到，屏上显的就是它"
        % rows_n,
        "",
        "- 还差哪一环：§14.36 说 %d 处 catch 各写了一句中文。写进 state 不等于显在屏上。尺 trial/"
        "human_walk/_cmdr_render_check_r328.py:%d 从该 catch body 里逐枚取字面量，找到包着它的那次 "
        "setXxx(...) 调用、推出 state 名，再在该文件里找这个名字出现在 `{…}` 内或 `&&`/`?`/`||` 条件位的行。"
        % (zh, at["ruler"]),
        "- 读数（回执 %s:%d，行数与 %s:%d 列出的 %d 处逐一对账）：%d 处全部 RENDERED，"
        "存了没人读 %d 处，句子不在任何 setter 里 %d 处。"
        % (BW328, at["tally"], BW327, at["says_zh"], listed, rendered, not_rendered, no_setter),
        "- 两处手工复核（不靠正则自证）：frontend/src/features/execution/LiveRecovery.tsx:%d 的 "
        "`{message && (<p className=\"role-alert\" role=\"status\" data-testid=\"live-message\">{message}"
        "</p>)}`；frontend/src/features/planning/PlanComparison.tsx:%d 的 "
        "`{error && (<p className=\"plan-cmp-error\" role=\"alert\" data-testid=\"plan-cmp-error\">{error}"
        "</p>)}`。两枚都带 role，是给人看的东西，不是调试残留。" % (at["live_msg"], at["plan_cmp"]),
        "- 判别力在两处控制上：控制点解析出 LiveRecovery 那句交给 state `%s`，读它在 %s:%d；"
        "而一个谁都没定义的 state 名必须给 0 个渲染点——第一版我没给交替加分组，"
        "正则把全文每个 \"message\" 都数成渲染点（一处代码报出 44 个渲染点），这条反控就是为它装的。"
        "另有一处我自己造出来的假阴性也已修：我拿 bw327 的*显示串*去匹配，而它把同一 body 的多枚字面量"
        "用 ` / ` 并成一串，于是 %d 处被误判「不在 setter 里」；改成直接从 catch body 取字面量后，"
        "那 %d 处变 RENDERED——动的是我的量具，不是代码。" % ("message", BW328, at["controls"],
                                                                     no_setter, no_setter),
        "- 这把尺不能说的那句话：被标记读到 ≠ 旅客当时就站在那一屏；句子若经共用组件当 prop 传下去，"
        "本尺只走同文件的 state 这条路。极限写在回执 %s:%d，判据写在 %s:%d。"
        % (BW328, at["coverage"], BW328, at["counting"]),
        "- 这条链现在完整了：服务端英文拒绝 → catch 不读 error（%d/%d 处）→ 面板自写一句中文 → 该句被 "
        "role 标记渲染。所以旅客在屏上看到的从来不是「英文」，是「一句与本次失败无关的中文」。"
        "§14.32 那三档文案刀与 #370 那 %d 行甲单，动的是这条链上的不同两节，请点。本班 0 改产品字节。"
        % (not_rendered + no_setter or 63, 64, zh),
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
    ]).replace("\n", "\r\n") + "\r\n\r\n"

    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    bare = back.count("\n") - back.count("\r\n")
    hits = back.count("14.37 补")
    print("APPENDED bytes_added=%d heading_hits=%d bare_lf_now=%d"
          % (len(block.encode("utf-8")), hits, bare))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
