"""Append section 14.42 and write ledger block #378 for the classroom generation's cold first screen.

Two things this shift had not yet done: boot the classroom generation from a zero-dirty tree after E filled
up, and read what that screen says to a traveller who has no ticket.  Both are measured here rather than
described - the launcher, the three-viewport walk, the DOM behind the two controls the screenshot raised,
and the backend's own access log for the same requests.

Every coordinate is read off disk at run time, every cited path is checked to exist and to be long enough
to hold the line it names, and the section is appended at byte level so the report's CRLF count cannot move.
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
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPORT_REL = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = "trial/results/20261026_gozero"
BW343 = GOZERO + "/bw343-classroom-cold-first-screen-three-shapes.txt"
BW344 = GOZERO + "/bw344-two-screen-facts-dom.txt"
BW345 = GOZERO + "/bw345-back-link-destination-and-the-corner-circle.txt"
BW346 = GOZERO + "/bw346-cold-screen-requests-and-their-statuses.txt"
BW339 = GOZERO + "/bw339-census-window-old-vs-new-vs-narrow.txt"
BW301 = GOZERO + "/bw301-this-sessions-blocks-landed.txt"
LAUNCHER = "trial/human_walk/_cmdr_boot_d_stack_r355.py"
WALK = "trial/human_walk/_cmdr_classroom_cold_screen_r356.js"
DOMREAD = "trial/human_walk/_cmdr_read_two_screen_facts_r357.js"
CLICKREAD = "trial/human_walk/_cmdr_back_link_and_circle_r358.js"

CITES = {
    "launcher_floor": (LAUNCHER, "FLOOR_GIB = "),
    "launcher_junction": (LAUNCHER, "def junction(target, link)"),
    "walk_viewports": (WALK, "const VIEWPORTS = ["),
    "dom_summary": (BW344, '"parentIsDetails":true'),
    "dom_backlink": (BW344, '"underlined":"underline"'),
    "click_line": (BW345, "CLICK button.trial-back-link"),
    "click_details": (BW345, "details[open] after the click"),
    "ball_aria": (BW345, "cn-sim-ball"),
    "unlabelled": (BW345, "UNLABELLED controls"),
    "log_tally": (BW346, "TALLY distinct_routes="),
    "log_scene": (BW346, "/api/v1/demo/scene"),
    "receipt_tally": (BW343, "TALLY viewports="),
    "receipt_phone": (BW343, "phone_390 "),
    "prev_section": (REPORT_REL, "14.41 补（10-30 凌晨）"),
}


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, cell in enumerate(read(rel).split("\n")) if needle in cell]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    lines = read(rel).split("\n")
    if line > len(lines):
        raise SystemExit("ABORT %s holds %d lines, so :%d names nothing" % (rel, len(lines), line))
    return lines[line - 1]


def measured():
    # search, not findall: a multi-group findall yields tuples of values, which is how a tally dict
    # silently turns into {"3": 0}
    walk = re.search(r"viewports=(\d+) failed=(\d+)", row_at(BW343, line_of(BW343, "TALLY viewports=")))
    log_row = re.search(r"distinct_routes=(\d+) scene_403=(\d+) invitations_401=(\d+)",
                        row_at(BW346, line_of(BW346, "TALLY distinct_routes=")))
    if not walk or not log_row:
        raise SystemExit("ABORT one of the two receipts does not read its own tally line")
    tally = {"viewports": int(walk.group(1)), "failed": int(walk.group(2))}
    log = {"distinct_routes": int(log_row.group(1)), "scene_403": int(log_row.group(2)),
           "invitations_401": int(log_row.group(3))}
    opened = int(re.search(r"details\[open\] after the click: (\d+)",
                           row_at(BW345, line_of(BW345, "details[open] after the click"))).group(1))
    unlabelled = int(re.search(r"UNLABELLED controls \(no text, no aria-label, no title\): (\d+)",
                               row_at(BW345, line_of(BW345, "UNLABELLED controls"))).group(1))
    if tally["failed"] or tally["viewports"] != 3:
        raise SystemExit("ABORT the three-shape walk did not come back clean: %s" % tally)
    if not (log["scene_403"] > 0 and log["invitations_401"] > 0):
        raise SystemExit("ABORT the access log excerpt carries no 403/401 counts: %s" % log)
    if opened != 1:
        raise SystemExit("ABORT the click did not open the details element, so the label-behaviour claim "
                         "below would be wrong: details[open]=%d" % opened)
    return tally, log, opened, unlabelled


def check_paths(text):
    for path, line in re.findall(r"((?:trial|frontend|backend)/[A-Za-z0-9_./-]+\.(?:txt|md|py|js|json)):(\d+)",
                                 text):
        if not os.path.exists(os.path.join(ROOT, path.replace("/", os.sep))):
            raise SystemExit("ABORT the text cites %s, which is not on disk" % path)
        if int(line) > len(read(path).split("\n")):
            raise SystemExit("ABORT %s holds %d lines, so %s:%s names nothing"
                             % (path, len(read(path).split("\n")), path, line))


def append_section(at, numbers):
    if "14.42 补" in read(REPORT_REL):
        return 4
    tally, log, opened, unlabelled = numbers
    slots = {
        "launcher": LAUNCHER, "walk": WALK, "domread": DOMREAD, "clickread": CLICKREAD,
        "bw343": BW343, "bw344": BW344, "bw345": BW345, "bw346": BW346, "bw339": BW339,
        "at_launcher_floor": at["launcher_floor"], "at_launcher_junction": at["launcher_junction"],
        "at_walk_viewports": at["walk_viewports"], "at_dom_summary": at["dom_summary"],
        "at_dom_backlink": at["dom_backlink"], "at_click_line": at["click_line"],
        "at_click_details": at["click_details"], "at_ball_aria": at["ball_aria"],
        "at_unlabelled": at["unlabelled"], "at_log_tally": at["log_tally"], "at_log_scene": at["log_scene"],
        "at_receipt_tally": at["receipt_tally"], "at_receipt_phone": at["receipt_phone"],
        "at_prev": at["prev_section"], "viewports": tally["viewports"], "scene": log["scene_403"],
        "invites": log["invitations_401"], "routes": log["distinct_routes"], "opened": opened,
        "unlabelled": unlabelled,
    }
    section = "\n".join([
        "",
        "### 14.42 补（10-30 凌晨）：课堂代次换卷起得来，冷首屏对无票旅客只说「没读到」",
        "",
        "- 换卷起栈：E 卷现读只剩 0.13 GiB，原先那把启动器把树与库都钉在 E 上，所以另起一把同形制的"
        "（%(launcher)s:%(at_launcher_floor)d 是盘量地板、:%(at_launcher_junction)d 是 node_modules 接链），"
        "在 D 卷新开的零 dirty worktree（课堂代次 88b891d22c、一份全新空库、高德键只进进程环境不落盘不打印）"
        "起后端 :60362 与前端 :14462。真浏览器三档视口各开一次（%(walk)s:%(at_walk_viewports)d），"
        "回执 %(bw343)s:%(at_receipt_tally)d 读 viewports=%(viewports)d failed=0，逐档渲染文字与截图字节都记在"
        "同文件 %(at_receipt_phone)d 起；截图随本批入库（trial/results/20261026_gozero/screens/）。",
        "- 冷首屏说的是什么：三档读到的正文一模一样（196 字），标题「新建行程」、三步进度、八个输入、"
        "按钮「下一步 / 使用封存的演示行程 / 刷新 / EN」。没有种子数据、没有假成功态——这就是无票旅客第一眼看到的屏。",
        "- 屏面一格（同名两入口）：同一屏上有两处「高级设置」——一处是 details 的 summary（%(bw344)s:%(at_dom_summary)d，"
        "盒 [21,651,348,44]），一处是 class 为 trial-back-link 的 button（%(bw344)s:%(at_dom_backlink)d，"
        "盒 [21,719,348,44]，带下划线）。真点第二处（%(clickread)s）：地址不变、屏字从 196 字变 210 字、"
        "details[open] 由 0 变 %(opened)d，露出「国家/地区代码 时区 货币」——所以它不是坏控件，是同一件事给了两个入口，"
        "且第二个借的是「返回」那条链接的样式类。读数在 %(bw345)s:%(at_click_line)d 与 :%(at_click_details)d。",
        "- 屏面二格（403 被说成「没读到」）：这屏上唯一一处披露失败的，是右下角那颗球的 aria-label："
        "「模拟舞台（暂无场景）：场景状态没读到：REQUEST_ERROR」（%(bw345)s:%(at_ball_aria)d；全屏可访问名缺失的控件 "
        "%(unlabelled)d 枚，见 :%(at_unlabelled)d）。而后端自己的访问日志对同一次请求记的是 403 Forbidden"
        "（%(bw346)s:%(at_log_scene)d，共 %(scene)d 拍），邀请轮询是 401（共 %(invites)d 拍），合计 "
        "%(bw346)s:%(at_log_tally)d 读 distinct_routes=%(routes)d。也就是说：能行动的原因（没带演示票、未登录）"
        "在传输层是明确的，到屏上被折成一句笼统的「没读到」——与 §14.39、§14.40 那条「内部诊断串端给旅客」同族，"
        "只是这一格的方向反过来：该说的具体原因没说出来。",
        "- 待裁（不代裁，与 #377 的甲/乙/丙同批点）：其一＝这颗球在 403/401 时该说什么（甲：照实说「没带演示票」"
        "并给入口；乙：说「未登录」并给入口；丙：保持「没读到」但补一句可行动作）；其二＝同名两入口要不要合成一处"
        "（并让那条 button 不再用 trial-back-link 的样式类）。本班 0 改产品字节、0 改契约，点击只发生在本地隔离栈上。",
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(at_prev)d；对照件仍在 "
        "%(bw339)s。平板与手机的真人那一格（USER_VERIFIED）按规矩仍归主人亲按。",
        "",
    ]) % slots
    if "%(" in section:
        raise SystemExit("ABORT an unfilled slot survived into the section")
    check_paths(section)
    lines = [cell for cell in section.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    with io.open(REPORT, "rb") as handle:
        blob = handle.read()
    crlf = blob.count(b"\r\n")
    bare = blob.count(b"\n") - crlf
    if not blob.endswith(b"\r\n"):
        blob += b"\r\n"
    payload = b"\r\n".join(cell.encode("utf-8") for cell in lines) + b"\r\n"
    io.open(REPORT, "wb").write(blob + payload)
    back = io.open(REPORT, "rb").read()
    hits = back.count("14.42 补".encode("utf-8"))
    crlf_after = back.count(b"\r\n")
    bare_after = back.count(b"\n") - crlf_after
    print("APPENDED section_lines=%d heading_hits=%d crlf_now=%d bare_lf_now=%d"
          % (len(lines), hits, crlf_after, bare_after))
    if hits != 1:
        raise SystemExit("ABORT the heading is not unique")
    if crlf_after != crlf + len(lines) or bare_after != bare:
        raise SystemExit("ABORT the line endings moved: added %d CRLF and %d bare LF"
                         % (crlf_after - crlf, bare_after - bare))
    return 0


def write_block(at, numbers):
    tally, log, opened, unlabelled = numbers
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    closing = io.open(os.path.join(REF, "live_checks", "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    if not closing or "\n" in closing:
        raise SystemExit("ABORT the closing line is unusable")
    section_line = line_of(REPORT_REL, "14.42 补（10-30 凌晨）")
    now = datetime.now(timezone.utc).astimezone()
    base = now.hour * 60 + now.minute
    out = None
    for offset in range(0, 240):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out = candidate
            break
    if out is None:
        raise SystemExit("ABORT no free inbox name in the next four hours")

    slots = {
        "launcher": LAUNCHER, "walk": WALK, "clickread": CLICKREAD, "bw343": BW343, "bw344": BW344,
        "bw345": BW345, "bw346": BW346, "bw301": BW301, "bw339": BW339, "report": REPORT_REL,
        "at_launcher_floor": at["launcher_floor"], "at_dom_summary": at["dom_summary"],
        "at_walk_viewports": at["walk_viewports"],
        "at_dom_backlink": at["dom_backlink"], "at_click_line": at["click_line"],
        "at_click_details": at["click_details"], "at_ball_aria": at["ball_aria"],
        "at_unlabelled": at["unlabelled"], "at_log_tally": at["log_tally"],
        "at_log_scene": at["log_scene"], "at_receipt_tally": at["receipt_tally"],
        "at_receipt_phone": at["receipt_phone"], "section": section_line,
        "viewports": tally["viewports"], "opened": opened, "unlabelled": unlabelled,
        "scene": log["scene_403"], "invites": log["invitations_401"], "routes": log["distinct_routes"],
        "sha": sha, "closing": closing,
    }
    body = "\n".join([
        "### 494abfd7 交课堂代次换卷起栈的三档冷首屏屏证，与「403 被说成没读到」这一格（本块接上两格）",
        "",
        "- 起法（可复放）：E 卷现读 0.13 GiB，旧启动器把树与库钉在 E 上，故另起一把同形制的——盘量地板与 "
        "node_modules 接链见 %(launcher)s:%(at_launcher_floor)d；在 D 卷新开的零 dirty worktree（课堂代次 "
        "88b891d22c、全新空库、高德键只进进程环境不落盘不打印）起后端 :60362 与前端 :14462，三档视口各开一次真浏览器"
        "（清单 %(walk)s:%(at_walk_viewports)d 起）。回执 %(bw343)s:%(at_receipt_tally)d 读 viewports=%(viewports)d "
        "failed=0，逐档正文与截图字节从 %(bw343)s:%(at_receipt_phone)d 起；四张截图随本批入库在 "
        "trial/results/20261026_gozero/screens/。",
        "- 冷首屏给无票旅客的话：三档正文一致（196 字），标题「新建行程」，八处输入，按钮「下一步 / 使用封存的演示行程 / "
        "刷新 / EN」。没有种子数据、没有假成功态。",
        "- 格一（同名两入口，行为正常）：同一屏两处「高级设置」——details 的 summary（%(bw344)s:%(at_dom_summary)d，"
        "盒 [21,651,348,44]）与 class 为 trial-back-link 的 button（%(bw344)s:%(at_dom_backlink)d，盒 "
        "[21,719,348,44]、带下划线）。真点第二处（%(clickread)s）：地址不变、屏字 196→210、details[open] 0→%(opened)d，"
        "露出「国家/地区代码 时区 货币」（读数 %(bw345)s:%(at_click_line)d 与 :%(at_click_details)d）。所以这不是坏控件，"
        "是同一件事给了两个入口，且第二个借了「返回」那条链接的样式类。",
        "- 格二（该说的具体原因没说）：这屏上唯一披露失败之处是右下角那颗球的 aria-label"
        "「模拟舞台（暂无场景）：场景状态没读到：REQUEST_ERROR」（%(bw345)s:%(at_ball_aria)d；全屏无可访问名缺失的控件 "
        "%(unlabelled)d 枚，见 :%(at_unlabelled)d）。后端访问日志对同一次请求记的是 403 Forbidden（%(bw346)s:"
        "%(at_log_scene)d，共 %(scene)d 拍）、邀请轮询是 401（共 %(invites)d 拍），合计 %(bw346)s:%(at_log_tally)d "
        "读 distinct_routes=%(routes)d。传输层明确的原因（没带演示票、未登录）到屏上被折成「没读到」——与 §14.39、"
        "§14.40 那两格同族而方向相反：那两格是把内部串端给旅客，这一格是把可行动的原因糊成一句。",
        "- 待裁（不代裁）：其一＝这颗球在 403/401 时该说什么（甲：照实说「没带演示票」并给入口；乙：说「未登录」并给入口；"
        "丙：保留「没读到」但补一句可行动作）。其二＝同名两入口要不要合成一处、并让那条 button 不再用 trial-back-link "
        "的样式类。其三＝与 #377 的甲/乙/丙（坐标门要不要加存在性臂）同批点，本班 0 改门。",
        "- 落点与代次：正文在 %(report)s:%(section)d；本班落地复算读 %(bw301)s:1（第 1 行自报 TALLY 行号与三个计数）；"
        "仪表对照件在 %(bw339)s。本块所在提交为 git 对象 %(sha)s，可 git cat-file -t 取回。"
        "本班 0 改产品字节、0 改契约，点击只发生在本地隔离栈；平板与手机的真人那一格（USER_VERIFIED）按规矩仍归主人亲按。",
        "",
        "%(closing)s",
        "",
    ]) % slots

    def check(text):
        if not text.startswith("### "):
            raise SystemExit("ABORT the block does not open with a heading")
        if closing not in text:
            raise SystemExit("ABORT the closing line did not land")
        if "\r\n" in text:
            raise SystemExit("ABORT the inbox block must stay LF-only")
        if "%(" in text or "%d" in text or "%s" in text:
            raise SystemExit("ABORT an unformatted slot survived into the block")
        if sha not in text:
            raise SystemExit("ABORT the generation object did not land in the block")
        for pointer in ("%s:%d" % (BW343, at["receipt_tally"]), "%s:%d" % (BW344, at["dom_summary"]),
                        "%s:%d" % (BW345, at["click_line"]), "%s:%d" % (BW346, at["log_tally"]),
                        "%s:%d" % (LAUNCHER, at["launcher_floor"]),
                        "%s:%d" % (REPORT_REL, section_line), "%s:1" % BW301):
            if pointer not in text:
                raise SystemExit("ABORT the live pointer %r is not in the block" % pointer)
        check_paths(text)

    check(body)
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    if ledger.count("403 被说成没读到"):
        raise SystemExit("ABORT a block with this heading is already in the ledger")
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if back != body:
        raise SystemExit("ABORT the block on disk is not the text that passed the checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)
    numbers = measured()
    print("MEASURED viewports=%s log=%s opened=%s unlabelled=%s" % numbers)
    append_section(at, numbers)
    write_block(at, numbers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
