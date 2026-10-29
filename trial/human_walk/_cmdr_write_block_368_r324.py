"""Write the #368 ledger block: of the caller rows bw318 found, which sit on a panel the registry mounts.

Rows are parsed from the bw322 receipt while this runs and reconciled three ways (parsed rows against the
receipt's own TALLY, the TALLY against bw318's published caller_found, and the concentration pairs against
the mounted count), so this block cannot describe a different set than the two rulers above it.
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
    "bw318_tally": (BW318, "TALLY caller_found="),
    "ruler": ("trial/human_walk/_cmdr_panel_ask_r322.py", "def registry_panels"),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.34 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.33 补（10-29 午后）"),
}

ROW = re.compile(r"^\s*(\d+)\.\s+(\S+)\s+函数 (\S+)（(frontend/\S+?):(\d+)）→ (\w+)，使用者 (\d+) 处"
                 r"（其中可成面板的 (\d+) 处）(.*)$")
EVIDENCE = re.compile(r"^\s{6}(frontend/\S+?):(\d+)(  ← .*)?$")

VERDICT_CN = {"ON_A_MOUNTED_PANEL": "挂在注册表渲染的面板上",
              "USED_BY_APP_SHELL": "由 app/ 壳自己发",
              "USED_OFF_PANEL": "由注册表从不渲染的组件发",
              "SHARED_API_ONLY": "只剩共用 API 层",
              "NO_USER_FOUND": "无人问"}


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


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def parsed_rows():
    lines = read(BW322).split("\n")
    rows = []
    for index, line in enumerate(lines):
        match = ROW.match(line)
        if not match:
            continue
        evidence = []
        for following in lines[index + 1:index + 4]:
            found = EVIDENCE.match(following)
            if found:
                evidence.append((found.group(1), int(found.group(2)), bool(found.group(3))))
            elif following.strip() and not following.startswith("      "):
                break
        if not evidence and re.search(r"使用者 (\d+) 处", line) and int(
                re.search(r"使用者 (\d+) 处", line).group(1)):
            # a row that claims users has to locate them; a row with zero users is already located by
            # its own building-file coordinate on the row line
            raise SystemExit("ABORT row %s claims users but names no user coordinate" % match.group(1))
        rows.append({"rank": int(match.group(1)), "url": match.group(2), "name": match.group(3),
                     "file": match.group(4), "line": int(match.group(5)),
                     "verdict": match.group(6), "users": int(match.group(7)),
                     "panel_users": int(match.group(8)), "note": match.group(9).strip(),
                     "evidence": evidence})
    if not rows:
        raise SystemExit("ABORT bw322 published no parseable rows")
    if rows[0]["rank"] != 1:
        raise SystemExit("ABORT the row list does not start at one")
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    slots = re.findall(r"=(\d+)", row_at(BW322, at["tally"]))
    if len(slots) != 6:
        raise SystemExit("ABORT the bw322 TALLY does not read as six numbers")
    mounted, shell, off, shared, none, rows_published = [int(value) for value in slots]
    caller_found = int(re.findall(r"=(\d+)", row_at(BW318, at["bw318_tally"]))[0])
    if rows_published != caller_found:
        raise SystemExit("ABORT bw322 covers %d rows against bw318's caller_found of %d"
                         % (rows_published, caller_found))
    if mounted + shell + off + shared + none != rows_published:
        raise SystemExit("ABORT the verdicts do not cover every row")
    rows = parsed_rows()
    if len(rows) != rows_published:
        raise SystemExit("ABORT parsed %d rows against the receipt's own %d"
                         % (len(rows), rows_published))
    counted = {key: sum(1 for item in rows if item["verdict"] == key) for key in VERDICT_CN}
    if (counted["ON_A_MOUNTED_PANEL"], counted["USED_BY_APP_SHELL"], counted["USED_OFF_PANEL"],
            counted["SHARED_API_ONLY"], counted["NO_USER_FOUND"]) != (mounted, shell, off, shared, none):
        raise SystemExit("ABORT the parsed verdicts disagree with the TALLY: %s" % counted)

    conc = row_at(BW322, at["concentration"])
    files_on_panel = int(re.search(r"rest on (\d+) distinct", conc).group(1))
    pairs = re.findall(r"([\w/.-]+)=(\d+)", conc)
    if sum(int(value) for _, value in pairs) != mounted or len(pairs) != files_on_panel:
        raise SystemExit("ABORT the concentration line does not reconcile with the mounted count")
    table = row_at(BW322, at["mount_table"])
    imported, rendered = [int(value) for value in
                          re.search(r"imports (\d+) module\(s\) and renders (\d+)", table).groups()]
    shared_name, named_rows = [int(value) for value in
                               re.search(r"^NAME_UNIQUENESS (\d+) of (\d+)",
                                         row_at(BW322, at["uniqueness"])).groups()]
    if named_rows != rows_published:
        raise SystemExit("ABORT NAME_UNIQUENESS counts %d rows against %d" % (named_rows, rows_published))
    print("LIVE NUMBERS rows=%d mounted=%d shell=%d off=%d imported=%d rendered=%d panels=%d"
          % (rows_published, mounted, shell, off, imported, rendered, files_on_panel))

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

    listing = []
    for item in rows:
        cells = "、".join("`%s:%d`%s" % (rel, line_no, "（注册表渲染）" if mounted_mark else "")
                          for rel, line_no, mounted_mark in item["evidence"])
        if not cells:
            cells = "无使用者，构建处即上行坐标"
        listing.append("　%d｜`%s` → %s；构建处 `%s:%d`；函数 `%s`；使用者 %d 处，可成面板的 %d 处；%s"
                       % (item["rank"], item["url"], VERDICT_CN[item["verdict"]], item["file"],
                          item["line"], item["name"], item["users"], item["panel_users"], cells))

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

    body = "\n".join([
        "### 494abfd7 交「会问的那二十处里哪几处真挂在面板上」的逐枚归属（#368，接 §14.34）",
        "",
        "- 为什么还要这一腿：#366 交出「前端会问」，但没说发这句请求的是不是一屏旅客打得开的面板。"
        "尺 trial/human_walk/_cmdr_panel_ask_r322.py:%d 把「挂上面板」定成注册表既 import 了该模块、"
        "又把它当 JSX 组件渲染，两条都要成立；只看使用者不够——该行构建文件自己就是被渲染的组件时也算。"
        % at["ruler"],
        "- 分母同代对账：本块解析 %d 行＝回执 %s:%d 的 rows＝bw318 发布 caller_found=%d（回执 %s:%d），"
        "五档判定相加亦等于 %d（回执 :%d）。四路相等才继续。"
        % (len(rows), BW322, at["tally"], caller_found, BW318, at["bw318_tally"], rows_published,
           at["tally"]),
        "- 读数（回执 %s:%d）：%d 处挂在注册表渲染的面板上，%d 处由 app/ 壳自己发，"
        "%d 处由注册表从不渲染的组件发，%d 处只剩共用 API 层，%d 处无人问。"
        % (BW322, at["tally"], mounted, shell, off, shared, none),
        "- 集中度才是这一格该看的：那 %d 处只压在 %d 枚文件上（回执 %s:%d）——%s。"
        "注册表 import %d 枚模块、渲染其中 %d 枚（回执 %s:%d），所以「哪几枚面板」比行数更有用。"
        % (mounted, files_on_panel, BW322, at["concentration"],
           "、".join("`%s`（%s 处）" % (rel, value) for rel, value in pairs), imported, rendered,
           BW322, at["mount_table"]),
        "- 自报一格我造成的错读数：同一把尺四个口径给出四组数（回执 %s:%d 逐档写明）。"
        "第一版把注册表里任何文字当挂载，多算了几处——app/V8Experience.tsx 只出现在一条文档注释里"
        "（frontend/src/app/v8PanelRegistry.tsx:83），却被算成面板；第二版只认 import 边，"
        "反过来漏掉「构建文件本身就是被渲染组件」那几处；第三版要求 import 加 JSX；"
        "第四版把「路径在 app/ 文件里就地拼出、别处永远提不到那个局部名字」从无人问改判成应用壳。"
        "第一版的回执已入提交代次 e329db4b2c，不是我私下改的口。" % (BW322, at["revision"]),
        "- 两条判别臂（回执 %s:%d、%s:%d）：注册表文字里出现却无 import 边的模块被点名剔除，"
        "import 了却不渲染的也算不上面板；整名搜索换一个谁都没定义的名字必须命中 0 枚文件。"
        "另有同名疑虑实测：%d 行共用一个函数名，其余各行各自点名不同可调用物。"
        % (BW322, at["match"], BW322, at["control"], shared_name),
        "- 下面 %d 行整串由回执解析、非手抄，每行自带构建处与使用者坐标：" % len(rows),
    ] + listing + [
        "- 这把尺不能说的那句（不替它补）：注册表渲染 ≠ 旅客会打开那一屏，整名命中 ≠ 真发生了调用"
        "（注释与再导出都算）。极限写在回执 %s:%d——它只把「哪几屏可能显出这句英文」收窄，"
        "代替不了真走一遍。本班 0 改产品字节。" % (BW322, at["coverage"]),
        "- 待裁（不代裁）：文案刀由此多一档按面板切的选法——先切承载这 %d 处的上述 %d 枚文件，"
        "还是照 §14.32 的三档切；两档都要先定 §14.31 那句大小写口径。" % (mounted, files_on_panel),
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。"
        % (at["section"], at["prev_section"], sha),
        "",
        closing,
        "",
    ])

    pending = [f for f in os.listdir(INBOX) if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if not back.startswith("### "):
        raise SystemExit("ABORT the block does not open with a heading")
    if closing not in back:
        raise SystemExit("ABORT the closing line did not land")
    if "\r\n" in back:
        raise SystemExit("ABORT the inbox block must stay LF-only")
    if back.count("｜`") != len(rows):
        raise SystemExit("ABORT not every parsed row made it into the block")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
