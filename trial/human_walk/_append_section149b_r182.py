"""Append the 14.9 correction: the retrieval scanner had two shape defects of its own."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.9 补（同日晚）：本班这把尺自己有两格形制缺陷，改掉后数重算一次，前文那行不改写。

- 扩展名正则把 `ts` 排在 `tsx` 前面，于是每一处 `.tsx` 引用都被读成 `.ts` 名，「按名字找不到」虚高到五十五枚；
  改成长扩展优先（trial/human_walk/_cmdr_cited_artifact_audit_r179.py:22），并把 `${DIR}/x.png`、`*/.mjs`
  这类模板与通配单独计一档 `not-a-citation-template-or-glob`（同文件 :28）。
- 重算后的现读（代次 `a2763a0843d19c09db799c7866f5d80fd119be5a`，回执
  trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6）：文中不同引名 402 个 ——
  整路径在库 169、换路径在库（文中只写短名）173、在树上未入库 33、被 .gitignore 吞 2、
  模板/通配 13、按名字仍找不到 12。
- 那 12 枚再核一层才敢定性：它们是本班文档里用省略号缩写的文件名（如 `bf110…-r4.txt`、`bn122…390.txt`）
  与正文举例（`json`、`mine.txt`、`theirs.tsx`），不是「引了不存在的证据」；
  真缺口仍是「在树上未入库」那 33 枚，逐枚点名这一条等点单。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.9 补" in text:
        print("ABORT the correction is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d" % (
        len(block.encode("utf-8")), read_back.count("14.9 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
