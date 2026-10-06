  note@494abfd7@2026-09-22T19:54+08: 仲裁第三次源审（`5775917170` §2/§3）逐项判定：
  ```text
  protected-db guard        = ACCEPTED        （path_is_forbidden 已下沉共享模块、走 normcase+casefold，钉了 _LIVE.DB/_Preview.DB 反例）
  reverse closure semantics = ACCEPTED-MECHANISM（KILLED/STREAK_BROKEN 才算 closure-grade；SURVIVED/NOT_MEASURED 停在 STREAK_GREEN）
                              ⚠ 但 external CLOSED 仍需 auditor-readable mutation receipt：`CNX_ORD0210_REVERSE_MUTATION=KILLED` 只是字符串声明，不能凭它签 CLOSED
  freshness shared predicate= RED             （`_instrument_problems()` 仍在 test 文件里；`streak_verdict()/receipt_problems()` 共享模块本身无机械检查 ⇒ 别的引用方仍可绕过）
  run-shape exactness       = RED（新增洞）   （`verify_run_shape()` 只查声明 target 是否出现在 argv，未精确抽出 selector 集合并要求相等；
                                               它举了你们测试里的反例：cross=[... TARGET_NODEID, ..., 'tests/seed.py::test_seed'] ⇒ run_shape_verified=True）
  ```
  **修法（它给的）**：解析 argv 中 pytest positional selectors —— single-node 必须**恰好一条且等于 TARGET_NODEID**；
  preceded 形制 selector 序列与声明 nodeids **逐项同序相等**；whole-file 恰好一个 file selector。修完发可读 patch，它直接二审。
