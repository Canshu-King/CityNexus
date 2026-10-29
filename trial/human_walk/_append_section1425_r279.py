"""Append section 14.25: the thirty cited-but-untracked artifacts are now committed."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.25 补（10-29 午）：把本班自己引用过却没入库的叁拾枚工件交进去了

§14.23 点到「叁拾叁枚在树上未入库」为止就没往下动 —— 那些是本班自己产出的屏证与仪表，入库属本班职责内，
不需要谁点单，所以这一格就地闭掉。

- 先把名字落回路径：尺 trial/human_walk/_cmdr_citable_untracked_r276.py:69 输出四档
  （唯一路径 / 同名多枚 / 找不到 / 已跟踪），叁拾叁枚引用名（回执
  trial/results/20261026_gozero/bw276-citable-untracked-paths.txt:2）里 叁拾 枚唯一解析到一枚路径，
  零 枚同名歧义，叁 枚在 trial/ 下找不到；合计 3.37 MiB（同回执 :5）。
  同名歧义为零这一条是刻意要求的：一枚名字对多枚路径时宁可点名，不许猜着提交。
- 尺自己也坏过一次且是自己露的：第一版取字段错位，把「(cited」当成文件名解析出 壹 枚、全部找不到 ——
  现在 trial/human_walk/_cmdr_citable_untracked_r276.py:33 加了断言（解析出的名字必带扩展名，
  否则整把尺 ABORT），不再让坏读法伪装成空结果。
- 入库：提交 b423f66abec0fd74683140cb682cc0c4664a7aed（31 枚路径，走 trial 那套提交门，
  FOREIGN_STAGED before=21 after=21，没卷走并发写者的暂存条目）。
- 复算：引用尺重跑后「在树上未入库」从 叁拾叁 降到 叁，整路径在库 贰佰叁拾陆、
  换路径在库 贰佰叁拾贰、不可取回合计 拾柒（回执
  trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6 与 :8），
  该复算随提交 da74cda3d9593ac6599e59138553791b86488c97 入库。
- 剩下那 叁 枚不猜路径、贰 枚被 .gitignore 吞的形状保留点名 —— 短名引用（文档只写文件名不写目录）
  仍是 贰佰叁拾贰 枚那一档，可取回但不好读，属文档写法问题，另计。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.25 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d"
          % (len(block.encode("utf-8")), read_back.count("14.25 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
