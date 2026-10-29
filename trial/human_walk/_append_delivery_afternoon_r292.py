"""Append the afternoon note to the delivery document (LF-only file)."""

import io
import os
import subprocess
import sys

DELIVERY = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"
REPORT = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
午后补记（10-29 12:3x）：「接受」那一按的门量清了，冻不出证据的成因也量出来了

- 主人要做的动作没变（还是那三件：走课堂 :14462 那代亲测、平板 USER_VERIFIED 仍空、要点真路线得先让
  那一栈真捕一次）；本班新增的是下面这些现场事实，不需要主人动手就能读。
- 新增读数：行程还没选过任何方案时按「接受」，屏上会拿到 409 与一句英文原句
  `Trip Studio requires an active plan`——屏上没有中文说法接它（正文 §14.27 读数壹）。
- 主干读数：整条「接受」路上，那道会否决「地点事实仍未决」的共享门被问 0 次；同一枚方案直接问它，
  它当场拒。接受自己那扇门只判冻结证据（身份、完整性、过期、逐段分钟、货币、时间），
  对营业与费用事实 0 处提及（§14.27 读数贰、叁）。
- 成因读数：不是「城市没矩阵」——换成矩阵齐的城仍停在 503。是那枚库里实有的 30 行移动证据
  把端点记成了 `arrival-…`／`stay:bei…` 这类锚与住下报价键，而方案走的是 UUID 形状的 place_id，
  两者交集 0；同一把尺往自己的副本灌一行真 place_id 端点，交集立刻变 2，所以那个 0 是库里的事实
  （§14.27 读数伍）。
- 交上去待裁三件：接受要不要也过共享门；证据端点键是否统一到 place_id；409 那句英文端不端给旅客。
  本班 0 改产品字节，没替任何人裁。
- 没改善的部分照口径点名：这「接受」一按在有无键的 canary 上都到不了成功态，所以「按这一版安排」
  对旅客仍未真走通；平板那一代的亲测仍未做；课堂栈仍停在同一代不动。
- 落点：正文在 %s:%d；本批工件的提交代次为 git 对象 %s。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(DELIVERY, encoding="utf-8", newline="").read()
    if "午后补记（10-29 12:3x）" in text:
        print("ABORT the note is already appended")
        return 4
    root = r"D:/moodle/_cmdr_rescue_v3_1022"
    lines = io.open(os.path.join(root, REPORT.replace("/", os.sep)),
                    encoding="utf-8", errors="replace").read().split("\n")
    hits = [index + 1 for index, row in enumerate(lines) if row.startswith("14.27 补")]
    if len(hits) != 1:
        raise SystemExit("ABORT the section anchor is not unique: %s" % hits)
    sha = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", root, "cat-file", "-t", sha],
                      capture_output=True, text=True, check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    block = (BLOCK % (REPORT, hits[0], sha)).strip("\n") + "\n\n"
    io.open(DELIVERY, "w", encoding="utf-8", newline="").write(text + block)
    back = io.open(DELIVERY, encoding="utf-8", newline="").read()
    if not back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    if "\r\n" in back:
        print("ABORT the delivery file must stay LF-only")
        return 6
    print("APPENDED bytes_added=%d hits=%d section_line=%d head=%s"
          % (len(block.encode("utf-8")), back.count("午后补记（10-29 12:3x）"), hits[0], sha[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
