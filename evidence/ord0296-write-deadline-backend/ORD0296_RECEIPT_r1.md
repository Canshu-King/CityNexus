# ORD-0296 · ORD-0281 的后端半：服务端写预算

lane F `8ccd71d8` · 2026-09-25T09:23:55+08:00

候选 `6d041dcce11d`（父 = 我先读到的权威尖 `5c4608cede6c`，相等：True），ref `review/ord0296-write-deadline-f`。按 Q37 交付即冻结：
`frozen_tip = 6d041dcce11d05f28a55abadd40717f321b4db38`

## 1. 这半件到底做了什么（以及没做什么）

```text
默认值：write_busy_timeout_ms=30000（引擎实测 PRAGMA 30000，同一来源）、write_deadline_ms=45000
判级：WRITE_DEADLINE_CONFIG_OK；两场景 delta_ms=agent.commands:15000, plans.generate:15000
两态门的两侧：45000 ⇒ 放行；1 ⇒ 拦（DOOR_RAISED）；plans.generate:60000 ⇒ 只动那一格
具名答复：预算用完又撞锁 ⇒ 503 + SERVER_WRITE_DEADLINE_EXCEEDED + 服务器自己那句话（带两个数）
不改善：第一次撞锁（未超预算）仍是今天的 OperationalError→框架 500；前端 14 条写腿一条未动
```

## 2. 13 格（每格的句子由本格读数现场拼）

```text
C1_default_strictly_above_measured_busy_timeout DEFAULT_ABOVE_BUSY_TIMEOUT
C2_two_way_door_RED_when_deadline_not_above  DOOR_BLOCKS_UNREACHABLE_DEADLINE
C3_two_way_door_GREEN_strictly_above         DOOR_ALLOWS_VALID_CONFIGURATION
C4_lock_wait_has_exactly_one_source          SINGLE_SOURCE_ENFORCED
C5_per_scenario_configuration_is_real        SCENARIO_CONFIG_EFFECTIVE
C6_exhausted_budget_answers_by_name          NAMED_ANSWER_LOAD_BEARING
C7_inside_budget_keeps_todays_error          RENAME_IS_BUDGET_CONDITIONAL
C8_answer_is_registered_and_server_said_it   HANDLER_REGISTERED_AND_SELF_DESCRIBING
C9_normal_write_path_unchanged               HAPPY_PATH_UNTOUCHED
C10_budget_is_per_request                    BUDGET_SCOPED_TO_REQUEST
C11_mutation_campaign_summary                ALL_NINE_ARMS_HAVE_CARRIERS
C12_full_suite_ab                            NO_NEW_RED
C13_what_this_change_does_NOT_improve        SCOPE_NAMED

10 臂反突变：carriers_removed 合计 11、survivors 无、意外红 0、每轮字节级还原 True

## 3. 整套件 A/B

```text
分母 候选 {'10': 'failed', '1218': 'passed', '15': 'skipped', '1': 'xfailed'} vs 基线 {'10': 'failed', '1208': 'passed', '15': 'skipped', '1': 'xfailed'}
only_in_candidate=空  only_in_baseline=空
两棵恒红 10 条 = 已知基线红（按子集判，不当新账）
判级：NO_NEW_RED
```

## 4. 坐标

```text
6d041dcce11d05f28a55abadd40717f321b4db38  tree 5e9b6decb7f7396e79d0d0b607b81b3f9c493663  parent 5c4608cede6cb7bd5f3ac7e704bfee379ca47abc
backend/app/core/config.py: 5f3062f5025569c927594c4a302df5d8ec75e267
backend/app/db/session.py: 3ef99ffe398c048ff729ffd0016e61b8ce0ae678
backend/app/db/write_deadline.py: ba2393c3da30d6941587869be26cd303389b7f46
backend/app/main.py: 871aec006a3f6482f7a2700a8baeff8c25f7690f
backend/tests/test_qoder_ord0296_write_deadline.py: deacc9d7483f1b8fd8d24b6e23e586bf402d85f6
6d041dcce11d05f28a55abadd40717f321b4db38  refs/heads/review/ord0296-write-deadline-f
https git/ref == candidate: True

## 5. 纪律

`demo/reset` 0 次；`_live`/`_preview` 未碰；凭据 0 打印；权威线未直写；已发布路径 0 覆盖 0 删除；改动 5 件全部在 backend/**。
