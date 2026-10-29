"""Append section 14.26: the commit door gained an import gate, and a sibling leg's bare commit was fixed."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.26 补（10-29 午）：提交门加了一格「引用落空即拒」，另一条腿的裸 commit 也当场补上 pathspec

- 门那一格（§14.24 已记）不再重复；这一节记同型的第二处。查「还有没有别处绕开门」时撞到：
  值守的尺在另一棵树里 `git add` 带着自己那枚路径、`git commit` 却不带 —— 正是提交门当初要防的形状。
  副本里能看见修好的两处：trial/human_walk/_push_rulers_r2_pathspec_shape_r282.py:96（提交带 pathspec）
  与 trial/human_walk/_push_rulers_r2_pathspec_shape_r282.py:105（提交完再比对「这次到底带走了哪几条路径」，
  多带一条就 rc=7 —— 原来那道「纯度验」只查整棵树里有没有产物目录名，看不见多带别人的暂存条目）。
- 判别的两臂（一次性小仓，探针 trial/human_walk/_cmdr_commit_shape_protection_r281.py:48 与 :56）：
  裸 commit 那臂实测把并发写者 staged 的那枚文件单独提交了上去
  （回执 trial/results/20261026_gozero/bw281-commit-shape-protection.txt:2 ——
  carried 里只有别人的文件名，本班那一行代码根本没出去，等于替别人做了一次提交）；
  带 pathspec 那臂只带走自己那枚、对方的条目仍留在 index
  （trial/results/20261026_gozero/bw281-commit-shape-protection.txt:3），
  合起来 VERDICT PROTECTED（同回执 :4）。前臂不成立就不足以说明后臂防住了什么，所以两臂都要跑。
- 归属照口径：那棵树的 index 归它自己的写者，本班只就地改了脚本、没有在那棵树里提交任何东西；
  改动以副本形式随本班枝入库，保证坐标可取回。要落那棵树，请它的写者自己提交。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.26 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d"
          % (len(block.encode("utf-8")), read_back.count("14.26 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
