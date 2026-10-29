"""Write the #362 ledger block: the 17 not-retrievable citations, itemised, with four kinds of fix.

Anchors are re-read from the receipts at invocation time; a non-unique anchor aborts instead of
shipping a coordinate that cannot be retrieved.  The closing line comes from CLOSING_LINE.txt.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
GOZERO = "trial/results/20261026_gozero"
OUT = r"D:\moodle\_qoder_ledger_inbox\494abfd7_0549.md"

CITES = {
    "audit_declared": (GOZERO + "/by179-cited-artifact-audit.txt", "NOT_RETRIEVABLE"),
    "short_forms": (GOZERO + "/by179-cited-artifact-audit.txt", "SHORT_FORM_CITATIONS"),
    "sheet_source": (GOZERO + "/by305-not-retrievable-one-by-one.txt", "SOURCE trial/results"),
    "sheet_tally": (GOZERO + "/by305-not-retrievable-one-by-one.txt", "TALLY a rule ignores"),
    "sheet_legacy": (GOZERO + "/by305-not-retrievable-one-by-one.txt", "frontend/src/app/LegacyApp.tsx"),
    "sheet_note": (GOZERO + "/by305-not-retrievable-one-by-one.txt", "nothing here was added"),
    "ruler_pool": ("trial/human_walk/_cmdr_not_retrievable_one_by_one_r305.py",
                   "def tracked_and_on_disk"),
    "ruler_guard": ("trial/human_walk/_cmdr_not_retrievable_one_by_one_r305.py",
                    "fix the parser before publishing"),
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


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

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

    sheet = GOZERO + "/by305-not-retrievable-one-by-one.txt"
    audit = GOZERO + "/by179-cited-artifact-audit.txt"
    body = "\n".join([
        "### 494abfd7 交「17 枚取不回引用」的逐枚清单与四档修法（#362，#347 的续）",
        "",
        "- 为什么再补一刀：§14.24 之后这类只剩 17 枚，可「17」这个数没法点单。尺 trial/human_walk/"
        "_cmdr_not_retrievable_one_by_one_r305.py:%d 把每枚名字拿全仓路径（git 认的 + 未跟踪的）去碰，"
        "逐枚给结论与候选坐标；清单在 %s:%d 起，分档数在同回执 :%d。"
        % (at["ruler_pool"], sheet, at["sheet_source"], at["sheet_tally"]),
        "- 四档（共 17 枚，逐枚见回执）：档壹 2 枚——**文件其实在，只是引用没写目录**"
        "（例：`LegacyApp.tsx` 的真路径是 frontend/src/app/LegacyApp.tsx，同回执 :%d；那枚属前端写者的面，"
        "本班只报不动）；档贰 8 枚——有最接近的真文件，是引用写法省了目录或写了省略号，"
        "照回执给的候选改写即可；档叁 3 枚——形状被 .gitignore 规则吞掉（error-context.md 一类），"
        "**永远提交不进去**，只能换证据形态或不再当可取回证据引用；档肆 4 枚——盘上没有任何文件对得上，"
        "需要发一条勘误说明。" % at["sheet_legacy"],
        "- 尺自己带两道闸：解析到的条数必须等于 by179 声明的 17（trial/results/20261026_gozero/"
        "%s:%d 那行），不等就 ABORT 不出表（闸在 trial/human_walk/"
        "_cmdr_not_retrievable_one_by_one_r305.py:%d）；第一版只把 trial/ 下的未跟踪文件放进池，"
        "于是对 by179 报 present-but-untracked 的前端文件说了「没匹配」——两把尺打架是我的池窄了，"
        "改成收全仓未跟踪项后两把尺一致。" % (audit.split("/")[-1], at["audit_declared"],
                                              at["ruler_guard"]),
        "- 与「短名引用」那族分清楚：by179 另计 232 条**可取回但没写目录**的引用（%s:%d），"
        "那是一族、不是这 17 枚；两族口径不并表。" % (audit, at["short_forms"]),
        "- 请点的动作（一次点一档即可）：壹贰两档是**本班能自己改的引用写法**（发新条不改旧正文那一口径"
        "仍适用）；叁要裁「这类证据还要不要在正文里当坐标用」；肆要裁「勘误写在哪」。"
        "本班 0 改产品字节、0 动别人的面（回执 :%d 那行：没加、没改名、没删）。"
        % at["sheet_note"],
        "- 落点与代次：上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d；"
        "本批工件的提交代次为 git 对象 %s，可 git cat-file -t 取回。" % (at["prev_section"], sha),
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
