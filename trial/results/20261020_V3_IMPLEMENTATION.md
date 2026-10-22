# V3 增量实测：三空间、持续对话与出发检查

新版可试用：探索、我的旅程、我的已接成三个主空间；完整的草案→正式出发→Guardian/多人决策链尚未闭环。

## 本次接单与提交

- 消费 Issue #42、PR #23 评论 6275500591 / 6275842406，保留原有代码与用户数据。
- 原始 41 文件素材：`5bfdee77d91d9adf3c1f3d7ccbf24a436448a3b4`。
- V3 主界面：`5755bf6d458a68d003b2e50e9edee1871120989c`。
- 签名出发读取与消费端：`5ce2d17428c5b5953e1b85f7c9b1ae41006f458a`。
- 最终产品/启动器：`d667bab16284a369e5a18ab9764246f82faa8450`。同一 PR #23 分支；未更改 Qoder 主线、用户数据库或部署。
- Qoder 来源：`a4692457a9b531e7bee355974d26c89905425512`、生成客户端来源 `b2bfeb3dec8d2d5ad5538cf2abe514cc47c0d1a4`。逐路径适配，没有整枝导入。

## 实际产品变化

1. 底部固定三个入口：探索 / 我的旅程 / 我的。地图、日程、对话是当前 Journey 的内部视图。切换空间、刷新可恢复，聊天输入不会因为换页重新创建 task。
2. 普通发送继续 DISCUSS / ask_traveler；用户另点研究按钮后才开始研究。沿用无限研究模式，没有恢复工作量下拉框。ACTIVE 阶段复用已有 Hermes 行程助手表单作为全局输入，保持真实 run / 审批逻辑。
3. A/B/C 是独立可切换的方案预览，选用仍通过签名草案 PUT；当前日程可按日期切换，照片、地图、日程沿用同一来源 candidate ID，点跨日期照片会打开对应日期。
4. 我的旅程直接呈现已有 Agent 草案和出发准备。有草案时不强迫重新进入手动选地点流程。补资料按钮继续同一任务；正式方案仍分别选用和确认启动。
5. 手机出发准备消费 `GET /journeys/{id}/departure` 与 `/members/me`。读取携带 bearer、no-store，展示服务器阶段和正式候选数。
6. 接入时保留本分支的成员能力校验：成员读取需 JOURNEY_READ，确认资格来自 JOURNEY_EXECUTION_UPDATE；未得到可行性判断不显示 READY，正式已选计划按 Journey 的实际指针读取。没有增加启动或审批绕行路径。
7. 初次页面先展示旅行愿望输入，日期和偏好折叠；目的地仍需填写。纯一句话自动创建的全新用户链未在本轮实测。

## 原始素材入库

在 Windows Downloads 找到完整原 ZIP，SHA256 `af084281d7b3f05cee235650c57e9708a759da21f2a7316ddbc62571681c4543`。导入前核对 SHA/CRC/十图 manifest，导入后 fetch 远端并逐字节比较所有 41 条目，PASS：10 PNG、10 HTML、17 JPG、目录/原规格/README/manifest。原图作为设计参考，未把其示意照片/金额/事故写成真实产品事实。

[原始设计目录](../../docs/revolution/v3-design/index.html)

## 真实服务与 Chrome-use 复核

- 入口：`http://127.0.0.1:14332/revolution`；后端 18501；原隔离 DB/auth 在最终产品代码上重启复用。
- 同一签名广州 Journey `f97d2dbf-921c-4942-b29b-7765ccb52e5d`，task `73a7efa7-0fb0-4e2a-bf8f-3001a3865600`。
- 读回仍是草案 revision 2、三备选、DISCUSS、三待选选项。通过 Chrome-use focus/Enter 实际切到我的旅程与 B 预览；未点击“选用”或发送模型消息。截图摆位使用同页 DOM 操作与 CDP viewport。
- 390×844、430×932、1366×980、1566×980：实际 document width 等于 viewport，三主导航、一个聊天框；照片保留来源作者/许可。截图为安装版 Chrome CSS 视口，不是手机硬件。
- 最终服务签名 `/departure` HTTP 200，`NO_PLAN_SELECTED`，正式候选 0；`/members/me` HTTP 200。出发读取为 `private, no-store`。
- 本次复核无业务 POST/PUT，无新模型/地点研究发送。已有公开来源资料与先前真实模型记录仍保留；不是本轮重新查到的营业/费用证据。

[真实 HTTP / 视口回执](20261020_V3_LIVE_RECEIPT.json)

| 关键帧 | 实际截图 |
| --- | --- |
| 390 探索与来源照片 | [图片](assets/20261020-v3-real-390-explore.png) |
| 390 同任务三方案 B 预览 | [图片](assets/20261020-v3-real-390-journey.png) |
| 430 持续讨论与待选择 | [图片](assets/20261020-v3-real-430-discussion.png) |
| 430 草案出发准备与真实阶段 | [图片](assets/20261020-v3-real-430-preparation.png) |
| 1366 地图/日程并排 | [图片](assets/20261020-v3-real-1366-explore.png) |
| 1566 地图/日程并排 | [图片](assets/20261020-v3-real-1566-explore.png) |

## 验证结果

- 后端出发读取：`pytest backend/tests/test_qoder_departure_read_r1.py`，14/14 PASS，独立内存 SQLite。
- 完整界面专项：48/48 PASS，安装版 Chrome headless、独立上下文、明确 API fixture；含三导航、跨页讨论、A/B/C、日期/地图关联、身份切换、正式方案 select/start 分离、ACTIVE Hermes 轨迹恢复。早期回归发现并修复了导航恢复、旅行需求预填、旧入口和新接口 fixture 适配问题。
- 启动器与 WB2API 读取：11/11 PASS，无外部请求。
- TypeScript `typecheck:all`、Vite build、Python compile、diff-check PASS。Vite 仍有原有大 chunk 提示。
- 客户端新增四个声明节点从 OpenAPI 生成结果提取，181 行增量；未覆盖其他历史契约差异。

## 剩余交付

1. **草案到正式计划的写入桥**：现有 GoalDraft source IDs 不是 canonical Place UUID，现有 generate 接口还会重新排程。已在 PR #35 评论 6276254335 请求 revision/幂等/逐 slot 缺项/同草案保留的窄桥。Qoder 最新 b2bfeb3dec 的交付仍只有两个读接口；本次已把读接口真实接到 UI。
2. **真实正式旅程与 Guardian/collective**：本次没有创建 ACTIVE，也没有新增 Guardian 事故或运行 2/3→3/3 共享变更。已有执行与成员确认组件继续保留；V3 新合同的完整串联仍未验收。
3. **真机亲手操作**：`USER_VERIFIED=PENDING`。首次一句话创建、真实双日局部修改→正式出发、Guardian 和全员确认仍需连续验收。

`V3_SPEC_PUBLISHED=YES | ORIGINAL_BINARY_41_FILES_IN_GITHUB=YES | V3_CODE_DELIVERED=INCREMENTAL | REAL_JOURNEY_CLOSURE=BLOCKED_AT_DRAFT_TO_FORMAL | USER_VERIFIED=PENDING`
