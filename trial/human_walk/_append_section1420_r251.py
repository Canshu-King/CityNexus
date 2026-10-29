"""Append section 14.20: the stay route starts the journey without ever asking the gate."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.20 补（10-29 午前）：一按「选这家酒店」就出发，而那扇门从头到尾没被问过

§14.19 末登记的那处「产品内同形分歧」，本班没让它停在纸面上，直接拿真路由走了一遍。

- 走法：一枚独立探针 trial/human_walk/_cmdr_stay_plan_select_gate_r250.py，在自己的临时库上按顺序
  走产品真实路由（demo/reset → 建行程 → 房价捕获 → 住下方案生成 → 住下方案选用 → 方案选用门 → 出发门），
  同时用 trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:51 那把 trace 数 plan_authority_blocker
  的每一次回答（不只是拒绝，见 trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:75）。
  声明：这一趟的行程是探针通过产品自己的 POST 路由建出来的临时对象，不是主人手指踩过的屏，
  也没有手工灌库、没有桩、没有 DOM 注入。
- 读数一（分母）：整条走查里那扇门被问 零 次 —— 回执
  trial/results/20261026_gozero/bw250-stay-plan-against-select-gate.txt:3 记 GATE_ANSWERS_RECORDED 1，
  而那唯一一次是探针自己拿真数据直接问的正控制（同回执 :8 与 :22，seen_by_trace=True）。
  也就是说「零」不是尺没咬：尺在同一进程、同一枚方案上确实咬到过拒绝。
- 读数二（为什么会零）：住下方案选用那一刻就把行程和方案都推成出发态 ——
  backend/app/operations/v9.py:520 这个函数里 backend/app/operations/v9.py:761 写 plan.status=ACTIVE、
  backend/app/operations/v9.py:779 写 journey.status=ACTIVE；调用者是路由
  backend/app/main.py:10714 与它下面的 backend/app/main.py:10727。
  回执 :16 现读 JOURNEY_STATUS_RIGHT_AFTER_STAY_SELECT ACTIVE、:5 现读 PLAN STATUSES {"ACTIVE": 1}。
  之后旅客再按方案选用门，得到的是 backend/app/main.py:18182 那句状态挡回（实测 422
  「Only a candidate plan can be selected」，回执 :18）；再按出发门，
  backend/app/main.py:20015 那句「已是 ACTIVE 就回快照」直接放行（实测 http_status=200，回执 :20）——
  所以出发门里 backend/app/main.py:20040 那次调用根本没轮到。
- 读数三（门自己怎么说）：把这枚真方案直接递给那扇门，它答 UNRESOLVED_ACTIVITY_FACTS，
  返回臂与 §14.19 那三十九枚同一格（backend/app/services.py:799），
  所用内容地点 玖 枚全部是产品自己写的 backend/app/operations/v9.py:340 那把 provider、
  营业时间词是 backend/app/operations/v9.py:358 写的 NORMALIZED（回执 :7），
  而该词不在 backend/app/services.py:599 认的四词里，排除条件 backend/app/services.py:768 又不认这把 provider。
- 于是这条不再是「口径分叉」那么轻：同一枚方案，走路由能出发、问门会被拒。
  写者（backend/app/operations/v9.py:761 与 :779）与判者（backend/app/main.py:20040）之间没有握手，
  而 backend/app/main.py:19305 早就把同一把 provider 记成「服务器自有的排程结构」——
  三处各说各话。这一格该归 ORD-0708（营业时间未知要不要否决）与 #283 那道门一起裁，
  本班不代裁、0 改产品字节。
- 与屏证的关系：主人真机上走的是 Revolution 那条（住下方案不在屏上按），所以这格目前不是主人手下的现象；
  它是「路由能出发、门会拒绝」的形状差，属交付门禁的口径，不写成用户面上已发生的故障。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.20 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    lines = read_back.split("\r\n")
    head = [i + 1 for i, line in enumerate(lines) if line.startswith("14.20 补")]
    print("APPENDED bytes_added=%d hits=%d crlf_split_head=%s"
          % (len(block.encode("utf-8")), read_back.count("14.20 补"), head))
    return 0


if __name__ == "__main__":
    sys.exit(main())
