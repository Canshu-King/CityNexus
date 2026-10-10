  note@494abfd7@2026-09-22T22:44+08: **仲裁已裁写入端校验（`5778314066`，一句话+四格边界照录）**：
  **"要校验，但分两层——所有写入先要求 `rule_code ∈ canonical vocabulary`；若 `kind=HARD`，还必须要求 `rule_code ∈ HARD_EXECUTABLE_SET`，否则在写入前 422 fail-closed、不落库；SOFT 不因『不属于 hard-executable』而被拒。"**
  ```text
  unknown code                            -> 422 UNKNOWN_RULE_CODE        -> 0 row persisted
  known code + kind=HARD + not executable -> 422 HARD_RULE_NOT_EXECUTABLE -> 0 row persisted（名字可调，但必须与 UNKNOWN 分开）
  known code + kind=SOFT                  -> 按该 code 的 soft/preference 契约处理，不要求 ∈ HARD_EXECUTABLE_SET
  known code + kind=HARD + hard-executable-> 允许落库，再由 feasibility 按真实证据语义求值
  ```
  ⇒ 本单第一步（STROLLER/LARGE_LUGGAGE 的 severity 参数）不受影响；写入端校验按这四格落，**与四个 SOFT 码的可行性层工作不要混成一笔**。
