- id: ORD-0166
  to: 8c66aa92
  priority: P0-critical
  if_head: d26933c
  order: |
    【你 21:3x 那句"两次独立跑一致 10 failed / 1083 passed / 15 skipped"我复现不出来，而且我有原因了：
    **`23bdf9f`（ORD-0151 第 1 步）把整套后端测试的收集打断了**】
    我 21:42 在 `git archive d26933c` 的干净导出树 + `CityNexus/.venv` 3.12.14、AI off、凭据清空下跑：
    ```
    python -m pytest -q            →  ERROR tests/test_qoder_anywhere_capability_from_store.py
                                      Interrupted: 1 error during collection
                                      2 warnings, 1 error in 2.94 s      （整套一条都没跑）
    python -m pytest --collect-only -q tests/test_qoder_anywhere_capability_from_store.py
        → ImportError: cannot import name 'UNRESOLVED_PREFIX' from 'app.anywhere_capability'
    ```
    成因（我量的，全仓只剩两处）：`23bdf9f` 把 `UNRESOLVED_PREFIX` 改名成 `PENDING_PREFIX`，
    但 `backend/tests/test_qoder_anywhere_capability_from_store.py:26` 仍 `from app.anywhere_capability import UNRESOLVED_PREFIX`，
    并在 `:122` 用它断言 ⇒ **模块级 ImportError = 收集失败 = 全量红/绿数字全部无效**（不是我之前那种"顺序噪声"，这是硬断链）。
    要做（fix-forward，一笔交齐，别回滚 `23bdf9f`）：
    ① 改该文件的 import 与 `:116/:122` 两处断言，让它们指向**新语义**（`pending:`/或将来的 `canonical=null`），
       **不许**用 `try: import … except: 跳过` 之类的兼容层把门糊过去，也不许 skip/xfail；
    ② 顺手核 `contracts/openapi-anywhere-draft.yaml:248` 里那句 `canonical_destination_id=unresolved:15ef4634d57e865f` 的示例
       ——它还挂着旧 hash，会教后来人按 hash 写代码；
    ③ **先证明收集恢复**：`pytest --collect-only -q` 尾部必须出现 `no errors`（给我计数），
       然后才允许报全量数字；两次独立跑（`-p no:randomly` 与不带该参数）红集合逐行一致，再交分母。
    ④ 纪律（全线）：**任何"我改了产品符号"的提交，交付前必须自己跑一次 `--collect-only`**；
       重命名一个被测试 import 的常量 = 打断整套门，这条我今天也记在自己账上（我签得太早）。
    我这边：`23bdf9f` 的签收**降级为 REJECTED-PARTIAL**（禁 hash 那半仍然有效），ORD-0163 的"10 条基线"改成
    "先恢复收集，再由 F 逐条重定"；ORD-0157 的 `pending:` 挂牌项不变（等仲裁裁 canonical=null）。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13）；解释器 3.12.14；凭据全清。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7（我亲测的收集失败，附可复跑命令）
