## commander 处置 @2026-09-23T02:37+08 —— **C `8c66aa92` 的 ORD-0224 回合以 `failed` + 空收尾结束**（40+ 工具调用却没交报告）；不干等，已按"读流水→从盘上续跑"推动它

### ① 现场（我自己读到的，不是它报的）

```text
C 的 ORD-0224 回合（activeTurnId ff1d4932…）最终 status = failed，最终文本 = ""（空）
该回合内的工具：多处 Bash/Edit/Write 成功，少数 Bash failed —— 即"活干了一半，报告没出来"
主线 git status（我 02:26 读过）里属于它的在制品：
   M backend/app/anywhere_capability.py
   M backend/app/catalog_hydration_operations.py
   ?? backend/tests/test_qoder_ord213_ask_store_before_world.py
```
⇒ 这正是我们记过的"会话罢工"形状：**failed 空回合**；代价是**它以为写完的东西我一无所知**，而主线还带着它未提交的在制品（会让部署与别人合流都判不清边界）。

### ② 我的处置（三件，一次性发过去；它是 `ready`，不排队）

1. **先盘后做**：要它把 `git status --porcelain -- backend/ contracts/` 与 `git diff --stat` 列出来，并**逐项说明每个改动属于 ORD-0224 的哪一步**（1 弱修 / 2 新 g3 / 3 tail-A / 4 小包 / 5 为何收敛 / 6 反向突变），且**把"已落盘 / 只在草稿里 / 压根没开始"三种分开写**。
2. **从盘上继续**，不要从头重跑六步；交付形状仍要 `run shape + 精确 nodeid + 命令 + 每步判定`，突变报三字段，**没做完的明写**。
3. **收尾纪律**：若今晚做不完，请在**干净的小批次上提交**并说明停在哪，不留一大片未声明的工作树。
**另附 ORD-0234（一行）**：`backend/app/capabilities.py` 留 `else None`、删它的 `else "STRONG"`（B 实测两栏各 21 passed ⇒ 删不破门），排六步之后、或顺手做并在报告里单独列一行。

### ③ 同时记一条待观察（还没动手）

`4e974ae5`（HJ-P4）从约 02:12 起 `runtimeState=running` 但 **revision 冻在 122**（约 25 分钟没动），activeTurnId `86ceadfe…` 自 02:02 起未变。**revision 不涨不等于死了**——一次很长的工具调用（装依赖 / 长测试 / 起整条 lane 栈）期间它也不涨。⇒ **本轮不杀它**，下一轮再看：若再冻 10–15 分钟且状态无变化，则按"授权我自主重启卡住的本地 agent"处置。**判据（写下来免得以后靠感觉）**：*连续两次巡检之间 revision 不变 **且** 其名下进程/产物 mtime 也无变化 ⇒ 视为卡住；只有 revision 不变而产物在动，才是"在干活"。*

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
