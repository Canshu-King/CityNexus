"""Record the arbiter's pending-identity ruling and unblock ORD-0157's ④.

Two edits, both proved:
  * append a short block at the end of ## DELIVERIES (before the ORDERS heading);
  * replace ORD-0157's status line (matched by its unique text) with the ruling reference.
Neither touches any other lane's block; the file stays LF.
"""

import io
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ORDERS_HEADING = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
OLD_STATUS = ("  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7"
              "（覆盖 0151 的\"两处\"前提；provider 调用 0 是我自己量的）")
NEW_STATUS = ("  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7"
              "（覆盖 0151 的\"两处\"前提；provider 调用 0 是我自己量的）"
              "｜**④ 已裁 @00:2x**：仲裁 `e4b7faa3`/`pending_destination_identity_policy.md` 采纳我的第三条路——"
              "`canonical_destination_id=null` + `pending_destination_label` 保原文 + `destination_pending_key` 只作相关/幂等键；"
              "两条反向突变已写进门（把 `pending:<raw>` 写回 canonical、或拿 pending key 当 catalog join key，都必须红）。挂起解除，按此实现。")

BLOCK = """### SESSION=494abfd7 · 仲裁两条新 policy 我拉回并落单（含我 ③ 挂起项的裁定）@本机钟 00:2x

`STATUS: ARBITER-DOCS-INGESTED | 树：权威 tip `d26933c` 未动 | 未碰 :4781/:4782/:8693 与 _live.db | 未触发 demo/reset | evidence `arbiter_docs/`（四份契约原文，REST contents 取回，未对 github.com 用 git 网络）|`

- `docs/pending_destination_identity_policy.md` @ **`e4b7faa3`**（+103）：**我 ③ 的挂起项被采纳**——
  身份列 `canonical_destination_id=null`、原文进 `pending_destination_label`、幂等/相关另用 `destination_pending_key`；
  并新增两条**反向突变**门（把 `pending:<raw>` 写回 canonical 必须红；拿 pending key 当 catalog join key 必须红）。
  ⇒ ORD-0157 ④ 解除挂起，C 可直接按此实现；`pending:` 现有落库行按 R10 就地回填、**不许删**。
- 同文件新增 **ORD-0167 小县城端到端闭环**验收：pre-state inventory → raw 保真 → provider 解析 → provider-backed catalog
  → 共享 planner（join 只许用真 canonical）→ 产品结果 → 重放幂等；三组（happy / NO_MATCH / RUNTIME_FAILURE），
  收据 11 项（sha、exact raw、normalized query、operation id、canonical before/after、两层 provenance、planner input identity、final state、retry）。
  冻结句：**Resolve a real place, preserve the user's raw request, and carry only real canonical identity into planning.**
- `docs/test_execution_truth_policy.md` @ **`65f1934f`**（+38）：**"没有 X"必须先打印现场 inventory**——这条正是我今晚第四次
  同族错（拿猜的字段名 `data-attribution-evidence-kind` 去问，实际叫 `data-evidence-kind`）换来的全线规矩；已并入 ORD-0166/0168 的报数口径。
- 状态：手机预览链仍健康（`:4782` 200、隧道 401 即需鉴权、`POST /api/v1/demo/reset` → **403 `PREVIEW_GUARDED`** 我带正确凭据实测）；
  后端未动，用户数据未动。
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    if "\r\n" in old:
        print("ABORT: CRLF")
        return 2
    print("before chars", len(old))
    if old.count(ORDERS_HEADING) != 1:
        print("ABORT: ORDERS heading not unique:", old.count(ORDERS_HEADING))
        return 2
    if old.count(OLD_STATUS) != 1:
        print("ABORT: ORD-0157 status matched", old.count(OLD_STATUS), "times")
        return 2
    if OLD_STATUS in BLOCK:
        print("ABORT: block contains the status text")
        return 2

    new = old.replace(OLD_STATUS, NEW_STATUS, 1)
    i = new.index(ORDERS_HEADING)
    body = BLOCK.strip("\n") + "\n"
    new = new[:i] + body + "\n" + new[i:]
    rb_check = new[:i] + new[i + len(body) + 1:]
    if rb_check != old.replace(OLD_STATUS, NEW_STATUS, 1):
        print("ABORT: delivery-block byte-identity proof failed")
        return 3

    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("readback equal:", rb == new, "| chars ->", len(rb), "| CRLF", "\r\n" in rb)
    print("new status occurrences:", rb.count("④ 已裁 @00:2x"))
    print("block occurrences:", rb.count(BLOCK.strip("\n")))
    print("ORDERS headings:", rb.count(ORDERS_HEADING))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
