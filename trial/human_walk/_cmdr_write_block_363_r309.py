"""Write the #363 ledger block: the traveller-facing short list, ranked worst-first.

Every row of the list is parsed out of the bw307 receipt while this generator runs, and every anchor is
re-read; a missing artifact or a non-unique anchor aborts instead of shipping an unretrievable coordinate.
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
BW307 = GOZERO + "/bw307-what-a-traveller-would-read.txt"
BW302 = GOZERO + "/bw302-which-surface-says-it-in-english.txt"
ROWS_TO_LIST = 14

CITES = {
    "same_source": (BW307, "SAME-SOURCE CHECK"),
    "rank_rule": (BW307, "RANKED worst-first"),
    "traveller_path": (BW307, "on a traveller path"),
    "jargon": (BW307, "carrying internal vocabulary"),
    "identifier": (BW307, "carrying a bare identifier slot"),
    "score": ("trial/human_walk/_cmdr_what_traveller_reads_r307.py", "def score"),
    "start_route": ("backend/app/main.py", 'journeys/{journey_id}/start", response_model=JourneyTwinSchema'),
    "select_route": ("backend/app/main.py", "plans/{plan_version_id}/select\")"),
    "key_synthesiser": ("backend/app/main.py", '"message_key": message_key or'),
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.30 补（10-29 午后）"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.29 补（10-29 午后）"),
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


def number_at(rel, line, pattern):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    row = io.open(path, encoding="utf-8", errors="replace").read().split("\n")[line - 1]
    found = re.findall(pattern, row)
    if not found:
        raise SystemExit("ABORT line %d of %s has no number matching %s" % (line, rel, pattern))
    return int(found[-1])


def ranked_rows(limit):
    """Parse the receipt table so the block cannot quote a row that the ruler did not publish."""
    lines = io.open(os.path.join(ROOT, BW307.replace("/", os.sep)),
                    encoding="utf-8", errors="replace").read().split("\n")
    rows = []
    for index, row in enumerate(lines):
        head = re.match(r"^\s*(\d+)\.\s+(\S+):(\d+)\s+\((\w+)\)\s*$", row)
        if not head:
            continue
        route = lines[index + 1].split("route:", 1)
        screen = lines[index + 2].split("screen would show:", 1)
        terms = lines[index + 3].split("internal terms:", 1)
        if len(route) < 2 or len(screen) < 2 or len(terms) < 2:
            raise SystemExit("ABORT receipt row %s has an unexpected shape" % head.group(1))
        numbers = re.findall(r"\d+", terms[1])
        if len(numbers) != 2:
            raise SystemExit("ABORT receipt row %s does not carry two counts" % head.group(1))
        rows.append({"rank": int(head.group(1)), "file": head.group(2), "line": int(head.group(3)),
                     "via": head.group(4), "route": route[1].strip(),
                     "screen": screen[1].strip(),
                     "jargon_count": int(numbers[0]), "id_count": int(numbers[1])})
    if not rows:
        raise SystemExit("ABORT the receipt published no ranked rows")
    if rows[0]["rank"] != 1:
        raise SystemExit("ABORT the ranked table does not start at one")
    return rows[:limit], len(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)
    counts = {
        "reachable": number_at(BW307, at["same_source"], r"= (\d+)"),
        "traveller_path": number_at(BW307, at["traveller_path"], r": (\d+)"),
        "jargon": number_at(BW307, at["jargon"], r": (\d+)"),
        "identifier": number_at(BW307, at["identifier"], r": (\d+)"),
    }
    rows, published = ranked_rows(ROWS_TO_LIST)
    print("LIVE COUNTS %s rows_parsed=%d published_rows=%d" % (counts, len(rows), published))
    if published != ROWS_TO_LIST:
        raise SystemExit("ABORT the receipt publishes %d rows but this block lists %d"
                         % (published, ROWS_TO_LIST))

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

    listed = []
    for row in rows:
        listed.append(
            "　%d｜%s:%d（%s）在 `%s` 上端给屏上的是「%s」——内部词汇 %d 处、id 槽 %d 处"
            % (row["rank"], row["file"], row["line"], row["via"], row["route"],
               row["screen"], row["jargon_count"], row["id_count"]))

    now = datetime.now(timezone.utc).astimezone()
    base = now.hour * 60 + now.minute
    out = None
    for offset in range(0, 180):
        stamp = base + offset
        candidate = os.path.join(INBOX, "494abfd7_%02d%02d.md" % (stamp // 60 % 24, stamp % 60))
        if not os.path.exists(candidate):
            out = candidate
            break
    if out is None:
        raise SystemExit("ABORT no free inbox name in the next three hours")

    body = "\n".join([
        "### 494abfd7 交「%d 处里旅客最先撞到的头几条」可点单清单（#363，接 §14.29 那条待裁）" % counts["reachable"],
        "",
        "- 这把尺不复打口径：trial/human_walk/_cmdr_what_traveller_reads_r307.py:%d 直接复用 §14.29 "
        "那把尺的同一份 collect()，与已发布的 %d 处对不上就 ABORT 不出表（现读 %d 处，回执 %s:%d）。"
        % (at["score"], counts["reachable"], counts["reachable"], BW307, at["same_source"]),
        "- 排序口径（回执 %s:%d）：先旅客路径（/journeys、/plans、/trips、/travellers），"
        "再内部词汇，再裸 id 槽，最后比长度。%d 处里落在这四条路径上的 %d 处（:%d），"
        "带内部词汇的 %d 处（:%d），带裸 id 槽的 %d 处（:%d）。"
        % (BW307, at["rank_rule"], counts["reachable"], counts["traveller_path"],
           at["traveller_path"], counts["jargon"], at["jargon"], counts["identifier"], at["identifier"]),
        "- %d 条全列（下面每行都从回执解析，不是我手抄；回执表共 %d 行）：" % (len(rows), published),
    ] + listed + [
        "- 清单里能一刀罩几条先说清：头两条是同一句模板的两半（出发口的路由装饰器写在 "
        "backend/app/main.py:%d，选用口写在 backend/app/main.py:%d；两条 raise 自己在清单里那两行），"
        "改一处文案等于改两处；其余各条各自一条路由，一刀罩不住，要点单就得逐条点。"
        % (at["start_route"], at["select_route"]),
        "- 待裁（不代裁）：甲，这 %d 处带内部词汇、%d 处带裸 id 的是否统一改成"
        "「点名地点＋人话＋不端 id」那一形制；乙，是否给它们配各自具名键——"
        "现状是统一出口按状态码拼键（backend/app/main.py:%d），同码不同句共用一枚，"
        "不配就仍接不上中文。本班 0 改产品字节。" % (counts["jargon"], counts["identifier"],
                                                    at["key_synthesiser"]),
        "- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。" % (at["section"], at["prev_section"], sha),
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
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
