"""Append sections 14.23 and 14.24: the citation ruler's third defect, and the half-delivery gate."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.23 补（10-29 午）：那把「引用取回」尺第三次改自己，数重算一次

- 又抓到一格形制缺陷：判定「这不是引用（模板/通配）」的正则在
  trial/human_walk/_cmdr_cited_artifact_audit_r179.py:35，
  而它原先只看 basename —— 可 `${DIR}/x.png`、`*/.mjs` 这类标记偏偏在目录部分，
  于是两枚模板掉进「按名字找不到」里，把缺口数抬高了贰枚。
  改在 trial/human_walk/_cmdr_cited_artifact_audit_r179.py:77（判整串），重算的当代读数在
  trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6 ——
  模板/通配 拾柒、按名字找不到 拾贰、在树上未入库 叁拾叁、整路径在库 贰佰贰拾捌、
  换路径在库 贰佰零伍（短名引用同回执 :7，不可取回合计同回执 :8），代次记在同一回执 :2。
- 叁拾叁枚「在树上未入库」这次逐枚点名了，就在同一回执 :9 起，一枚一行、各带引用它的文档名；
  其中绝大多数是屏证与仪表输出，只有一枚是产品源文件 —— 那一枚不在这叁拾叁枚的口径里说话，
  它单独记下一节。

14.24 补（10-29 午）：并发写者交了一半 —— 玖 枚已暂存的组件引用着 git 不认识的模块，提交门现在会挡

- 尺：trial/human_walk/_cmdr_imported_but_untracked_r267.py 扫「已跟踪或已暂存的组件 import 了
  一枚只以未跟踪文件存在的模块」。它第一版恒报 零 —— resolve 把 frontend/src 拼了两遍
  （修在 trial/human_walk/_cmdr_imported_but_untracked_r267.py:42），是假绿；
  补了正控制（手工已知的 cityNamed 那一格必须出现，否则尺自己 ABORT）后，
  当代读数 拾贰 处（trial/results/20261026_gozero/bw267-imported-but-untracked.txt:4，
  自检通过同回执 :29）。
- 断在哪一代：另尺 trial/human_walk/_cmdr_half_delivery_generation_r270.py 逐枚验 HEAD 版、
  暂存版、工作树版 —— 已提交线 零 处（回执 trial/results/20261026_gozero/bw270-half-delivery-generation.txt:3），
  只在暂存版 玖 处（同回执 :4），只在工作树 叁 处（同回执 :5）；缺失模块去重 柒 枚（同回执 :21），
  全部 not-gitignored（不是被忽略，是忘了 add）。
  所以：现尖没坏，坏的是「下一笔把这些组件提交出去」那一下。
- 闸装进写的那扇门：trial/human_walk/_cmdr_pathspec_commit_gate_r119.py:67 是判据，
  :111 在 git add 之前拦，拒则 rc=6 且不写任何东西；同一笔交付里点名的模块算可解析（否则会把完整交付误拒）。
  两向都验过：自测第四臂 先拒「只交组件」再收「组件+模块一起交」
  （trial/human_walk/_cmdr_pathspec_commit_gate_r119.py:199 与 :207，整套 SELFTEST_RC=0）；
  真树判别拿 backend 之外那一枚危险组件（frontend/src/features/setup/JourneyTrialSetup.tsx，
  其暂存版第捌行 import ./cityNamed）走门，实测 REFUSE rc=6 并点名缺的模块。
- 本班没有替别人 add 那柒 枚模块（那是当事人的写面），也没提交那玖 枚 staged 组件；
  要谁补、什么时候补，请号令者对当事人点一句。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.23 补" in text or "14.24 补" in text:
        print("ABORT the sections are already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits_23=%d hits_24=%d"
          % (len(block.encode("utf-8")), read_back.count("14.23 补"),
             read_back.count("14.24 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
