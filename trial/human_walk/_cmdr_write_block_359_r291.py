"""Build the ledger block for #359, reading every coordinate live from the artifacts.

The Q43 door refuses a block whose line numbers were written from memory, and this shift has been
bitten twice by exactly that.  So this generator re-reads each cited file at invocation time,
asserts the anchor is where it claims to be, and only then emits the block - plus the verbatim
closing line taken from live_checks/CLOSING_LINE.txt, which the applier checks.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
GOZERO = "trial/results/20261026_gozero"
OUT = r"D:\moodle\_qoder_ledger_inbox\494abfd7_0439.md"

REJECT_LINES = re.compile(r"^ *return UNRESOLVED_ACTIVITY_FACTS$", re.M)


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle, expect=1):
    """Return the 1-based line number of a unique literal anchor."""
    lines = read(rel).split("\n")
    hits = [index + 1 for index, text in enumerate(lines) if needle in text]
    if len(hits) != expect:
        raise SystemExit("ABORT anchor %r found %d times in %s (expected %d)"
                         % (needle[:40], len(hits), rel, expect))
    return hits[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    report = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
    bw285 = GOZERO + "/bw285-accept-without-select.txt"
    bw288 = GOZERO + "/bw288-accept-with-frozen-evidence.txt"
    bw289 = GOZERO + "/bw289-why-evidence-cannot-freeze.txt"
    handoff = "trial/results/20261029_HANDOFF_GO_FROM_BLANK_r185.md"
    main_py = "backend/app/main.py"
    services_py = "backend/app/services.py"

    refuse_hits = [index + 1 for index, text in enumerate(read(services_py).split("\n"))
                   if REJECT_LINES.match(text)]
    if len(refuse_hits) != 5:
        raise SystemExit("ABORT the shared blocker now refuses at %d sites, not five - "
                         "re-read the section before citing" % len(refuse_hits))
    # §14.19 attributed the suite reds to the last of those sites; cite that one by position
    refuse = refuse_hits[-1]

    anchors = {
        "section": line_of(report, "14.27 补（10-29 午）"),
        "arm1": line_of(bw285, "ARM1 http_status=409"),
        "no_ask": line_of(bw285, "SHARED_BLOCKER_ASKED_DURING_ACCEPT NO"),
        "control": line_of(bw285, "control: shared blocker asked directly"),
        "walk_zero": line_of(bw288, "SHARED_BLOCKER_ASKED_DURING_WALK NO"),
        "no_new_plan": line_of(bw288, "ACCEPT_LANDED_A_NEW_PLAN_IN_A_DEPARTURE_STATE NO"),
        "no_facts": line_of(bw288, "ACCEPT_GATE_LOOKED_AT_PLACE_FACTS NO"),
        "thirty": line_of(bw289, "ORIGINAL: mobility_facts rows="),
        "endpoints": line_of(bw289, "ORIGINAL: first evidence endpoint ids="),
        "zero": line_of(bw289, "ORIGINAL: INTERSECT used place ids with mobility_fact endpoints = 0"),
        "bites": line_of(bw289, "RULER_BITES_ON_THE_COPY YES"),
        "raise409": line_of(main_py, 'raise HTTPException(409, "Trip Studio requires an active plan")'),
        "gate_doc": line_of(main_py, '"""Run the shared deterministic gate over a Trip Studio frozen snapshot."""'),
        "currency": line_of(main_py, 'failures.append(f"MOBILITY_CURRENCY_MISMATCH:{from_key}|{to_key}")'),
        "refuse": refuse,
        "handoff": line_of(handoff, "所以「零事实」是**还没捕**"),
    }
    print("ANCHORS %s" % anchors)

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    obj = subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha],
                         capture_output=True, text=True, check=True).stdout.strip()
    if obj != "commit":
        raise SystemExit("ABORT the generation object is not a commit: %s" % obj)

    closing = io.open(os.path.join(REF, "live_checks", "CLOSING_LINE.txt"),
                      encoding="utf-8").read().strip()
    if not closing or "\n" in closing:
        raise SystemExit("ABORT the closing line is unusable")

    a = anchors
    body = "\n".join([
        "### 494abfd7 交「接受那一按全程没问共享门」的现场读数与三件待裁（#359）",
        "",
        "- 走法（真路由、临时库，本班 0 改产品字节）：demo/reset → 建行程 → 房价捕获 → 住下方案生成 → "
        "住下选用 → 按「接受」换序；追踪器把每一次作答都记全、不只记拒绝，"
        "尺 trial/human_walk/_cmdr_accept_without_select_r285.py:56。",
        "- 读数壹（行程还没选过任何方案就按接受）：服务端回 409，给旅客的那句是英文原句 "
        "`Trip Studio requires an active plan`（backend/app/main.py:%d 抛出，回执 %s:%d 那行），"
        "message_key 只有通用的 request.conflict——屏上没有中文说法接它。"
        % (a["raise409"], bw285, a["arm1"]),
        "- 读数贰（本节主干）：整条接受路上共享权威门被问 0 次（%s:%d、%s:%d）；"
        "同一进程里直接拿同一枚方案问那扇门，它当场拒（backend/app/services.py:%d 那一条 return，"
        "用到 9 处地点、9 处内容地点，见 %s:%d 这行）。"
        % (bw285, a["no_ask"], bw288, a["walk_zero"], a["refuse"], bw285, a["control"]),
        "- 读数叁（它自己那扇门判什么）：自述是「over 一份冻结快照跑共享确定性门」（backend/app/main.py:%d），"
        "逐条判据直到 backend/app/main.py:%d 全是快照身份、完整性、过期、逐段分钟、货币与时间，"
        "对地点的营业与费用事实 0 处提及（%s:%d）。所以 §14.21 那张表里「接受」这一行是"
        "看得见一扇门、但不是同一扇门。" % (a["gate_doc"], a["currency"], bw288, a["no_facts"]),
        "- 读数肆（换成矩阵齐的城也一样）：CN-BEIJING 仍停在 503，接受没造出任何新方案（%s:%d）。"
        "本班这一格先前读反过一次：仪表把「那枚方案本来就 ACTIVE」当成「接受把它推成 ACTIVE」，"
        "改判定式为「只认接受自己产出的方案」后重跑才落定。" % (bw288, a["no_new_plan"]),
        "- 读数伍（冻不出证据的成因）：那枚临时库里 mobility_facts 实有 30 行、全挂在这枚行程上"
        "（%s:%d），可证据的端点键是 arrival-…／stay:bei… 这一类锚与住下报价键（同回执 :%d），"
        "而方案活动用的是 UUID 形状的 place_id，两者交集 0（同回执 :%d）。正对照：同一把尺往自己的"
        "副本里灌 1 行、端点就用方案真用的那两枚 place_id，交集立刻从 0 变 2"
        "（同回执 :%d RULER_BITES_ON_THE_COPY YES）——那个 0 是库里的事实，不是尺接不上。"
        % (bw289, a["thirty"], a["endpoints"], a["zero"], a["bites"]),
        "- 口径收窄一处，不发全表式勘误：交接稿 %s:%d 那句「零事实是还没捕、不是捕不到」，"
        "在住下这条路上要读成「捕了，但端点键与方案不同源，所以对这版方案不可用」；课堂栈那枚"
        "「两张表总行数现读为零」是另一枚库、另一条路径的读数，不改口。" % (handoff, a["handoff"]),
        "- 待裁三件（本班不代裁）：壹，「接受」要不要也过共享权威门——现在它只过证据门，证据一齐"
        "就能把地点事实仍未决的方案写进出发态；贰，冻结证据的端点键是否统一到 place_id（不统一则"
        "住下生成的方案永远冻不出证据，「按这一版安排」这类操作对旅客永久不可达）；叁，409 那句"
        "英文原句与内部术语是否端给旅客。",
        "- 落点与代次：正文在 %s:%d；本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。"
        % (report, a["section"], sha),
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
