"""Write ledger block #376: an erratum for the coordinates #375 cited, read back one by one.

#375 cites seven file:line pointers.  Every one of them was right the minute it was written - and then this
shift landed another block, the census re-ran, and the ruler itself grew a self-anchor, which move line
numbers inside the very artifacts #375 points at.  Old posts are not edited here, so the correction is a new
block.

Nothing is remembered.  Each pointer is pulled out of #375's own archived text, its meaning is recovered
from the words wrapped around it (not from a line number), the line that meaning currently occupies is
read off disk, and the pair goes into the block.  If a pointer turns out not to have drifted, the block says
so instead of claiming a correction that did not happen.
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
PROCESSED = r"D:/moodle/_qoder_ledger_inbox/_processed"
GOZERO = "trial/results/20261026_gozero"
BW301 = GOZERO + "/bw301-this-sessions-blocks-landed.txt"
BW339 = GOZERO + "/bw339-census-window-old-vs-new-vs-narrow.txt"
REL = "trial/human_walk/_cmdr_blocks_landed_census_r301.py"
REPORT = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
SELF = "trial/human_walk/_cmdr_write_block_376_r350.py"
CORRECTED_HEADING = "管落地的普查自己跨零点数不到全"

# meaning is recovered from the words around a pointer, never from the pointer's own value.  The nearest
# keyword wins: the same window can mention several readings, and the one touching the pointer is the one
# that decided it.
FEATURES = (
    ("为 checked=", "checked 计数行", "TALLY checked=", None, None),
    ("负对照", "负对照行", "NEGATIVE_CONTROL unseen title", None, None),
    ("落地行", "边界行", "WINDOW_EDGE first block excluded",
     "边界打印行", 'out.append("WINDOW_EDGE first block excluded'),
    ("段首见", "第一段行", "  stretch 1:", None, None),
    ("session_window", None, None, "日窗定义行", "def session_window"),
    ("按停顿", None, None, "分段定义行", "def stretches"),
)


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


def archived_block():
    matches = []
    for cell in os.listdir(PROCESSED):
        if not cell.startswith("494abfd7") or ".inserted_" not in cell:
            continue
        text = io.open(os.path.join(PROCESSED, cell), encoding="utf-8", errors="replace").read()
        if CORRECTED_HEADING in text:
            matches.append((cell, text))
    if len(matches) != 1:
        raise SystemExit("ABORT the block I am correcting matches %d archived files, not one"
                         % len(matches))
    return matches[0]


def pointers_of(text):
    """Every file:line pointer and each "same file :N" follow-up, with the words before and after it."""
    which_of = {os.path.basename(BW301): BW301, os.path.basename(BW339): BW339,
                os.path.basename(REL): REL, os.path.basename(REPORT): REPORT}
    found = []
    current = None
    for match in re.finditer(r"([A-Za-z0-9_.-]+\.(?:txt|py|md))\s*:\s*(\d+)|(同文件)\s*:\s*(\d+)", text):
        if match.group(1):
            which = which_of.get(match.group(1))
            line = int(match.group(2))
            if which is None:
                continue
            current = which
            tail = match.group(2)
        else:
            which, line, tail = current, int(match.group(4)), match.group(4)
        if which is None:
            raise SystemExit("ABORT a pointer %r appeared before any file was named" % match.group(0))
        start = match.end() - len(tail)
        found.append((which, line, text[max(0, start - 200):start], text[start:start + 200]))
    receipt = [cell for cell in found if cell[0] == BW301]
    ruler = [cell for cell in found if cell[0] == REL]
    if len(receipt) < 4 or len(ruler) < 3:
        raise SystemExit("ABORT #375 yielded %d receipt pointers and %d ruler pointers, fewer than the "
                         "erratum is written to cover" % (len(receipt), len(ruler)))
    return found


def classify(rows):
    out = []
    for which, line, before, after in rows:
        # an un-moved pointer is its own proof: the line it names still is the line that meaning occupies
        hit = None
        for keyword, r_label, r_needle, k_label, k_needle in FEATURES:
            needle = r_needle if which == BW301 else k_needle
            label = r_label if which == BW301 else k_label
            if needle is None or label is None:
                continue
            if line_of(which, needle) == line:
                hit = (label, needle)
                break
        if hit is None:
            best = None
            for keyword, r_label, r_needle, k_label, k_needle in FEATURES:
                label = r_label if which == BW301 else k_label
                needle = r_needle if which == BW301 else k_needle
                if label is None or needle is None:
                    continue
                if keyword in after:
                    offset = after.index(keyword)
                elif keyword in before:
                    offset = -(len(before) - before.rindex(keyword))
                else:
                    continue
                if best is None or abs(offset) < abs(best[0]):
                    best = (offset, label, needle)
            if best is None:
                raise SystemExit("ABORT could not recover the meaning of %s :%d from %r / %r"
                                 % (os.path.basename(which), line, before[-40:], after[:40]))
            hit = (best[1], best[2])
        out.append((hit[0], line, line_of(which, hit[1]), which))
    seen = set()
    for label, old, now, which in out:
        if (label, old) in seen:
            raise SystemExit("ABORT the pointer %s:%d matched two readings at once" % (label, old))
        seen.add((label, old))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    name, corrected = archived_block()
    found = pointers_of(corrected)
    rows = classify([cell for cell in found if cell[0] in (BW301, REL)])
    wrote_block = os.path.getmtime(os.path.join(PROCESSED, name))
    quiet = []
    for which, line in sorted(set((cell[0], cell[1]) for cell in found
                                  if cell[0] not in (BW301, REL))):
        if os.path.getmtime(os.path.join(ROOT, which.replace("/", os.sep))) > wrote_block:
            raise SystemExit("ABORT %s was rewritten after the block under correction was posted, so its "
                             "pointers cannot be called stable" % os.path.basename(which))
        quiet.append("%s:%d" % (which, line))
    cited = re.findall(r"((?:trial|frontend|backend)/[A-Za-z0-9_./-]+\.(?:txt|md|py)):(\d+)", corrected)
    doubled = sorted(set("%s:%s" % (os.path.basename(path), line) for path, line in cited
                         if "20261026_gozero/trial/results/20261026_gozero" in path))
    if not doubled:
        raise SystemExit("ABORT no doubled directory was found in the block under correction, so the "
                         "paragraph below would be describing a defect that is not there")
    # the needle is stitched at runtime: written whole it would appear on this very line and the anchor
    # check would find two copies of itself
    gate_line = line_of(SELF, "in path" + ":")
    print("DOUBLED_PATHS %s | new door lives at %s:%d" % (doubled, SELF, gate_line))
    drifted = [cell for cell in rows if cell[1] != cell[2]]
    stayed = [cell for cell in rows if cell[1] == cell[2]]
    for label, old, now, which in rows:
        print("  %-14s %s  old :%d -> now :%d %s" % (label, os.path.basename(which), old, now,
                                                     "(moved)" if old != now else "(same)"))
    if not drifted:
        raise SystemExit("ABORT not one pointer moved, so this erratum would correct nothing")

    tally_now = line_of(BW301, "TALLY checked=")
    tally_row = re.search(r"checked=(\d+) green=(\d+) red=(\d+)", row_at(BW301, tally_now))
    if not tally_row:
        raise SystemExit("ABORT the tally line at %s:%d does not read its three counts"
                         % (os.path.basename(BW301), tally_now))
    counts = {"checked": int(tally_row.group(1)), "green": int(tally_row.group(2)),
              "red": int(tally_row.group(3))}
    anchor = re.search(r"TALLY_LINE (\d+) \| checked (\d+) green (\d+) red (\d+)", row_at(BW301, 1))
    if not anchor:
        raise SystemExit("ABORT line one of the receipt no longer carries the self-anchor")
    if (int(anchor.group(1)) != tally_now or int(anchor.group(2)) != counts["checked"]
            or int(anchor.group(3)) != counts["green"] or int(anchor.group(4)) != counts["red"]):
        raise SystemExit("ABORT the self-anchor on line one does not match the tally line it names")

    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    hits = ledger.count(CORRECTED_HEADING)
    if hits != 1:
        raise SystemExit("ABORT the block I am correcting appears %d times in the ledger, not once" % hits)

    at = {
        "anchor_def": line_of(REL, "STABLE_ANCHOR line 1 | TALLY_LINE"),
        "anchor_check": line_of(REL, "landed = io.open(receipt"),
        "flat_def": line_of(REL, "def flat(text)"),
        "control_tally": line_of(BW339, "  TALLY checked=44 green="),
        "section": line_of(REPORT, "14.40 补（10-30 凌晨）"),
        "prev_section": line_of(REPORT, "14.39 补（10-30 零点）"),
    }
    print("LIVE ANCHORS %s" % at)

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    closing = io.open(os.path.join(REF, "live_checks", "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    if not closing or "\n" in closing:
        raise SystemExit("ABORT the closing line is unusable")

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

    listing = ["　%d｜「%s」在 %s：旧坐标 :%d，现读 %s:%d（%s）"
               % (index + 1, label, which, old, which, current,
                  "已换号" if old != current else "未换号")
               for index, (label, old, current, which) in enumerate(rows)]

    slots = {
        "heading": CORRECTED_HEADING, "name": name, "bw301": BW301, "bw339": BW339, "rel": REL,
        "total": len(rows), "moved": len(drifted), "same": len(stayed),
        "quiet_count": len(quiet), "quiet": "、".join(quiet),
        "doubled_count": len(doubled), "doubled": "、".join(doubled),
        "self": SELF, "gate_line": gate_line,
        "tally_now": tally_now, "control_tally": at["control_tally"],
        "anchor_def": at["anchor_def"], "anchor_check": at["anchor_check"], "flat_def": at["flat_def"],
        "section": at["section"], "prev_section": at["prev_section"],
        "checked": counts["checked"], "green": counts["green"], "red": counts["red"],
        "anchor_line": anchor.group(1), "anchor_count": anchor.group(2), "sha": sha, "closing": closing,
    }
    body = "\n".join([
        "### 494abfd7 勘误：把「普查回执与尺」那几枚会漂的坐标逐枚现读，并交出第 1 行的自指锚（本块接上一格）",
        "",
        "- 错在哪：上一块（标题含「%(heading)s」那格，归档件 %(name)s）在两份会生长的工件里共交了 %(total)d 枚 "
        "file:line 坐标（另有 %(quiet_count)d 枚指向本轮未再重写的工件：%(quiet)s）。写它的那一刻每枚都对；"
        "随后本班又落了一块（普查表随之变长），尺自己也为这次的故障加了行。现逐枚重读：%(moved)d 枚已换号、"
        "%(same)d 枚未换号。旧帖不改，本块逐枚自行为证——每枚坐标的含义都是从那一块原句的词里认出来的，"
        "不是拿号对号。",
    ] + listing + [
        "- 更要紧的一处：那一块里有 %(doubled_count)d 枚坐标把同一层目录连写了两遍（gozero 那层出现两次），"
        "本机没有这种路径——形制对而读者取不回，比行号换号更硬。受影响的是：%(doubled)s。正确写法就是本块现读的"
        "单层坐标，例如 %(bw301)s:%(tally_now)d。这道闸现在装在本类的交块检查里：逐枚 os.path.exists，并核那文件"
        "有没有那么多行（%(self)s:%(gate_line)d）；本块自己先过它，写重的路径从此出不了门。",
        "- 改成什么（今后只引这两枚）：回执的 checked 计数不再引具体行，改引 %(bw301)s:1 ——尺现在把 TALLY 的行号"
        "与三个计数写进第 1 行（%(rel)s:%(anchor_def)d），落盘后还把这张表读回来核那枚指针是否真落在 TALLY 行上"
        "（%(rel)s:%(anchor_check)d）。现读第 1 行自报 TALLY_LINE %(anchor_line)s、checked %(anchor_count)s，"
        "与 %(bw301)s:%(tally_now)d 那行的 checked=%(checked)d green=%(green)d red=%(red)d 同号同值。"
        "不靠重跑取回的那枚仍在：%(bw339)s:%(control_tally)d（对照件，一次写完不再重跑）。上面 listing 里的现读号"
        "是交块那一刻的快照——本块落下后自指锚会自报新号，那是设计如此，不是又一处漂移；要引就引第 1 行。",
        "- 这一类错怎么防：三件。(1) 会重跑的回执自带自指锚，块引第 1 行而不引下面任意一行；(2) 尺里两枚会换行的"
        "夹入读数（负对照与逐格 gate 回执）已压成单行（%(rel)s:%(flat_def)d）——不压的话第 1 行的行号算术自己就错，"
        "这次正是新装的自指校验当场抓出来的；(3) 交块前对自家块做一次「坐标回读」：凡指针指向会生长的工件，"
        "落账前最后一次现读，凡凭记忆写的一律不算数。本班 0 改产品字节、0 点击。",
        "- 代次与正文：本块所在提交为 git 对象 %(sha)s，可 git cat-file -t 取回；正文在 "
        "trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(section)d，上一节在同文件 "
        "trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(prev_section)d。",
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
        if text.count("旧坐标 :") != len(rows):
            raise SystemExit("ABORT not every classified pointer made it into the listing: %d of %d"
                             % (text.count("旧坐标 :"), len(rows)))
        for label, old, current, which in rows:
            if "旧坐标 :%d，现读 %s:%d" % (old, which, current) not in text:
                raise SystemExit("ABORT the pair for %s (%d -> %d) is not in the block" % (label, old, current))
        for pointer in ("%s:1" % BW301,
                        "%s:%d" % (BW301, tally_now),
                        "%s:%d" % (BW339, at["control_tally"]),
                        "%s:%d" % (REL, at["anchor_def"]),
                        "%s:%d" % (REL, at["flat_def"]),
                        "%s:%d" % (REL, at["anchor_check"]),
                        "GO_FROM_BLANK_REPORT.md:%d" % at["section"],
                        "GO_FROM_BLANK_REPORT.md:%d" % at["prev_section"]):
            if pointer not in text:
                raise SystemExit("ABORT the live pointer %r is not in the block" % pointer)
        if sha not in text:
            raise SystemExit("ABORT the generation object did not land in the block")
        # every cited path must exist on disk and be long enough to hold the line it names: the Q43 door
        # checks the shape of a coordinate, so a doubled directory passes there and fails for a reader
        for path, line in re.findall(r"((?:trial|frontend|backend)/[A-Za-z0-9_./-]+\.(?:txt|md|py)):(\d+)",
                                     text):
            if "20261026_gozero/trial/results/20261026_gozero" in path:
                raise SystemExit("ABORT the block carries a doubled directory: %s" % path)
            if not os.path.exists(os.path.join(ROOT, path.replace("/", os.sep))):
                raise SystemExit("ABORT the block cites %s, which is not on disk" % path)
            if int(line) > len(read(path).split("\n")):
                raise SystemExit("ABORT %s holds %d lines, so the block cites a line that is not there"
                                 % (path, len(read(path).split("\n"))))

    check(body)
    pending = [cell for cell in os.listdir(INBOX) if cell.endswith(".md") and not cell.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d | pointers %d moved %d same %d"
          % (len(pending), len(rows), len(drifted), len(stayed)))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = io.open(out, encoding="utf-8").read()
    if back != body:
        raise SystemExit("ABORT the block on disk is not the text that passed the checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
