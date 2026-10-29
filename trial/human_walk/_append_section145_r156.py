"""Append section 14.5 to the go-from-blank report without disturbing its mixed line endings.

The report body is mostly CRLF, so the appended block uses CRLF too and the instrument refuses to
touch any byte before the insertion point.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
### 14.5 那两枚 KeyError 不是契约改名：四枚文件一把跑，十六枚红归到同一族夹具裸读

跑法（现读）：`cd backend && python -m pytest -q tests/test_r64_member_side_quest.py
tests/stateful/test_journey_truth_state_machine.py tests/test_provider_runtime_gate.py
tests/test_qoder_activity_identity_contract.py -p _cmdr_unsigned_experience_probe_r155 --tb=no -p no:warnings`
（PYTHONPATH 指向 trial/human_walk，解释器 3.12.14）。末行原样：`42 failed, 42 passed in 14.21s`。
探针 trial/human_walk/_cmdr_unsigned_experience_probe_r155.py 只观察：它把 starlette 的
TestClient.get 与 Client.get 各包一层（同一趟调用用 `_cmdr_r155_seen` 只记一次），记下 URL 里含
/experience 或 /events 的每一次读的状态、body 顶层键与是否带 Authorization，不改请求、不改响应、
不改任何产品字节。回执 trial/results/20261026_gozero/bu155-unsigned-experience-probe.txt。

套件侧读数（回执前四行，逐字）：`TOTAL /experience READS 44`、`SIGNED STATUS COUNTS {}`、
`UNSIGNED STATUS COUNTS {"401": 44}`、`READS PER DOOR {"/events": 10, "/experience": 34}`。
四十四个读全是不带凭证的读，全被 401 挡回；401 的 body 顶层只有 `error` 一个键，
`message` 原文是 `authenticated traveler credentials are required`。

分辨对照（同一趟旅程、同一扇门、同一条腿里，跑在测试还活着的时候 —— 挪到 sessionfinish 时
principal verifier 的会话夹具已拆，签发器直接 503 'CityNexus traveler principal verifier is not configured'，
那一格我在第一次跑时踩到并记在这里）：

- /experience 不带 bearer ⇒ `CONTROL UNSIGNED status=401 body_keys=['error']`；
  带 bearer ⇒ `CONTROL SIGNED status=200 has_active_plan_key=True active_plan_id=55523d40-cafe-5bd2-b30a-de057ec7a839`。
- /events 不带 ⇒ `EVENTS CONTROL UNSIGNED status=401 body_type=dict first_item_type=str`
  —— 把 401 的 dict 当列表遍历，拿到的第一个元素就是字符串，这正是 stateful 那十枚栈尾
  `AttributeError: 'str' object has no attribute 'get'` 的成因；
  带 ⇒ `EVENTS CONTROL SIGNED status=200 body_is_list=True item_count=0 traveler_id_known=True`。
  这条只证形状（list 对 dict-of-strings），不证条目：刚 reset 的新旅程本来就没有事件。

归因更正（§14.4 的数偏小）：那一节按 `--tb=line` 记的「KeyError active_plan：2 枚」只是这一族在
r64 一枚文件里露出来的两枚（tests/test_r64_member_side_quest.py:1840 与 :2063）。四枚文件一把现读，
同一族的夹具裸读是十六枚：

| 文件 | 现读红数 | 露出来的形状 | 读的门与行 |
| --- | --- | --- | --- |
| `tests/test_r64_member_side_quest.py` | 2 | KeyError 'active_plan' | backend/tests/test_r64_member_side_quest.py:1840 |
| `tests/test_qoder_activity_identity_contract.py` | 2 | KeyError 'active_plan' | backend/tests/test_qoder_activity_identity_contract.py:103 |
| `tests/test_provider_runtime_gate.py` | 2 | 断言把 401 body 当 200 答比 | backend/tests/test_provider_runtime_gate.py:295 |
| `tests/stateful/test_journey_truth_state_machine.py` | 10 | AttributeError 'str' object has no attribute 'get' | backend/tests/stateful/test_journey_truth_state_machine.py:267 |

十六枚与 §14.4 那廿六枚过期时钟族相加＝四十二枚，与本次末行的 42 failed 对齐（42+42=84 条收集，
本次没重算整套分母）。

产品侧不动：`active_plan` 在 app/stay_mobility.py:2052 是无条件写进投影的键，路由
app/main.py:10325 只是往后加 recovery/flags，所以既不是契约改名也不是少发一个键；挡人的是
app/main.py:10323 那次 `_authorize_private_journey_read`，它拒得对（私有旅程读要 bearer 是 10-26 收紧后的口径）。
要修的是夹具的读面：r64 一枚文件里已有签名臂 `_auth`（backend/tests/test_r64_member_side_quest.py:84），
给这些裸读补上即可；stateful 那一枚整个模块没有任何签名臂，得先加一枚再逐处补，属具名的夹具改动。
这一刀我不自取：它超出刀三「只修过期断言」划下的范围，报上去等点单。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    original = io.open(REPORT, encoding="utf-8", newline="").read()
    if "### 14.5" in original:
        print("ABORT 14.5 is already in the report; refusing to append a second copy")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    updated = original + block
    io.open(REPORT, "w", encoding="utf-8", newline="").write(updated)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(original):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED 14.5 bytes_added=%d size=%d->%d" % (len(block.encode("utf-8")), len(original), len(read_back)))
    print("14.5 HEADING COUNT %d" % read_back.count("### 14.5"))
    print("TAIL %r" % read_back[-70:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
