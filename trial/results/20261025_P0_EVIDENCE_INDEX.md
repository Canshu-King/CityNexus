# P0 证据索引（由回执现读生成）

生成器：`trial/human_walk/_p0_evidence_index_r1.py`；每条都从回执解析，缺文件写 MISSING。

| 项目 | 判定 | 证据 | 关键读数 |
|---|---|---|---|
| P0-1 LAN 不穿透 / 票一次性 | 绿 | presenter-proxy-bypass-1.txt, pairing-replay-66.txt | BYPASS_SUSPECTED=False；首兑 200，重兑 401，无 key 403 |
| P0-2 时钟条接同一 run（屏上） | 绿 | clock-run-ui-1.txt | PLUS30_1_TEXT "模拟时间：12/03 09:30 · 执行第 1 步 · 模拟进行中"；AFTER_NEXT "模拟时间：12/03 12:18 · 执行第 6 步 · 模拟进行中"；ERRORS [] |
| P0-2 两日闭环（真栈） | 绿 | clock-two-day-classroom-62.txt, classroom-clock-run-62-live-classroom.png | FINAL "模拟时间：12/04 10:00 · 执行第 8 步 · 模拟行程已完成"；classroom-clock-run-62-live-classroom.png (58862 bytes) |
| P0-2 LAN 平板等价路径 | 绿 | clock-run-lan-63.txt, classroom-clock-run-63-c.png | AFTER_NEXT "模拟时间：12/03 15:00 · 执行第 6 步 · 模拟进行中"；classroom-clock-run-63-c.png (63854 bytes) |
| P0-2 场景→守护→缺任务 | 绿 | clock-scene-guardian-59.txt | AFTER_SCENE "等待守护决策 · 12-03 09:00"；AFTER_GUARDIAN "缺少守护任务 · 12-03 09:00" |
| P0-2 单一状态链（CAS + 旧门） | 绿 | single-state-chain-65.txt | stale=409（SIMULATION_SEQUENCE_STALE）；legacy=409（USE_SIMULATION_RUN_ADVANCE） |
| P0-3 城市池 / 1 城同 run | 黄（池子 BLOCKED，但不挡开演） | cities-classroom-62.txt | 池 status=BLOCKED，eligible=0/3，missing=VERIFIED_CITY_ADCODE_REQUIRED,AT_LEAST_3_CAPTURED_ROUTES_REQUIRED |
| 守护暂停（#47 P0） | 红（缺陷，已报） | guardian-unavailable-67.txt, 20261025_GUARDIAN_AI_SWITCH_REPORT.md | guardian http=200，after=PAUSED_FOR_ACCEPTANCE；progress proposal_id=None，proposals=0 |
| AI 开关不拦调用（#47 P0） | 红（缺陷，已报） | guardian-unavailable-67.txt | ai_enabled=False；guardian_runs=1；agent_runs 读数见报告 |
| 接受调整支线 | 绿 | proposal-accept-68.txt | accept http=200；plan e74a5edb-3f6d-40c3-910c-52e449619d40 → f84adc05-fb3b-4721-9c21-4db3bab96c28 |
| resume 门（夹具） | 绿 | resume-after-resolved-69.txt | resume http=200，after=RUNNING（事件先在副本里 RESOLVED，1 行） |
| 死锁屏提示 | 绿 | acceptance-note-70.txt | ACCEPTANCE_NOTE "守护没有交出可接受的提案（进度里看不到提案 id）；这条模拟解不开，请重启课堂演示（双击启动器）。" |
| 合入后一键核对 | 绿 | after-merge-check.txt | ENTRY_DOOR=PAIRING，SIM_CONSOLE=AVAILABLE:NOT_STARTED，all_green=True，tickets=3 |
| P0-4 平板亲手点 | PENDING | tablet-evidence-20261026-015439.txt | VERDICT=NO_EXTERNAL_CLIENT，外部请求=0，run={'id': 'e354b9da-80b7-4882-b3aa-ef295ffdd103', 'sequence': 0, 'status': 'RUNNING', 'virtual_now': '2026-12-03T09:00:00+08:00', 'updated_at': '2026-10-25T17:50:47.099158+00:00'} |
