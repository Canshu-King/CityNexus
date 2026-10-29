"""Append section 14.13: the KeyError family, attributed instead of left as "not yet read".

Section 14.10 explicitly left one claim unmade -- that the ten KeyError reds could only be described
as "this answer did not carry the key".  This closes it with two live reads: whether each call site
attaches any credential at all (per-file auth-marker count and the call as written), and where the
product actually emits the one key that is not about credentials (`error_type`, set only on an
exception path).

CRLF-dominant report: explicit CRLF block, plus the byte-preserving assertion before writing.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.13（10-29 上午）：§14.10 里留那句「KeyError 一族还没逐枚读到分支」的话，现在收了 —— 十枚分家，两族。

- 现读一：九个文件里有一枚带 auth 痕迹的文件之外，其余文件对鉴权标记的计数为零
  （`grep -c "Authorization|_auth|bearer|traveler_token"` 逐文件现读：`tests/test_wp04_endpoints.py` 零、
  `tests/test_wp06_postgate_hardening_next.py` 零、`tests/test_wp07_foundation_assist.py` 零、
  `tests/test_v16_integration.py` 零、`tests/test_r14_terminal_disruption_recovery.py` 零、
  `tests/test_wp06_twin_v2_gate.py` 零、`tests/test_qoder_anywhere_matrix_truth.py` 零）；
  而两枚有痕迹的文件（`tests/test_agent_mission_runtime.py` 计数一、`tests/test_v12_authoritative_trip_execution.py` 计数三）
  出事那一行的调用本身没挂任何头 —— 引文现读：`tests/test_agent_mission_runtime.py:447` 是
  `client.get(f"/api/v1/journeys/{journey_id}").json()[...]`，`tests/test_v12_authoritative_trip_execution.py:248` 是
  `client.get(f"/api/v1/journeys/{journey_id}/twin").json()["context"]["execution"]`。
- 所以这九枚（`current_activity_id` 两枚、`budget`、`traveler_id`、`context` 两枚、`trip`、`projection_status` 两枚）
  与 §14.7 那把只读探针对出来的是同一族：私有读口拿不到 bearer 就回 401，答复体只有 `{"error": {…}}` 那一套键，
  测试按成功体的形状去下标 ⇒ KeyError。**这一族归到凭证族那条待裁修单里，不再算"未定性"**。
- 现读二（唯一不是鉴问题的那枚）：`tests/test_qoder_anywhere_matrix_truth.py:466` 读的 `error_type`
  在产品里只在异常路径上出现 —— `app/integrations/mobility/runtime.py:189`、`app/integrations/mobility/runtime.py:318`、
  `app/integrations/mobility/runtime.py:383` 三处都在 `except` 里赋值。⇒ 分类答复走 CAPTURED 那一支时本来就不带这个键，
  测试却无条件读它。这与 §14.11 那条「越界矩阵判 CAPTURED 而不是 FAILED」是同一格的两面：一枚要说门没咬，一枚要说读法太宽，
  **两面都量到了，但归属仍等裁**（修测试读法 / 修产品把 CAPTURED 也带上 error_type / 判越界门该不该咬）。
- `projection_status` 那两枚补一句分寸：键确实在产品里有出处（`app/main.py:19797`），本节的结论是"那一趟答复是 401 体、
  不是缺这个字段的产品分支"；要把 401 与"产品分支没带键"彻底分开，得把那两枚的 `client` 装上 bearer 再跑一次 ——
  那是改夹具的动作，等点单，没自取。
- 零产品字节、零测试改动：本节全部来自现读计数、引用行与 grep 出处。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.13（10-29 上午）" in text:
        print("ABORT section 14.13 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.13（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.13（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d section_head_line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
