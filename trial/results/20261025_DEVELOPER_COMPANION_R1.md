# Issue #51：DSH Developer Companion 首个可运行切片

状态：**可运行执行桥、真实 DSH 源码修改、独立回归和任务回滚已交付；完整 Issue #51 尚未关闭。**

基线为 rescue 的 `ead51d6cdf3fce6e463dcef6a847b106d0fc9ffb`，交付分支为 `codex/developer-autopilot-r1-20261025`。没有改 rescue、Qoder 手机页面、课堂启动器或 `backend/app/main.py`。

## 开发者现在能用什么

`tools/developer_companion` 是独立启动的本机 CLI，使用已有 DSH SDK profile。它能创建任务、查看持久化进度、查看 diff/工件、取消任务、设置超时、捕获允许路径的提交、独立验证和回滚。无需 Codex CLI，也不向旅行者工具目录加入 shell。

```powershell
python -m tools.developer_companion.demo_fix --source . --state-dir "$env:USERPROFILE/cn51/tasks" --provider workbuddy2api --model cn:deepseek-v4.1-flash
```

这条命令会实际调用本机 DSH 路由。需本机已有该路由的凭据；桥接器不会打印、复制或提交它。任务先复核当前源码，已经修复的基线不应重复造缺陷。其他故障使用 `--repro-file` 和明确的源码 allowlist，详见 [使用说明](../../tools/developer_companion/README.md)。

每任务建立私有浅层 Git 仓库和 checkout；不复制源工作树的未提交文件、未跟踪数据库或 `.env`。控制面只逐路径提交允许的修改。Windows Job Object 在退出、取消和超时时回收执行器及其子进程。状态使用原子文件持久化，owner-session 以带盐哈希绑定。

## 真正执行了哪一次模型任务

- Task：`c13fe1a3aab8438f92dbc2b9`。
- 执行器：本机 DSH `0.1.2-alpha.1` 的 SDK 通道。
- 请求路由：`workbuddy2api / cn:deepseek-v4.1-flash`。这里只记录请求 ID，不推测网关背后的实际模型。
- 实际工具调用 **121 次**，工具错误 **2 次**，脱敏事件 **245 条**，模型执行约 **668 秒**。
- 模型实际修改了 `backend/app/agent/guardian_stream.py`，新增 `backend/tests/test_guardian_card_after_accepted_replan.py`，并执行测试。
- DSH 的工作区沙箱不能写 checkout 之外的私有 Git 元数据，因此由可信控制面逐路径提交模型产物：`982840466809c10460e696645919240572ef501c`。
- 人工代码复核增量：`c1eaf5e7854a5c4ee60acb7b3ebe0e09c4341af8`、`f7edd9a5d8fcfcf7a8b9cb5a53632afc6d1ca3a4`。修正关闭时间字段、非对象 JSON 处理，并把旧影响/行动移入历史。最终修复不是全部由模型单独完成。

最初的故障描述误用了另一份页面代码的前提，声称当前 UI 已消费 `observation.resolution`。复核基线发现当前页面没有消费该字段。最终通过后端投影适配现有 UI，没有导入先前探索任务修改过的 Qoder 前端/lockfile，也不把该探索任务算成功。

## 产品变化与独立验证

重规划接受后，Event 已是 `RESOLVED`，旧接口仍把此前影响放在当前工作列表。现接口只在服务器持久化 `RESOLVED + resolved_at` 时投影关闭信息，把旧影响/行动放到 `history`。原始数据库记录保留；未关闭事件不采用用户 payload 中自报的关闭文字。

干净验证 checkout 的源码 SHA：`f7edd9a5d8fcfcf7a8b9cb5a53632afc6d1ca3a4`。

```text
py -3.13 -m pytest backend/tests/test_guardian_card_after_accepted_replan.py backend/tests/test_mobile_guardian_stream_routes.py -q -p no:cacheprovider
9 passed, 3 warnings; exit 0

py -3.13 -m unittest discover -s tools/developer_companion/tests -v
12 tests; OK; exit 0
```

独立测试由控制面选择命令，另建干净 checkout 和数据库执行；未使用模型自报结果代替验收。12 项执行桥测试覆盖实际 Git 快照/补丁重放、认证/重启、控制面提交新增文件、越界产物拒收、磁盘预检、取消/超时、日志脱敏，以及 Windows 父进程退出后子进程的回收。

## Chrome 实测

使用独立 SQLite、真实 FastAPI HTTP 和实际前端。地点/路线为确定性测试场景，没有调用旅行模型或现场地点来源。

同一案例：Journey `22222222-2222-4222-8222-222222222222`；Event `2fa280f7-5982-41e0-af5e-23f7137459f7`；Proposal `b3979d97-6f6d-4901-a976-68f323f9fa45`。

1. Chrome-use 从页面「我的旅程 → 课堂演示 → 行程守护」进入，原生选择器点击「接受这份调整」，服务器实际返回接受成功。
2. 基线读取：Proposal `ACCEPTED`、Event `RESOLVED`、open_events=0，但没有关闭信息，旧影响仍在当前列表。
3. Chrome-use 随后持续 EOF，改用 Chrome DevTools 独立浏览器上下文，经同一正常登录入口读取同一数据库，没有再次接受方案。
4. 保留数据库和签名密钥，仅重启隔离后端加载修复。390×844 触摸视口中，事件显示「已处理」，当前影响为 0；旧影响保留在 API `history`，关闭时间为原服务器时间。

修复前后原生截图已显示在 Codex 对话。Chrome DevTools 的文件导出被其 workspace-root 策略拒绝，未绕过，所以本 PR **没有声称包含已落盘的前后 PNG**。这也不是手机硬件验收。

页面另外仍显示空的「当前恢复第 3 轮 / 正在处理」以及一次调整读取失败提示。这是尚未解决的页面/恢复轮次问题，本切片没有修改 Qoder 热文件来掩盖它。

## 实际回滚

对模型任务分支执行了 `rollback_task`，依次 revert 3 个任务提交，得到 `22403c5b393d2121f96005089c87cc87958e04e4`。控制面确认回滚后源码树与 `ead51d6` 完全一致。原补丁、验证日志、模型工件仍在本机；交付分支保留已复核的修复。

## 尚未完成的 Issue #51 条件

当前身份仍是启动 CLI 的本机用户。私有 Git、工作区写沙箱和 Job Object 已实现，**独立 OS 执行用户及宿主机读取隔离尚未实现**。因此本切片可本机显式试用，不能当作可接收任意不可信源码的完整隔离服务。模型未自主完成真实 Chrome 操作，浏览器验收由包工头完成。截图文件导出也待接通。

可公开回执、测试原始输出的脱敏副本及源码哈希见 [机器回执](developer-companion-20261025/receipt.json)、[后端测试](developer-companion-20261025/guardian-tests.log)、[执行桥测试](developer-companion-20261025/bridge-tests.log)、[修复前 API](developer-companion-20261025/before-api-receipt.json)、[修复后 API](developer-companion-20261025/after-api-receipt.json)。本机 owner token、DSH 原始会话、私有数据库与凭据未提交。
