import io
txt = r"""
- 值守拍 21:18 +08（42d1a6fa）**Codex 两条：额度墙已解、容量墙又落下；我把整条链路换成可回读的证据，并纠正一处我差点冒领的功劳**。
  - **新仪器（比像素可靠）**：Codex 桌面端把会话落在 `C:\Users\仓鼠王\.codex\thread_history_1.sqlite`（只读 `mode=ro` 打开，未写）。`thread_turns(status,started_at,completed_at,error_json)` + `thread_items(item_type,created_at_ms,item_json)` 就是"这条任务有没有在干活、为什么停"的原始凭据。两条目标任务：`Harness = 01a0c796-5741-75a0-8dc3-ed0af5f54b7c`、`Mission A = 01a0c887-274e-7753-bae5-74e2a34677f9`。
  - 18:12:5x 两条同时 `failed` = `usageLimitExceeded`「Your workspace is out of credits」⇒ 之前"0 落盘"是**额度**不是死机。20:50 之后额度恢复：旁证是同机另一条**心跳自动化**线程 `01a07739-d826`（每 2 分钟一条 `<heartbeat>` userMessage，指令"继续推进当前 Revolution Lab 任务，直到 23:00"）在 20:54:10→20:54:57 拿到 `completed`，20:56 又 `serverOverloaded`，20:58/21:00/21:02/21:04 继续跑——**说明容量是忽有忽无的，不是永久关闭**。
  - **我踩到的仪器坑（记下来，别再犯）**：`beat.py` 的 Codex 列量的是 worktree 文件 mtime，而心跳那一拍只做 `git status` 且 `decision=DONT_NOTIFY`，工作树 clean ⇒ **0 件改动 ≠ 停**。以后 Codex 侧先读 sqlite 再下结论。
  - 21:11:56 / 21:12:06 两条各自收到一条 userMessage「继续」并真的跑起来：Harness 21:16:13 报「继续推进 R26：同一 disposable DB 的 backend/MCP 进程重启幂等验证，先写可执行探针和 focused test」，Mission A 21:16:15 报「同一贡山重跑到真实 provider 超时…继续跑事实采集、规划和选择边界」。**但这两条「继续」不是我送进去的**：我在 21:11:5x 只按过一次回车，Mission A 那条 9 秒后的「继续」我这边没有任何动作可解释；且我两次 `SendInput` 返回 0/92（输入被抢），前台窗口在我操作期间自己变过两次。⇒ 结论是**用户本人当时就在 Codex 里操作**，我不冒领这次复活。
  - 21:16:39 两条**同一秒**再次 `failed` = `Selected model is at capacity`（`serverOverloaded`，GPT-6 Luna 最高）。这次不是额度，是上游模型容量，没有给重置时间。
  - 我自己那两次投递尝试的诚实读数：`wake_task.ps1` 在 21:09:10 读到 Harness 输入框里确实逐字存着我 148 字的草稿（`pre_equals_target=True`），但 VK-only 回车与 UIA Invoke 最右按钮都**没有送出**（`POST value_len=148` 不变，sqlite 也没有我的 userMessage）；最后有效的是**带 scancode 0x1C 的回车**（`kbd.ps1 -Scan 28`）。Mission A 的 92 字草稿在我 21:15:4x 回车后仍在框里，随后被应用重渲染清掉（现 `value_len=5` = 占位符 `\n随心输入`），**没有留下我的残留草稿**。
  - 21:18:07 停止 UI 操作：Harness 那拍 `edits=2`（输入框不止一个，无法确定哪个是 composer）、Mission A 那拍 `focused_is_edit=False`（焦点被别的操作拿走）。⇒ 用户正在用这个 app，我继续敲就是抢键盘。**改为用户可一键完成**：在停住的那条任务输入框里发「继续」即可复活；或告诉我"人离开了"，我按已验通配方（UIA 聚焦 → 打「继续」 → 带 0x1C 的回车 → 回读 sqlite 新 turn）代敲。
- Qoder 六辆 21:11 后仍全部在产出（`beat.py` 20:46:51 那拍：包工头 0.1m / F 0.2m / HJ-P3 0.2m / D 0.3m / B(c01d72a3) 0.5m / E 0.1m，E 已从"具名等待"回到产出）。20:00 门槛那拍见上一条。
"""
with io.open("PATROL_LOG.md","a",encoding="utf-8",newline="\n") as f: f.write(txt)
print("ok")
