# CityNexus Developer Companion · DSH

本机开发者通过命令创建源码修复任务。执行器使用现有 DeepSeek Harness 的 `sdk` profile；不需要 Codex CLI。它与旅行者 API、Journey Agent 工具目录和课堂页面分开启动。

## 一条命令执行

在本仓库根目录运行。`--provider` / `--model` 使用本机 DSH 已登记的路由；下面是本次机器实际配置的路由名，不包含密钥。

```powershell
python -m tools.developer_companion.demo_fix --source . --state-dir "$env:USERPROFILE/cn51/tasks" --provider workbuddy2api --model cn:deepseek-v4.1-flash
```

默认复现描述是“接受重规划后 Guardian 仍显示问题未解决”。使用 `--repro-file path/to/repro.txt` 提供其他明确故障。执行器首先验证当前基线；故障已经修复时保留源码，记录可复核的结果。

`demo_fix` 在状态目录创建本机 owner-session 文件，每个任务保存其带盐哈希。命令先打印 task ID / 原始 SHA / 独立 checkout，随后运行 DSH。默认任务超时 1200 秒；`--timeout` 可调整。任务没有研究轮数限制。

## 控制接口

Python 接口位于 `service.py`：

- `create_task(repro, target_checkout, owner_session)`
- `get_task_progress(task_id, owner_session)`
- `get_diff(task_id, owner_session)`
- `stop_task(task_id, owner_session)`
- `get_preview_or_test_artifacts(task_id, owner_session)`
- `finalize_task(task_id, owner_session)`
- `verify_task(task_id, owner_session, commands)`
- `rollback_task(task_id, owner_session)`

独立终端可以查询或停止正在运行的任务：

```powershell
$source = (Get-Location).Path
$taskState = Join-Path $env:USERPROFILE 'cn51/tasks'
$ownerFile = Join-Path $taskState '.owner-session'
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile progress TASK_ID
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile diff TASK_ID
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile stop TASK_ID
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile artifacts TASK_ID
```

也可设置本机环境变量 `CITYNEXUS_COMPANION_OWNER`。CLI 不打印 owner token。没有 owner token 时，控制命令拒绝读取或修改任务。

## 执行和结果

每个任务建立自己的浅层裸 Git 仓库和 worktree，从本机源 checkout 按确切 SHA 获取当前树；源 checkout 的未提交文件、数据库和 `.env` 不进入快照。创建前按 Git 树大小检查磁盘余量。Windows 推荐短状态目录（如 `$env:USERPROFILE/cn51/tasks`），避免 AppData 虚拟化导致过长路径。默认 allowlist 只有本次 Guardian 源文件和回归测试；其他工单通过 `create-task --allow-path repository/path` 逐项指定。独立仓库没有远端，默认禁止推送，凭据助手和 Git hooks 关闭。

任务状态、时间、心跳、执行器 PID、工具名、经过脱敏的命令/路径、工具错误码和结果分别写入原子 JSON 与追加事件文件。模型正文、推理和原始工具输出不进入公开进度。DSH 自己的持久会话保存在任务的私有 `runtime/` 目录；不要将它作为报告上传。

执行结束后，控制面逐路径检查 allowlist，把允许范围内的源码修改和新增文件提交到任务分支。模型无需获得私有 Git 元数据的写权限；也可调用 `finalize` 捕获开发者复核后的追加修改。

完成一轮模型执行只会得到 `COMPLETED_UNVERIFIED`、`NO_CHANGE` 或失败状态。它不会自动宣称测试通过。`diff.patch` 带 SHA-256；新文件尚未提交时，`untracked_paths` 和 `diff_includes_untracked=false` 明确记录补丁缺口。

独立验证由开发者选择命令，而不是由模型的报告决定。把参数数组写入本机 JSON 文件，例如：

```json
[["python", "-m", "pytest", "backend/tests/test_confirmed_defect.py", "-q"]]
```

```powershell
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile verify TASK_ID --commands-file checks.json
```

验证在捕获提交的另一份干净 worktree 执行，生成命令、退出码、耗时、日志和哈希。所有命令通过后得到 `VERIFIED_LOCAL`；证据类型是本机隔离命令执行。真实浏览器截图由对应浏览器检查产出并登记。

回滚只操作该任务的干净提交链：

```powershell
python -m tools.developer_companion --source $source --state-dir $taskState --owner-file $ownerFile rollback TASK_ID
```

回滚创建 `git revert` 提交并检查最终树与 base SHA 一致；原始补丁和执行回执保留。遇到额外修改或合并提交会停在可检查状态，不删除工作目录。

## 进程和运行边界

DSH 普通工具使用 `workspace-write`，额外权限请求没有自动批准。父执行器在 Windows Job Object / POSIX process group 中运行；正常退出、停止和超时都回收其子进程。Windows 已有实际父进程先退出、子进程仍运行、关闭 Job 后子进程退出的自动测试。

当前进程身份仍是启动命令的本机用户。Job Object 负责进程回收，不能代替独立 OS 用户或主机读取隔离；这部分 Issue #51 的严格执行身份要求尚未交付。源码中的分支限制和本地路径检查也不是面向恶意源码的完整沙箱。此边界在任务 `isolation` 字段中记录。

DSH 从自己的凭据 seam 解析已有路由；桥接器不读取或复制凭据文件。默认 `deepseek-official` 没有 Key 不代表其他已配置路由不可用。本次已通过 `workbuddy2api` 路由实际调用代码工具。ACP profile 在本机 alpha 版本的新会话阶段返回内部错误，因此本实现使用经过实测的 SDK 通道。

## 运行检查

```powershell
python -m unittest discover -s tools/developer_companion/tests -v
```

协议/生命周期测试中的执行器替身始终记录 `TEST_DOUBLE`；它们验证控制面，不构成真实 DSH 源码修复证明。真实任务的证据单独记录在本次 Issue #51 的结果报告中。
