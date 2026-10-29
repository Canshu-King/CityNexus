# Issue 49 课堂增量 · 2026-10-26

基线为 rescue `0acc73ca25`；独立 Codex 分支提交到 PR #54，未直接写入 rescue。

## 产品变化

- `2242c07f9d`：WP01 测试调用方使用本人签名，保留原业务断言。
- `9913208062`：Guardian 子任务的 user turn 与 resolved intent 同时携带服务器确定的 Journey、父子 mission、当前事件绑定。未预编工具顺序或答案。
- `5f7abc128e`：作息解析识别“11点才出门/出发”和“玩到很迟/很晚”。按某日局部应用此约束的 GoalTask 接线另在施工，不能把解析通过当作手机排程已完成。
- 新增 `guardian_outcome` 只读投影，区分本事件提案就绪、Agent 未解成、实际外部失败、未配置与未知；保留旧 status。
- 新增 `activity_coverage`，按 Journey 本地日期区分规范地点数、本 run 完成、继承完成、占位和课堂目标缺额。空白旅行日也列出。每日至少两站是课堂显示目标，不增加普通旅行的出发或接受限制；该计数不认证 LIVE 来源。

新增字段位于原签名 `GET /api/v1/journeys/{jid}/simulation/runs/{rid}/progress`。数据只从该 Journey 的当前活动计划、当前 run 与场景关联记录读取。Qoder 前端尚未消费这两个字段，未声称屏上提示已同步修改。

## 根会话实际检查

均为独立 SQLite，未使用个人/原课堂库。

| 范围 | 结果 |
| --- | --- |
| WP01 调用方 | 29/29，exit 0 |
| Guardian 上下文 + 原 Presenter 集成 | 18/18，exit 0 |
| 原作息、草稿局部替换 + 晚起用例 | 16/16，exit 0 |
| Guardian 结果分类 + 原 Presenter 集成 | 23/23，exit 0 |
| 活动覆盖纯函数、签名 API + 结果分类 | 13/13，exit 0 |

上述范围有重叠，不累加为独立通过数量。现场模型结果与这些替身检查分开。

## 当前事件的真实模型增量

隔离副本同 run `5625ed72-9aff-4c87-8bb3-68d9291775e1`，当前闭馆 Event `7cf6f587-cec6-4c30-823a-b7cab6891c6f`。

- 通过 Chrome-use 页面开演、注入闭馆、交给守护助手；本轮按键 Enter 操作，不写成实体手机触控。
- Hermes `cn:hy3` AgentRun `a035a763-2c05-4667-83b9-2262c28e51e8` 实际完成 `inspect_journey`、`inspect_twin`，均 `ALLOW_AUTO`。此前同类失败 run 没有工具步骤且答缺 Journey ID。
- 后续模型请求超时，记录 `FAILED_EXTERNAL / MODEL_TIMEOUT`，该次尝试耗时 237231ms；没有新 proposal，不能报接受/恢复通过。
- Qoder 前端工作树在联调期间有并行改动；不将这次 UI 状态绑定为某个干净前端提交的全量验收。
- auto:cheapest 恢复服务已配置，当前浏览器重新配对/连接仍待恢复；没有声称已完成第二次模型调用。

## 四站缺口

准备计划原本是 Day1 天安门（run 前已完成）+故宫、Day2 天坛。规则删除提案移除了故宫，没有补位。研究中占位没有规范地点或路线，不能补足第四站；旧完成状态不能充当本 run 的新完成记录。

GitHub Actions 已接到 PR #54。此前 `6747478448` 的 CI 成功只覆盖当时已提交范围；本次投影/覆盖提交仍以其自身新 CI 读数为准。真实四站、当前新 proposal→接受→resume、从空白正式出发和实体设备仍待完成，Issue #49 保持开放。
