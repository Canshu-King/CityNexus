# PR #48 外审修复结果

处理评论：6394994319。日期：2026-10-25。

## 本轮产品变化

1. 删除 demo/session 和模拟写入的 loopback 无凭证豁免。无 Origin 的请求经过真实 HTTP 代理再到 loopback 后端，仍为 403；X-Forwarded-For 不能授权。主持人用服务端 key 发行 120 秒单次配对票据，票据只存哈希，兑换后获得 900 秒、绑定本 Journey 和本隔离数据库的主持人 bearer。共享浏览器控制模拟时不需要持有讲台 key。并发兑换只一个成功，过期和重复票据拒绝，兑换按真实 peer 限流。
2. GET /journeys 与回收站列表现在只返回当前有效签名成员有 JOURNEY_READ 权限的行程。
3. SimulationRun 与原生 HTTP 复用活动的 Journey/Plan/current cursor/转换前置条件、出发路线证据检查。run 存在时旧活动和旧写钟入口明确拒绝，避免两套时间线。模拟不能伪造多人恢复会合的本人到场。错误 cursor 导致整笔命令回滚。
4. 城市身份新增独立 provider adcode 绑定，保留 CN-RV 内部码。来源为本人 GoalTask 的 resolved AMap region，必须匹配已落库的行政区 ProviderCall。区县不能计作另一座城市。公用地点/路线快照须主持人明确发布，并先满足 5 POI / 3 捕获路线及 POI 的来源 adcode 归属检查；只复制公开字段，不复制私人行程、成员、Plan 或 task 身份。抽样按去重后的 provider adcode 进行。

## 验证

- Issue47 相关回归：71/71 PASS，含真实 socket HTTP 反向代理（省略 Origin、后端 peer=loopback）、配对消费/竞争/限流、配对 bearer 控制本 run、跨 Journey 权限、城市来源与公用快照、原生状态前置条件和原有两日回归。
- 原有 R28 原生执行真相回归：4/4 PASS。唯一旧匿名 twin 读取调用改为当前 owner 签名读取，保留全部业务断言。
- Ruff F 检查通过，diff-check 通过。
- 原始输出：20261025_ISSUE47_REVIEW_JUNIT.xml、20261025_ISSUE47_NATIVE_R28_JUNIT.xml。

本轮总计 75 项通过。测试环境是独立 SQLite 和签名 fixture；代理是独立真实 HTTP 代理，不是 Qoder 正在运行的 Vite，也不是另一台物理 LAN 设备。真实来源/模型请求为 0。当前没有三城真实资料或同一 run 的真模型提案接受连续证据。

## Qoder 接线

- 配对接口与新城市接口已写入 SIMULATION_RUN_API_20261025.md。
- 首次无凭据 demoSession 不再自动发 owner token；应输入操作端生成的单次配对票据，随后只使用返回的 bearer。
- ClassroomClockStrip 选择新 run 后只调用该 run 的 advance/scenes/guardian/resume；旧活动写入将返回 USE_SIMULATION_RUN_ADVANCE。
- 当前 Codex checkout 未修改任何 frontend 或课堂启动器。真实 Vite/LAN、手机 Day2 和真实三城/模型验收由 Qoder 在同一产品运行链继续完成。
