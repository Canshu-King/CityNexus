"""Append section 14.9: can every artifact the documents cite actually be retrieved?

The section reports the inventory the audit produced, keeps the two classes apart (untracked versus
unresolvable name), and refuses to call a scanner fragment a phantom piece of evidence.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
### 14.9 文中引到的工件能不能取回：389 个名里 336 个在库，33 个只在树上没入库，19 个是尺自己也认不出名

尺 trial/human_walk/_cmdr_cited_artifact_audit_r179.py:34 扫五份结果文档（DOCS_SCANNED 5），
把每个像文件名的引用拿出来，先在 `git ls-files` 的整路径里找，再在 basename 里找，
再分「被 .gitignore 吞了」「在树上但没入库」「按这个名字根本找不到」三档；
状态不许并成一个数。回执逐条清单在 trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6。

现读（代次 `57e9eddefbc80265c7365ff86deadb1b1fa55d59`，库内跟踪文件 11686 枚，文中不同引名 389 个）：

| 状态 | 数量 | 意思 |
| --- | --- | --- |
| 按整路径就在库里 | 167 | 直接可取回 |
| 换个路径在库里 | 169 | 可取回，但文中只写了短名（不带目录），要按 basename 才找得到 |
| 在树上但没入库 | 33 | 现在别人 clone 就拿不到 —— 例如 `390-go-cold.png`、`430-r54-plan-blocked.png`、`go-active-390-full.txt` |
| 被 .gitignore 吞掉 | 1 | `error-context.md` 一类，永远进不了库 |
| 按这个名字找不到 | 19 | 尺自己也认不全（如 `-2.png`、`-r4.txt`）：那是我的正则从中文标点处把长名切断了，不能拿去当"假证据"报 |

两点边界先说在前面：这 33 枚多数不属本班（更早班次的屏证，以及并发写者还在改的文件），
本班不在别人未提交的工件上动手；要收这一格是「把屏证与收据装进库」那张单的事，
需要点名逐枚决定，不能一把 `git add -A`。第二行那 169 枚是引用形制问题不是缺失问题，
修法是在文档里写全相对路径 —— 与 Q43 坐标门同一条口径（门只认 `文件:行`、blob、四十位、refs）。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    original = io.open(REPORT, encoding="utf-8", newline="").read()
    if "### 14.9" in original:
        print("ABORT 14.9 already present")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(original + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(original):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED 14.9 bytes_added=%d heading_hits=%d" % (
        len(block.encode("utf-8")), read_back.count("### 14.9")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
