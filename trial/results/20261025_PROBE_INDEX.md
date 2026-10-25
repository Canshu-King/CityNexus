# 课堂探针索引（跑之前先看「改场景？」这一列）

位置：`trial/human_walk/`；证据：`trial/results/20261022_v3_human_chrome/`。
「改场景」= 会改演示库（接受提案、推进时钟、把行程走到完成、注入事件）。带 * 的跑完必须重跑启动器恢复开局。

## 会改场景（跑完恢复）

| 探针 | 用途 | 证据文件 |
| --- | --- | --- |
| `_classroom_rehearsal_r14.mjs` * | 手机主链彩排：进入→守护→接受→时钟→地图 | `classroom-rehearsal-14.txt` |
| `_classroom_desktop_flow_r39.mjs` * | 投影（1280×900）全流程，含点「接受」 | `classroom-desktop-flow-39.txt` |
| `_classroom_tablet_flow_r46.mjs` * | 平板横屏（1280×800）全流程 | `classroom-tablet-flow-46.txt` |
| `_classroom_mixed_order_r51.mjs` * | 先地图后守护的混序 + 接受 + 刷新 | `classroom-mixed-order-51.txt` |
| `_classroom_touch_order_r52.mjs` * | 同上，但用触摸仿真（tap） | `classroom-touch-order-52.txt` |
| `_classroom_finish_r47.mjs` * | 把行程点到终点并测重进入口 | `classroom-finish-47.txt` |
| `_classroom_done_plus_r49.mjs` * | 完成态下按「+1 小时」的守卫（现在应被禁用） | `classroom-done-plus-49.txt` |
| `_classroom_plus60_r50.mjs` * | 开局按「+1 小时」，读提示文案 | `classroom-plus60-50.txt` |
| `_classroom_presenter_event_card_r25.mjs` * | 隔离栈控制台注入场景事件 | `classroom-presenter-event-card-25.txt` |
| `_classroom_two_day_loop_r31.mjs` * | 隔离栈两日闭环（真模型，约四分多钟） | `classroom-two-day-loop-31.txt` |
| `_classroom_guardian_note_r35.mjs` * | 隔离栈按「交给守护助手」并读慢提示 | `classroom-guardian-note-35.txt` |

## 只读（不改演示库）

| 探针 | 用途 | 证据文件 |
| --- | --- | --- |
| `_classroom_lan_path_r27.mjs` | 局域网地址同屏：时钟、提案、蓝点 | `classroom-lan-path-27.txt` |
| `_classroom_desktop_card_r36.mjs` | 投影形状的守护卡与命中测试 | `classroom-desktop-card-36.txt` |
| `_classroom_phone_card_r37.mjs` | 手机形状逐时刻读卡片位置 | `classroom-phone-card-37.txt` |
| `_classroom_wrong_turn_r38.mjs` | 误点「开始探索」后的回头路 | `classroom-wrong-turn-38.txt` |
| `_classroom_slow_replans_r40.mjs` | 人为延迟 `/replans`，验加载行 | `classroom-slow-replans-40.txt` |
| `_classroom_refresh_r41.mjs` | 真课堂栈刷新两次仍回课堂 | `classroom-refresh-41.txt` |
| `_classroom_run_resume_r34.mjs` | 隔离栈运行中刷新（票门后端） | `classroom-run-resume-34.txt` |
| `_classroom_entry_state_r48.mjs` | 只读：同一时刻 session/journey/twin 的真实状态 | `classroom-entry-state-48.txt` |
| `_classroom_ai_state_r44.mjs` | 只读：AI 状态词与屏上标题 | `classroom-ai-state-44.txt` |

## 需要特殊前置

| 探针 | 前置 |
| --- | --- |
| `_classroom_entry_banner_r33.mjs` | 隔离栈 + 一张票；由 `_entry_banner_stack_r1.py` 起栈并传票 |
| `_classroom_presenter_ticket_r30.mjs` | 隔离栈 + 票；`after_merge_check_r1.py` 会自动读启动器留下的票 |
| `_classroom_backend_down_r42.mjs` | 先停 60391，跑完必须重跑启动器 |
| `_classroom_map_failure_r43.mjs` | 自带瓦片拦截，不改库，但要在课堂栈上跑 |
| `_classroom_preseed_vs_run_r1.py`（`.py`，在 human_walk） | 隔离栈与课堂库副本，不动课堂栈 |

## 恢复与自检

- 恢复开局：`D:\moodle\_cmdr_v3_port_1022\start_classroom_demo.bat`（或直接跑 `prepare_classroom_scene_r1.py`）。
- 恢复后自检：`classroom_demo_selfcheck_r1.py`，看到 `DEMO_READY=true`、`JOURNEY_STATUS=ACTIVE`、`PROPOSAL_WAITING` 有 id、`CLOCK` 为开场。
- 值守日志：`D:/moodle/_cmdr_v3_live_1022/classroom_watch.log`（每十五分钟一拍；演练时段出现 ALERT 属正常）。

## 2026-10-25 13:00 新增

| 探针 | 改场景？ | 说明 |
|---|---|---|
| `_presenter_proxy_bypass_r1.py` | 否（隔离栈） | LAN 经 Vite 代理请求 `/demo/session`，三档全 403 |
| `_simulation_run_api_probe_r1.py` | 否（复制库） | 读 cities/run 形状；start 被原生 journey 状态拒 |
| `_activate_and_run_r1.py` | 否（复制库） | 真实 `/start` → `PLACE_UNAVAILABLE` 读数 |
| `_advance_error_r1.py` | 否（复制库） | 单次 advance 的 409 body |
| `_clock_run_fixture_r1.py` | **是（复制库）** | 参数化夹具：`CLOCK_JOURNEY`、`CLOCK_MUTATE=0` 只读、`CLOCK_PROBE` 换探针 |
| `_walk_to_completion_r1.py` | **是（复制库）** | API 连走 20 步到 `SIMULATED_COMPLETED` |
| `_clock_run_ui_r58.mjs` | 否（夹具栈） | 390px：+30/+1h/到下一站/刷新 |
| `_clock_scene_guardian_r59.mjs` | 否（夹具栈） | 场景注入 → 守护 → 缺任务 |
| `_clock_completed_r60.mjs` | 否（只读副本） | 历史完成态入口：封存条、无时钟 |
| `_clock_two_day_r61.mjs` | 否（夹具栈） | 390px 连按到两日完成 |
