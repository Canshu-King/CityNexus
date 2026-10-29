"""Append section 14.19: the thirty-nine authority refusals attributed to one arm."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.19 补（10-29 晨）：那三十九枚「方案不是权威」的红，第一次落进具体某一臂

前文（§14.17）把这三十九枚记作「侧面未量」，本节把侧面量出来，前文不改写。

- 量法：一枚只观察的 pytest 插件（trial/human_walk/_cmdr_sealed_arm_state_r245.py），
  在 plan_authority_blocker 返回的瞬间抓局部状态。判「观察-only」的尺是同数对照：
  不带插件 18 failed / 9 passed（11.97s），带插件仍 18 failed / 9 passed（54.28s），
  只有耗时变。三臂各落一份回执（同一把尺、文件名按臂分开，
  trial/results/20261026_gozero/bw245-sealed-arm-state-v13.txt / -sealedpair.txt / -staylife.txt）。
- 三十九枚全部从同一行返回：backend/app/services.py:799，即「既没封套、又非课程估算、又非用户认价」
  那最后一臂。返回臂唯一（回执 :3 sealed 臂三十九、他臂零）。
- 命中维度也唯一：探针读的壹佰叁拾贰枚地点行，opening 状态全是 NORMALIZED（回执 :8），
  而判据认的四个词是 NORMALIZED_VALID / OFFICIAL_WEB_VERIFIED / VERIFIED_PROVIDER / CLOSED
  （backend/app/services.py:599）；成本侧则全部已解（cost_evidence 全在，回执 :10，
  status 全 KNOWN，回执 :11，amount_minor 无一为 null，回执 :12）。所以这不是「价钱没核」，
  是「营业时间词表不认」。三十九次拒绝分布在贰拾贰枚用例上（回执 :38）。
- 封套那一格也确实没挂上：同一批地点行的 metadata 里 authority_envelope 壹佰叁拾贰枚全为缺席
  （回执 :7），而封套豁免读的正就是这个键（backend/app/services.py:791）。
- 出处链条：这批测试从 backend/tests/test_v13_integrity.py:36 借了 _journey_with_inputs，
  该 helper 定义在 backend/tests/test_v12_authoritative_trip_execution.py:15，
  它在 backend/tests/test_v12_authoritative_trip_execution.py:104 写 status=NORMALIZED，
  并在 backend/tests/test_v12_authoritative_trip_execution.py:106 起的 metadata 里不放 envelope
  （其中成本那一格在 backend/tests/test_v12_authoritative_trip_execution.py:111，倒是写全了）；
  同文件 backend/tests/test_v12_authoritative_trip_execution.py:122 另有一枚现成的封套步骤
  _seal_v12_test_plan，把每枚活动地点的 metadata 写成 SEALED_DEMO_FIXTURE，
  v13 借了造数据的 helper、没借这一步。
- 分辨臂（同尺、不改任何字节）：调用了那步封套的 backend/tests/test_r28_execution_truth.py:80 与
  backend/tests/test_r55_live_progress_drift_product.py:88 一起跑，主用例仍绿，
  同一探针在该臂只记到叁次 sealed 臂拒绝（回执 -sealedpair :3），且这三次正是那枚封套 helper
  自述要留的负对照（backend/tests/test_v12_authoritative_trip_execution.py:125 起那两句，
  它遍历的范围也在同文件 backend/tests/test_v12_authoritative_trip_execution.py:129，
  只封传进去的那一枚方案所用地点，未封的那一枚照旧拒）。
  另设一条不经过这扇门的臂：backend/tests/test_v8_stay_mobility.py 全程 plan_authority_blocker
  调用零次（回执 -staylife :3）。
- 由此，这叁拾玖枚从「侧面未量」改记为夹具侧缺一格声明：补法一行级（compose 之后对返回方案调
  _seal_v12_test_plan），有同树先例；或者把该 helper 的营业时间词换成判据认的那四个之一。
  两条都属夹具改动，未点单不动。
- 顺带量到一处同形分歧，只登记不判死：产品自己的 backend/app/operations/v9.py:358 也给地点行写
  status=NORMALIZED，其 provider_key 是 backend/app/operations/v9.py:340 那个值，
  不在选用门排除的锚点之列（排除只认 backend/app/services.py:768 那一把 provider）；
  而 backend/app/main.py:19305 却把同一 provider 归入「服务器自有的排程结构」。
  本次实测没有走到那扇门（staylife 臂调用零次），所以这条只算两处口径分叉，不算用户面上的缺陷。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.19 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    lines = read_back.split("\r\n")
    head = [i + 1 for i, line in enumerate(lines) if line.startswith("14.19 补")]
    print("APPENDED bytes_added=%d hits=%d head_line=%s"
          % (len(block.encode("utf-8")), read_back.count("14.19 补"), head))
    return 0


if __name__ == "__main__":
    sys.exit(main())
