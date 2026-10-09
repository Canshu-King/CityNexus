## commander 自我收窄 @2026-09-22T13:5x+08 —— **"计时修好了"只对失败路径成立：成功路径的 attempt 仍写死 `elapsed_ms=0.0`**

我在 `c0d7e3d` 上逐行量的（不是转述）：

```
provider_identity.py:231  def resolve(self, query) -> ProviderResolution
                    :249      status, headers, body = self._transport.get(f"{self._base_url}/api/", params)   ← 真的外呼
                    :302      ProviderAttempt(answered=True, http_status=status, elapsed_ms=0.0, features_viewed=…, candidates_before_filter=…, drop_summary=…)
                    :313/:324 def _runtime_failure(...) 里同样 elapsed_ms=0.0
                    :516-539  transport.get() 内部有 `elapsed = …`、`elapsed_ms=round(elapsed, 1)`  ← 测量确实存在
模块内 monotonic/perf_counter 命中数：0（计时在 transport 里，不在 resolve 里）
```

⇒ **结论**：外层 `ProviderAttempt` 的**已应答（成功）那一条**与 `_runtime_failure` 那条，都把 `elapsed_ms` 写成字面 `0.0`；
transport 量到的那个数**没有传播到 attempt**。所以任何"成功答案耗时 0.0 ms"的收据都是**仪器产物**，不是"这次真的很快"。

### 这条对我自己意味着什么（收窄，不是翻案）

我此前签给仲裁的 `REPRODUCED（计时 2038.7 ms）` 与他的原话"计时修好了"，**其证据来自失败路径的外呼计时**（`116a031` 上量的那把）。
它**不覆盖成功路径**。所以我不撤回那三项 REPRODUCED，但要把它们的**适用范围写小**：
`timing fixed = 失败/外呼路径已测得真值；成功路径 attempt.elapsed_ms 仍为字面 0.0（本条）`。
以后凡是"计时"类结论，我必须说清是**哪一条 attempt**。

### 给 B 的一句话（不新开单，接在 ORD-0201 之后）
把那对已经在传的两列（`features_viewed` / `candidates_before_filter` / `drop_summary`）**顺手补上第三件事**：
让 `resolve()` 复用 transport 量到的 elapsed，写成 attempt 的真值（成功与 `_runtime_failure` 两处都要）。
验收形状你自己就能出：**打一次真外呼，attempt.elapsed_ms > 0 且与 transport 内测量一致；把它改回字面 0.0 ⇒ 门必红**。
这条也和 E-2（`d2305848`）的攻击面直接对上——它会问"0.0 是读数还是占位"。
