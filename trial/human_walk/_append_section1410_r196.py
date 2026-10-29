"""Append section 14.10: the fifty-four unattributed reds, emptied with proof rather than renamed.

The report keeps CRLF as its dominant newline, so the block is written with explicit CRLF and the
appender asserts that every byte before the insertion point is unchanged.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.10（10-29 上午）：整套红里那「未定性」的五十四枚，现在一枚不剩地摊开了 —— 不是改标签，是把每一枚的来源摆出来。

- 先摊清单：尺 `trial/human_walk/_cmdr_unattributed_inventory_r194.py` 直接 import r164 的分组逻辑（不复制解析器，
  所以清单不可能和已发布的表各说一套），回执 `trial/results/20261026_gozero/bw194-unattributed-inventory.txt:1`：
  桶里 54 枚、分 54 组、牵涉 36 个文件；它自己还有一道对账闸 —— 清单数必须等于普查表已登的 54，不等就 ABORT。
- 再加类别：尺 `trial/human_walk/_cmdr_full_red_reason_census_r195.py`，回执
  `trial/results/20261026_gozero/bw195-red-census-extended.txt:6`。每个新类别都要靠一条**逐字出现在失败消息里**的字串命中，
  命中字串逐条登在 `trial/results/20261026_gozero/bw195-red-census-extended.txt:10` 往下；三处硬对账：
  记录数仍等于 pytest 自己报的那枚（同文件 `:4`）、挪出的三堆必须正好等于已发布的 54（`:6` `:7` `:8`）、
  旧标签「not yet attributed」必须归零（`:9` 表末项）。
- 去向：具名因类 36 枚、自发护壁句 9 枚（断言自己写清了撞了哪条例，仍要逐例再读，所以**不计入已解释**）、
  剩下 9 枚逐例读源码定性（下表，行号都是断言那一行的现读）。

| 位置 | 那行在读什么 | 现读到的形 |
| --- | --- | --- |
| `tests/test_wp06_followup_assist.py:223` | `verified["mobility"]["provider"] == "mock-mobility"` | 实际是 `amap_walking`：夹具拿到真供应商，钉子还钉在 mock |
| `tests/test_revolution_r77_recovery.py:1333` | `cost["amount_minor"] == 50000` | 「大人500円」被解析成 500 个最小单位；测试按 500.00 放大 ⇒ 日元小数位口径 |
| `tests/test_v14_trial_readiness.py:71` | `provider_status["nominatim"] == "UNAVAILABLE"` | 实际 `NOT_CALLED`：这一趟根本没叫过那条腿 |
| `tests/test_wp06_postgate_hardening_next.py:90` | `row.status == "ACKNOWLEDGED"` | 实际 `RESOLVED`：事件收口用词与状态机换了 |
| `tests/test_v7_traveler_twin.py:275` | `fit(低步行+室内) > fit(户外)` | 两侧都是 `0.0`：偏好项没进打分 |
| `tests/test_v5_autopilot.py:104` | `assert body is not None`（轮询到 EXECUTED 才赋值） | 循环里没出现 EXECUTED ⇒ 自动动作没走到执行 |
| `tests/test_wp04a0_bridge.py:116` | 重读行程的答复 `== before` | `before` 本身就是一枚错误答复，两边只差 `trace_id` ⇒ 整身比较永不相等 |
| `tests/test_qoder_simulation_mode.py:293` | `body["journey_status"] == "PLANNED"` | 实际 `DRAFT` 且 `selected_plan_version_id=None`：prepare-scenario 没造出方案（与演示种子口径同属一条待裁） |
| `tests/test_qoder_ord0434_share_grants.py:377` | OWNER 能力集合 == 六枚列举 | 实际集合与列举不齐 ⇒ 那份枚举过期了 |

- 与产品门对表的现读（不是推测）：`DEMO_DATABASE_NOT_ISOLATED` 出自 `backend/app/demo_access.py:20` 与 `backend/app/demo_access.py:28`
  两道 503；`TRAVELER_PRINCIPAL_VERIFIER_NOT_CONFIGURED` 出自 `backend/app/main.py:9544` 与
  `backend/app/execution/member_place_invitation.py:62`。这两族的红停在「门拒绝」这一步，不是断言猜错形状。
- `KeyError` 一族十枚要说清分母：这些键在产品里**是有出处的**（如 `projection_status` 见 `backend/app/main.py:19797`、
  `current_activity_id` 见 `backend/app/agent/gateway.py:1278`），所以只能说「这一条答复里没带这个键」，
  不能说「产品没这个字段」—— 要定到哪一头，得逐枚把那一条门的分支读一遍，这一条仍未做。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.10（10-29 上午）" in text:
        print("ABORT section 14.10 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d" % (
        len(block.encode("utf-8")), read_back.count("14.10（10-29 上午）")))
    tail = read_back.rsplit("\r\n\r\n", 2)[-2][:80]
    print("SECTION_HEAD %s" % tail.replace("\r\n", " | "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
