# 旅行需求进服务端与多地点方案增量

HUMAN_CAN_USE = PARTIAL。旅行需求、多地点预览与 AI 建议均已接到当前真实试玩服务。核心产品提交 `698b5eb23fb17dc6ffe0027636b8840167bee3f7`；当前真实后端运行 `bfcb9aeeba0ca38d007b6e60f5bbc1bcd4376ed1`，保留原数据库与登录凭据。

对应 PR #23 最新指示：[6247650836](https://github.com/Canshu-King/CityNexus/pull/23#issuecomment-6247650836)。

后续产品修正 `a0269f9f86`：在行程页保存需求后，同一页面的 AI 草稿同步到服务端回执中的需求；用户另行编辑的 AI 草稿不会被覆盖。390/430 定向用例2/2通过，新增检查期间修正了段落与 textarea 文本重复导致的测试定位歧义。

## 新产品与接口

1. `POST /api/v1/journeys` 接受可选 `planning_intent: {goal, interests, energy}`，与 Journey、OWNER 成员在同一事务保存到既有 `JourneyIntent`；含此字段时要求签名旅客与创建人一致。日期、人数、预算继续来自 Journey / JourneyTripContext。
2. `GET /api/v1/journeys/{id}/planning-intent`：签名成员读取本人的需求、本人有效地点观察及多日预览输入，`private, no-store`。重新认证后的另一浏览器可恢复，不读取设备 localStorage 的私人偏好作为正式输入。
3. `PUT /api/v1/journeys/{id}/planning-intent`：行程 OWNER 在 DRAFT 阶段编辑需求，更新原记录。手机行程页可直接修改原文、兴趣与节奏。
4. `POST /api/v1/journeys/{id}/plans/generate` 新增 `bootstrap_candidate_ids`，选择 2–6 个不同的本人有效地点，通过原来源门禁与 materialization 后，进入既有 `generate_plans` / generic composition。保留原 Idempotency-Key 回执，不新造排程模型。营业/费用不足会返回具名拒绝，未生成 PlanVersion。
5. `planning_preference_items` 读取这份持久意图，供既有 generic / authoritative 规划器消费；美食、户外、文化等明确兴趣进入分类匹配，“睡到中午”通过既有 day-rhythm 解析改变 generic 日窗口。PlanVersion 记录意图 ID、版本时间与摘要哈希，不把私人原文放入共享方案。

目前支持的映射会在页面显示。开放式原文完整保留；“海边”等尚未编译成可执行条件的要求不被暗中丢弃，也不声称已满足。少走路是软偏好，不代表已有经过核实的步行距离上限。人数、日期、预算从服务端读取；日期不足、未安排天数仍显示实际缺项。

## 手机体验

行程页集中显示来自多次本人搜索的地点，可多选查看按天分组的**想去清单（未排定）**。地点保留来源链接、营业、费用；转场未知直接显示未知。只有至少两处均通过原正式门禁才允许生成正式方案；选择方案、确认启动仍是两个独立动作。

以下为真实 Chromium 渲染截图，数据为明确的 **TEST_FIXTURE**，不是本次 live 来源或手机硬件证据：

![390px 服务端需求与双地点预览，TEST_FIXTURE](assets/20261018-server-travel-brief/server-brief-multiplace-390-TEST_FIXTURE.png)

![430px 服务端需求与双地点预览，TEST_FIXTURE](assets/20261018-server-travel-brief/server-brief-multiplace-430-TEST_FIXTURE.png)

## 实测状态

| 项目 | 本次结果 |
| --- | --- |
| 新需求接口 / 原生 PlanVersion | 独立 SQLite 签名测试通过；两处来源夹具经原接口补事实、选中、原生生成及读取；同 key 重发为同计划，新 key 可生成下一方案。不是 live POI 的连续证据。 |
| 偏好实际消费 | 美食改变原分类排序得分；中午起床使生成活动不早于12:00；条件下雨未伪装成当前天气。 |
| 真实来源 → 新版 PlanVersion | 本轮未完成；旧南京/台北已成功读取的来源仍缺营业/费用。 |
| 真实 ACTIVE | 本轮未发生。 |
| 真实模型 / 工具 / AgentRun | 首次调用401；修正客户端Key来源、正常重启后，在现有签名DRAFT中通过页面提交一次有界请求，HTTP200，返回 `MODEL_TOOL_SUGGESTION` / `HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE`，类别 `museum/gallery`，中文建议已显示。正式AgentRun尚未创建。 |
| 真实需求持久化 | 手机行程页编辑原有签名DRAFT，PUT planning-intent 200，GET 200；刷新后从服务端恢复原文与轻松节奏，未查询地图或模型。 |
| 验证 | 后端相关61/61；手机 Chromium 全套26/26；随后截图定向2/2；Key读取与启动器10/10；TypeScript、Vite build通过。 |

本次首次全套 UI 发现旧测试的只读请求清单缺新 GET，更新断言及夹具后全套通过。初次后端组合测试复用了固定 OSM 身份导致跨用例城市冲突，改为每次独立的夹具身份后通过。两个问题都保留原来源门禁，没有放宽产品校验。Vite 仍有既存大分包提示。

真实AI请求前补充并核对页面披露：「点击后将文字发送给已连接的 AI 服务，可能产生模型费用。」原生Chrome-use点击无请求，在资源记录和后端日志确认后才同页DOM点击一次。首次401保存在[原始失败回执](20261018_BOUNDED_AI_HTTP_RECEIPT.json)，修正后的真实成功记录另存[WB2API实测回执](20261018_WB2API_REPAIRED_LIVE.json)，没有覆盖原失败。

这次真实错误页面的390×844截图也尝试了一次，Chrome调试器 `Page.captureScreenshot` 在8000ms超时，未生成图片，未重试。本报告的两张新手机图因此仍明确标为TEST_FIXTURE；真实错误有浏览器响应与后端脱敏日志回执，没有假造截图。

随后 `/v1/models` 认证检查定位了凭据来源差异：控制台配置文件的 `api_key` 值返回401，用户提供教程中的客户端Key返回200/53模型。`--wb2api-key-file` 显式读取该本地文件，仅传入隔离进程内存。修正后一次真实 Chat Completions 工具调用成功；本次接口未返回具体路由模型名，因此只记录请求模型 `auto:cheapest`。模型建议不是营业或票价来源。

## 当前试玩入口与保留数据的重启

当前试玩入口 <http://127.0.0.1:14332/revolution>，前端14332/后端18501均已正常更新。用户再次明确要求修复后，同一启动会话46437的正常Enter停止成功；由启动器正常收尾，再以原DB及相邻认证密钥重启，当前启动会话29994。先前审批阻塞已解除，不再列为当前障碍。

下次需要重启时，在原启动窗口按Enter停止，然后使用以下命令复用现有数据。`--resume-database` 校验已有DB与相邻认证密钥；命令仅启动服务，模型请求由页面提交触发。

```powershell
Set-Location 'D:\moodle\_codex_workers\citynexus-chromeuse-retest-ccdd7486-20261018'
$trialRun = 'C:\Users\仓鼠王\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\CityNexus\Revolution\5e2ddbf81da2-20261018-144858-6da344'
& '.\backend\.venv\Scripts\python.exe' '.\trial\try_revolution.py' --agent --wb2api-key-file 'C:\Users\仓鼠王\Desktop\教程_本机项目接入网关_2026-10-14.md' --runtime-dir $trialRun --resume-database '_revolution_hands_on_20261018_144901.db' --frontend-port 14332 --backend-port 18501
```

当前主要缺口是正式方案需要的真实地点营业与费用资料，旧南京/台北来源未提供这些字段；本轮没有新的真实PlanVersion、ACTIVE或持久AgentRun。可以继续使用地点探索、需求编辑、多地点预览和AI建议。成功结果已由Chrome页面文本、响应JSON与后端200共同确认；截图功能两次发生调试器超时，没有生成本次成功画面，未用夹具图替代。
