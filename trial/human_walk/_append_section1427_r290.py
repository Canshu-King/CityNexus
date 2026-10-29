"""Append section 14.27: the accept door never asks the shared blocker, and why no evidence freezes."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.27 补（10-29 午）：「接受」那一按全程没问共享门，冻不出证据的成因是端点键与方案不同源

- 三把尺各管一段：trial/human_walk/_cmdr_accept_without_select_r285.py:56（走真路由并把每次作答记全）、
  trial/human_walk/_cmdr_accept_with_frozen_evidence_r288.py:56（把证据补齐那一档跑到哪算哪）、
  trial/human_walk/_cmdr_why_evidence_cannot_freeze_r289.py:67（只读普查上一把尺自己造的那枚临时库）。
- 读数甲（#356 甲的第一格）：行程还没有任何已选方案时按「接受」，服务端回 409，
  给旅客的那句是英文原句 `Trip Studio requires an active plan`
  （backend/app/main.py:18394 抛出，回执 trial/results/20261026_gozero/bw285-accept-without-select.txt:16），
  message_key 只有通用的 request.conflict——屏上没有任何中文说法接住它。
- 读数乙（这一节的主干）：整条「接受」路上，共享权威门被问 0 次
  （trial/results/20261026_gozero/bw285-accept-without-select.txt:35、
  trial/results/20261026_gozero/bw288-accept-with-frozen-evidence.txt:36）；
  同一进程里直接拿同一枚方案问那扇门，它当场拒（backend/app/services.py:799，
  用到 9 处地点、9 处内容地点，回执 trial/results/20261026_gozero/bw285-accept-without-select.txt:10）。
  「接受」自己那扇门只判冻结证据：它的自述就是「跑共享确定性门 over 一份冻结快照」
  （backend/app/main.py:18642），判据逐条是快照身份、完整性、过期、逐段分钟与货币
  （backend/app/main.py:18648 起到 backend/app/main.py:18699），对地点的营业与费用事实 0 处提及
  （trial/results/20261026_gozero/bw288-accept-with-frozen-evidence.txt:39）。
  所以 §14.21 那份「看得见门的三行」里，「接受」这一行是**看得见一扇门、但不是同一扇**。
- 读数丙：换成矩阵齐的那座城（CN-BEIJING，先前量过 56/56）仍然停在 503，
  「接受」没有造出任何新方案（trial/results/20261026_gozero/bw288-accept-with-frozen-evidence.txt:38）。
  这一格本班先前的仪表读反过一次：它把「那枚方案本来就是 ACTIVE」当成「接受把它推成 ACTIVE」，
  改判定为「只有接受自己产出的方案才算」后重跑，读数才落定（尺 trial/human_walk/_cmdr_accept_with_frozen_evidence_r288.py:258 那一行的判定式）。
- 读数丁（成因，也是 §14.22 补二 那条预检的续弦）：那枚临时库里 mobility_facts 实有 30 行、
  全都挂在这枚行程上（trial/results/20261026_gozero/bw289-why-evidence-cannot-freeze.txt:5），
  但证据的端点键是 `arrival-…`、`stay:bei…` 这一类锚与住下报价的键
  （同回执 :9），而方案活动用的是 7 枚 UUID 形状的 place_id（同回执 :8），两者交集 0（同回执 :10）。
  正对照：本尺把自己那枚库的副本灌进 1 行、端点就用方案真用的前两枚 place_id，
  交集立刻从 0 变 2（同回执 :20 与 :22 RULER_BITES_ON_THE_COPY YES）——
  所以那个 0 是库里的事实，不是这把尺接不上。
- 口径收窄一处，不发全表式勘误：交接稿 trial/results/20261029_HANDOFF_GO_FROM_BLANK_r185.md:78
  那句「零事实是**还没捕**、不是**捕不到**」在住下这条路上要读成「**捕了**，但端点键与方案不同源，
  所以对这版方案不可用」；课堂栈那枚「两张表总行数现读为零」是另一枚库、另一条路径的读数，不改口。
- 待裁三件（本班 0 改产品字节、不代裁）：一，「接受」要不要也过共享权威门——现在它只过证据门，
  一旦证据齐了就能把一版地点事实仍未决的方案写进出发态；二，冻结证据的端点键是否统一到 place_id
  （不统一则任何住下生成的方案都冻不出证据，「按这一版安排」这类操作对旅客永久不可达）；
  三，409 那句英文原句与内部术语是否端给旅客。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.27 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.27 补")
    print("APPENDED bytes_added=%d heading_hits=%d" % (len(block.encode("utf-8")), hits))
    return 0 if hits == 1 else 6


if __name__ == "__main__":
    sys.exit(main())
