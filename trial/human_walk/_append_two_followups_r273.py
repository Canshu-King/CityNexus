"""Append two follow-ups written in one beat: a report note (CRLF) and handoff notes (LF)."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"
HANDOFF = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261029_HANDOFF_GO_FROM_BLANK_r185.md"

REPORT_BLOCK = """
14.22 补（同一拍）：那捌 次 503 罩的是两个入口，不是一条

backend/app/main.py:19060 与 backend/app/main.py:19061 两枚路由装饰器（trip-studio/accept 与
plans/accept-reorder）挂的是同一个函数体 backend/app/main.py:19062，其内部只有一处实现入口
backend/app/main.py:19071。所以 §14.22 的读数对两条 URL 同样成立 —— 说清楚这是"共用同一实现"的
推及，不是我把第二条 URL 又真跑了一遍。
"""

HANDOFF_BLOCK = """
- 14.23 与 14.24 的交接句（10-29 午）：那把引用取回尺又改了自己一次（模板/通配的标记在目录部分，
  原先只看文件名 ⇒ 两枚模板被当成「找不到」），当代数在
  `trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6`，叁拾叁枚未入库自同回执 :9 起逐枚点名。
  更要紧的一格：玖 处**已暂存**的前端组件 import 着 git 不认识的模块（共 柒 枚模块在树上没 add、
  也没被 .gitignore 命中），分层读数 `trial/results/20261026_gozero/bw270-half-delivery-generation.txt:3`
  记 HEAD 零处 —— 所以现尖没坏，坏在下一笔提交。提交门已装闸
  （`trial/human_walk/_cmdr_pathspec_commit_gate_r119.py:111`，拒则 rc=6、不写东西），
  两向自测与真树判别都过了。接班的人别去替当事人 add：那 柒 枚是别人的写面，点名让当事人补一句即可。
- 同一拍还量到：`backend/app/main.py:19060` 与 `backend/app/main.py:19061` 两条 URL 共用同一个实现，
  所以 §14.22 的「一拖就 503」罩两个入口 —— 这是共用实现的推及，第二条 URL 没再真跑一遍。
"""


def append(path, block, marker, crlf):
    text = io.open(path, encoding="utf-8", newline="").read()
    if marker in text:
        print("SKIP %s already carries the note" % path)
        return 0
    body = block.strip("\n")
    if crlf:
        body = body.replace("\n", "\r\n") + "\r\n\r\n"
    else:
        if "\r\n" in text:
            print("ABORT %s stopped being LF-only" % path)
            return 3
        body = body + "\n"
        if "\r\n" in body:
            print("ABORT refusing to introduce CRLF")
            return 4
    io.open(path, "w", encoding="utf-8", newline="").write(text + body)
    read_back = io.open(path, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed in %s" % path)
        return 5
    if not crlf and "\r\n" in read_back:
        print("ABORT the write flipped line endings in %s" % path)
        return 6
    print("APPENDED %s bytes=%d hits=%d"
          % (path.split("\\")[-1], len(body.encode("utf-8")), read_back.count(marker)))
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rc = append(REPORT, REPORT_BLOCK, "14.22 补", True)
    if rc:
        return rc
    return append(HANDOFF, HANDOFF_BLOCK, "14.23 与 14.24 的交接句", False)


if __name__ == "__main__":
    sys.exit(main())
