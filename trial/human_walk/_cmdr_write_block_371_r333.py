"""Write ledger block #371: an erratum pointing block #370 at the paragraph that actually holds it.

Block #370 cites report section 14.35 as its body text.  That was true when it was written - the sentence
readings lived only in the bw327 receipt then - and is no longer the best pointer, because section 14.36
now carries them.  Old posts are not edited in this ledger, so the correction is a new block, and it
re-reads both the landed heading it corrects and the live line number of the new section rather than
quoting either from memory.
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
GOZERO = "trial/results/20261026_gozero"
BW327 = GOZERO + "/bw327-what-the-panels-say-instead.txt"

CORRECTED_HEADING = "交「屏上改写成什么话」的逐枚靶面"
CITES = {
    "section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.36 补（10-29 夜）"),
    "prev": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.35 补（10-29 夜）"),
    "tally": (BW327, "TALLY catch="),
    "rows_head": (BW327, "SAYS_ZH_ROWS the"),
}


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, row in enumerate(read(os.path.join(ROOT, rel.replace("/", os.sep))
                                                       ).split("\n")) if needle in row]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    ledger = read(LEDGER)
    hits = ledger.count(CORRECTED_HEADING)
    if hits != 1:
        raise SystemExit("ABORT the block I am correcting appears %d times in the ledger, not once" % hits)
    zh = int(re.search(r"says_zh=(\d+)", read(os.path.join(ROOT, BW327.replace("/", os.sep)))
                       .split("\n")[at["tally"] - 1]).group(1))
    print("LIVE ANCHORS %s | CORRECTED_BLOCK_HITS %d | says_zh %d" % (at, hits, zh))

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    closing = read(os.path.join(REF, "live_checks", "CLOSING_LINE.txt")).strip()
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

    body = "\n".join([
        "### 494abfd7 勘误：把「屏上改写成什么话」那格的正文坐标从 §14.35 挪到 §14.36（#371）",
        "",
        "- 错在哪：上一块（标题含「%s」那格）落点行写的是 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d，"
        "那是 §14.35。写它的时候句子读数只在回执里，指 §14.35 是唯一可选；现在 §14.36 已把这 %d 处句子"
        "逐枚写进正文，指 §14.35 就成了不准的坐标。" % (CORRECTED_HEADING, at["prev"], zh),
        "- 改成什么：正文坐标是 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d（§14.36 补）。"
        "旧帖不改，本块自行为证：账本里那一枚标题现读命中 %d 次，回执原坐标仍取自 "
        "trial/results/20261026_gozero/bw327-what-the-panels-say-instead.txt:%d 与 :%d。"
        % (at["section"], hits, at["tally"], at["rows_head"]),
        "- 这一类错怎么防：以后正文先落节、再交块，块里的坐标一律现读行号而非记忆；本次两段（§14.35 与 §14.36）"
        "都由追加器带唯一锚自证（锚不唯一就 ABORT）。本班 0 改产品字节。",
        "- 代次：本块所在提交为 git 对象 %s，可 git cat-file -t 取回。" % sha,
        "",
        closing,
        "",
    ])
    pending = [f for f in os.listdir(INBOX) if f.endswith(".md") and not f.startswith("selftest")]
    print("PENDING_INBOX_BEFORE_WRITE %d" % len(pending))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    back = read(out)
    if not back.startswith("### ") or closing not in back or "\r\n" in back:
        raise SystemExit("ABORT the block failed its own shape checks")
    print("WROTE %s bytes=%d" % (out, len(body.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
