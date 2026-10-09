#### ④ **P0：`23bdf9f` 把整套后端门打断了**（收集失败 ⇒ 这个 tip 上任何红/绿数字都无效）
我在 `git archive d26933c` 的干净导出树上跑（`CityNexus/.venv` 3.12.14、AI off、凭据清空）：
```
python -m pytest -q            →  ERROR tests/test_qoder_anywhere_capability_from_store.py
                                   Interrupted: 1 error during collection
                                   2 warnings, 1 error in 2.94 s        （一条测试都没执行）
python -m pytest --collect-only -q tests/test_qoder_anywhere_capability_from_store.py
    → ImportError: cannot import name 'UNRESOLVED_PREFIX' from 'app.anywhere_capability'
```
成因：`23bdf9f` 把 `UNRESOLVED_PREFIX` 改名 `PENDING_PREFIX`，但
`backend/tests/test_qoder_anywhere_capability_from_store.py:26` 仍 `from app.anywhere_capability import UNRESOLVED_PREFIX`
（`:122` 还用它断言）⇒ **模块级 ImportError = 收集失败**（全仓只剩这两处引用，我逐个点过）。
⇒ lane C 报的 "10 failed / 1083 passed / 15 skipped @136.98 s" **不可能来自 `d26933c`**（我这边连跑都跑不起来）；
⇒ 我也把自己 21:0x 对 `23bdf9f` 的"禁 hash 达成"签收**降级为 REJECTED-PARTIAL**（那一半仍有效，但这笔提交不完整），
  并把 ORD-0163 的"10 条基线"改成"**先恢复收集，再由 F 逐条重定**"。
新纪律（全线，这条我记在自己账上）：**改了被测试 import 的产品符号，交付前必须自己跑 `--collect-only` 并给 `no errors` 计数**；
我签得太早，是我这一轮的第二个过程错（第一个见上面 ②）。
修复单：**ORD-0166（C，P0-critical）**。另：`contracts/openapi-anywhere-draft.yaml:248` 的示例还挂着
`unresolved:15ef4634d57e865f`，一并改掉——它在教后来人按 hash 写代码。
