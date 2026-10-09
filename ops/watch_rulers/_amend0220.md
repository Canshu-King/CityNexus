  note@494abfd7@2026-09-22T18:43+08: ④ 由仲裁 `5775017441` 冻结（照录）：同 currency ＋ 同 scope 时才做这个数学判定；量纲不同先统一语义，**不能拿两个不同量纲硬比**。
  ```text
  if total_budget and lodging_budget are explicit, same currency, same scope
  and lodging_budget > total_budget:
    - must not silently pass
    - Step 2 must expose a visible, specific conflict
    - pressing Next must focus/scroll that conflict into the viewport
    - Step 3 must not be reachable while the contradiction remains
    - once corrected, the conflict disappears immediately and Next becomes usable
  ```
  并且**只做一次黑盒 API 探针**（同样的矛盾 payload 直接走创建/更新入口），**不许越权改后端**：
  server 已具名拒绝 ⇒ 本单只收 UI/HUMAN 层；server 仍 2xx/落库 ⇒ 那才新开一张 backend truth 单（建议原因码 `BUDGET_COMPONENT_EXCEEDS_TOTAL`），归 backend writer，不塞给你。
