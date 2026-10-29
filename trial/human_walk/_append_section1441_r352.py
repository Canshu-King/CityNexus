"""Append section 14.41: four arms against the coordinate door, and what a green verdict from it means.

Every number, verdict and anchor is re-read while this runs - out of bw341, out of the two generators whose
gates are cited, and out of the door's own printed arms.  Nothing here is quoted from memory, and the
section says which artifact carries which arm so a reader can re-run the probe instead of trusting prose.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT_REL = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
BW341 = "trial/results/20261026_gozero/bw341-what-the-q43-door-accepts-as-a-coordinate.txt"
BW339 = "trial/results/20261026_gozero/bw339-census-window-old-vs-new-vs-narrow.txt"
PROBE = "trial/human_walk/_cmdr_q43_shape_probe_r351.py"
BLOCKGEN = "trial/human_walk/_cmdr_write_block_376_r350.py"

CITES = {
    "probe_arms": (PROBE, "ARMS = ("),
    "probe_ghost": (PROBE, "GHOST = "),
    "real_head": (BW341, "ARM real_path"),
    "double_head": (BW341, "ARM doubled_directory"),
    "ghost_head": (BW341, "ARM no_such_file"),
    "range_head": (BW341, "ARM line_out_of_range"),
    "read": (BW341, "READ: all"),
    "tally": (BW341, "TALLY arms="),
    "exists_gate": (BLOCKGEN, "which is not on disk"),
    "range_gate": (BLOCKGEN, "line that is not there"),
    "prev_section": (REPORT_REL, "14.40 补（10-30 凌晨）"),
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
    return read(rel).split("\n")[line - 1]


def arm_facts(heading_line):
    """Under each ARM heading the receipt prints whether the path was on disk, and the door's own verdict."""
    lines = read(BW341).split("\n")
    tail = lines[heading_line:]
    exists = next(cell.split()[-1] for cell in tail if "path on disk here" in cell)
    verdict = next(cell.strip() for cell in tail if "door verdict" in cell)
    return exists, verdict


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    arms = dict((name, arm_facts(at[key])) for name, key in
                (("real", "real_head"), ("double", "double_head"),
                 ("ghost", "ghost_head"), ("range", "range_head")))
    tally = dict((k, int(v)) for k, v in re.findall(r"(arms|green|red)=(\d+)",
                                                    row_at(BW341, at["tally"])))
    if tally["red"] or tally["green"] != tally["arms"] or tally["arms"] != 4:
        raise SystemExit("ABORT bw341 no longer reads as four arms all green: %s" % tally)
    if not (arms["real"][0] == "True" and arms["double"][0] == "False"
            and arms["ghost"][0] == "False" and arms["range"][0] == "True"):
        raise SystemExit("ABORT the existence readings do not match the four shapes: %s" % arms)
    if not all("Q43_GATE_GREEN" in verdict for _exists, verdict in arms.values()):
        raise SystemExit("ABORT one arm did not come back green: %s" % arms)
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    print("LIVE ARMS %s tally=%s" % (arms, tally))

    if "14.41 补" in read(REPORT_REL):
        return 4
    slots = {
        "bw341": BW341, "bw339": BW339, "probe": PROBE, "blockgen": BLOCKGEN,
        "arms": tally["arms"], "green": tally["green"],
        "real_head": at["real_head"], "double_head": at["double_head"],
        "ghost_head": at["ghost_head"], "range_head": at["range_head"],
        "read_line": at["read"], "tally_line": at["tally"], "probe_arms": at["probe_arms"],
        "probe_ghost": at["probe_ghost"], "exists_gate": at["exists_gate"],
        "range_gate": at["range_gate"], "prev_section": at["prev_section"], "sha": sha,
    }
    section = "\n".join([
        "",
        "### 14.41 补（10-30 凌晨）：坐标门只认形制的四档实测——以及这块地界该谁守",
        "",
        "- 测法：同一句 claim（「共 46 条记录，逐条坐标见 …:148，另有 12 条待点单」）配四枚不同坐标目标，"
        "各跑一次门；四档定义见 %(probe)s:%(probe_arms)d（其中不存在那枚的文件名写在 :%(probe_ghost)d）。"
        "逐档原判落盘 %(bw341)s：真路径 :%(real_head)d、目录写重 :%(double_head)d、"
        "文件不存在 :%(ghost_head)d、真文件越界行 :%(range_head)d；合计行 :%(tally_line)d 现读 arms=%(arms)d "
        "green=%(green)d red=0。",
        "- 读数：四档都回 Q43_GATE_GREEN。「文件不存在」那档 os.path.exists 实测 False，「越界行」那档文件在而 "
        ":99999 不在文件长度内（回执 :%(range_head)d 起两行自己写着 True / False）。所以这道门的坐标臂判的是形制："
        "数字挨着一个像文件名的东西就算落了锚，不去问那路径在不在盘上、也不问那文件有没有那么多行。"
        "整句结论见 %(bw341)s:%(read_line)d。",
        "- 这解释上一格：#375 有 6 枚坐标把 gozero 那层目录连写两遍，过门时仍是绿的——「目录写重」那档就是那个形状"
        "（%(bw341)s:%(double_head)d 起）。不是门漏咬，是它本就不咬这个面。",
        "- 我这边守的：本班交块脚本落盘前逐枚现读——路径不在盘上就拒（%(blockgen)s:%(exists_gate)d），行号越过"
        "文件末尾就拒（%(blockgen)s:%(range_gate)d），现读号写进块里而不引记忆。装上它第一次自咬就咬到了模板里"
        "重复的目录前缀，改后的对照见 %(bw339)s 与 #376 的逐枚表。",
        "- 待点单（三档并列，不代裁）：甲＝给坐标门加一条「路径须在盘上、行号须在界内」的臂（那是号令者那把尺，"
        "本班 0 改它；四档样本与原判都在这张回执里，可直接复放）；乙＝不加，这条留给各家生成器自查（本班已按乙"
        "执行，代价是每个车道各自装）；丙＝只加「路径在盘上」不加「行号界内」（咬住写重与虚构，放过越界）。",
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%(prev_section)d。本班 0 改产品字节、"
        "0 点击、0 改门。代次 git 对象 %(sha)s。",
        "",
    ]) % slots
    lines = section.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    section = "\n".join(lines)
    if "%(" in section:
        raise SystemExit("ABORT an unfilled slot survived into the section")

    with io.open(REPORT, "rb") as handle:
        blob = handle.read()
    crlf = blob.count(b"\r\n")
    bare = blob.count(b"\n") - crlf
    if not blob.endswith(b"\r\n"):
        blob += b"\r\n"
    payload = b"\r\n".join(cell.encode("utf-8") for cell in section.split("\n")) + b"\r\n"
    io.open(REPORT, "wb").write(blob + payload)
    back = io.open(REPORT, "rb").read()
    hits = back.count("14.41 补".encode("utf-8"))
    crlf_after = back.count(b"\r\n")
    bare_after = back.count(b"\n") - crlf_after
    print("APPENDED bytes_added=%d section_lines=%d heading_hits=%d crlf_now=%d bare_lf_now=%d"
          % (len(payload), len(section.split("\n")), hits, crlf_after, bare_after))
    if hits != 1:
        raise SystemExit("ABORT the heading is not unique")
    if crlf_after != crlf + len(section.split("\n")) or bare_after != bare:
        raise SystemExit("ABORT the line endings moved: added %d CRLF and %d bare LF"
                         % (crlf_after - crlf, bare_after - bare))
    return 0


if __name__ == "__main__":
    sys.exit(main())
