"""Append section 14.11: the nine invariant guards, re-run at the tip, each one named by what it hit.

The report is CRLF-dominant, so the block is written with explicit CRLF and the appender asserts that
every byte before the insertion point is untouched.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.11（10-29 上午）：护壁句那一堆不再「它自己写了话就算」—— 现尖重跑一次，逐枚点名它到底撞上了什么。

- 现尖重跑（不是沿用上一代的日志）：九枚一起点，回执 `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:2`
  是代次行、`:3` 是解释器（Python 3.12.14 现读）、`:26` 是末行读数，九条消息全文在
  `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:7` 到 `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:15`。
- 逐枚点名（每条都另有一行源码现读或第二把尺背书；下表右侧就是那条背书）：

| 护壁句 | 它守的条例 | 现读到的漂移 | 背书 |
| --- | --- | --- | --- |
| `tests/test_qoder_anywhere_matrix_truth.py:375` | 越界（N=11）的 OD 矩阵必须判 FAILED | 实际 `CAPTURED` ⇒ 这道门在这台机器上没咬 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:7` |
| `tests/test_qoder_anywhere_provider_independence.py:70` | §17C：默认套件里不得有真出网调用 | 抓到两处真调用：`backend/tests/test_qoder_catalog_hydration.py:609` 与 `backend/tests/test_qoder_provider_identity.py:363`（前一行文本已现读：`httpx.get("https://photon.komoot.io/api/?q=instrument-selftest", timeout=1.0)`） | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:8` |
| `tests/test_qoder_anywhere_provider_truth.py:78` | 规范化目录至少要有地点可查 | 答复里地点集合为空；键含 `candidates`、`coverage`、`hard_gaps`、`malformed_candidates` 等 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:9` |
| `tests/test_qoder_ord0296_write_deadline.py:212` | 写锁等待只许写在一处 | `backend/app/catalog_hydration_operations.py:415` 硬写 `PRAGMA busy_timeout = 500`，与 `backend/app/core/config.py` 的 `settings.write_busy_timeout_ms` 并存 = 两处 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:10` |
| `tests/test_qoder_ord0307_credential_gate.py:187` | 套件环境下 verdict 应为 `CREDENTIAL_GATE_CLEAR` | 实际 `CREDENTIAL_LITERAL_OUTSIDE_PRODUCT_PATH`，且 `env_present` 读数为 0 ⇒ 扫描器在产物路径外抓到疑似字面量；是哪一枚文件还没读到，所以不下结论 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:11` |
| `tests/test_qoder_ord0332_error_receipt.py:207` | 失败的回执不落库 | 库里有名字含 `receipt` 的表 —— 但这些表是别的特征加的（`backend/app/db/models.py:364`、`backend/app/db/models.py:1664`、`backend/app/db/models.py:2665`）⇒ 要么设计已变、要么这条 `LIKE '%receipt%'` 太宽；分辨要数实际表名，留作下一步 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:12` |
| `tests/test_qoder_ord0402_recycle_bin.py:160` | ORD-0402 不许动 `list_journeys` 这扇门 | 登记的基线字节与现函数文本不一致 ⇒ 门动过，或基线该重登记，二者要裁 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:13` |
| `tests/test_qoder_ord0402_recycle_bin.py:295` | 契约里每个 operationId 都要在生成客户端有读者 | 六枚缺席；第二把尺独立复算出同一个数：`trial/results/20261026_gozero/bw201-contract-client-gap.txt:4` 契约 170、`:5` 客户端引用 164、`trial/results/20261026_gozero/bw201-contract-client-gap.txt:6` 缺席 6（并被尺强制等于护壁句自报的那个数） | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:14` |
| `tests/test_qoder_ord0434_share_grants.py:238` | ORD-0434 承诺匿名读那一扇一字不动 | 现读为动过 | `trial/results/20261026_gozero/bw200-guard-nine-at-tip.txt:15` |

- 缺席那六枚逐字点名（就是要重生成客户端的范围）：`accept_unknown_price_route_api_v1_journeys__journey_id__agent_goal_tasks__task_id__plans__plan_version_id__accept_unknown_price_post`、
  `answerJourneyClarification`、`freeze_plan_routes_api_v1_journeys__journey_id__agent_goal_tasks__task_id__plans__plan_version_id__freeze_routes_post`、
  `read_travel_gaps_api_v1_journeys__journey_id__agent_goal_tasks__task_id__plans__plan_version_id__travel_gaps_get`、
  `research_goal_places`、`resumeJourneyMission`（见 `trial/results/20261026_gozero/bw201-contract-client-gap.txt:9` 往下）。
- 尺：`trial/human_walk/_cmdr_contract_client_gap_r201.py` —— 它自己带三道闸：契约枚数非零、缺席数必须等于护壁句自报的那个数、
  引用数＋缺席数必须等于契约总数；任何一条不等就 ABORT，不发布第二个版本的数。
- 本班没改这些护壁句，也没为让它们变绿去动断言；这里只把「它撞到了什么」量出来。修法（把两处真出网调用挪进
  `backend/live_checks/` 的 opt-in smoke、重生成 `frontend/src/generated/api.ts`、重登记 `list_journeys` 基线、
  收紧那条 `LIKE`）都等点单。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.11（10-29 上午）" in text:
        print("ABORT section 14.11 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.11（10-29 上午）")
    print("APPENDED bytes_added=%d hits=%d" % (len(block.encode("utf-8")), hits))
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.11（10-29 上午）"):
            print("SECTION_HEAD line=%d" % i)
    return 0


if __name__ == "__main__":
    sys.exit(main())
