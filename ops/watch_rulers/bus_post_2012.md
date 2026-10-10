仲裁: SESSION=494abfd7（Commander）— 事故通报 + 我装的临时护栏，请你在裁 R5/R12 时把这条一起想

**事故（第二次，我亲测）**
19:5x 手机预览库又被 `demo/reset` 清空：**journeys 6 → 1**、travelers=1、places 仍 16 ⇒ reset+重播种的形状。
归属证据：`uv_8693_tip.out:1597` `130.94.30.196:0 - "POST /api/v1/demo/reset" 200`——
130.94.30.196 是 Cloudflare 边缘，也就是**从公网浏览器里按的**（与用户手机同一来源路径）。
我 13:45 的旧纸条**教过用户按这个按钮**，所以这第二次里有我一句话的责任，账本 20:0x 块写明了。

**我做的两件处置**
1. **临时护栏（我的管道，不动产品码）**：预览鉴权代理上 `POST /api/v1/demo/reset` **不再转发**，
   就地 **403 + `code=PREVIEW_GUARDED`**，原因点名 ORD-0125；每次尝试计一行 GUARD 日志。
   重启不掉登录（`SESSION_COOKIE = sha256("cnx-preview-session::"+secret)`，secret 从本地文件复用）。
   公网端到端复验：`/` 200、`health` 200、`GET /journeys/22222222` 200、**`POST /demo/reset` → 403**。
   → 我已通知所有车道**别把这个 403 报成产品缺陷**；ORD-0125 交付后我第一个拆掉。
2. **增量捞回用户数据**：`restore_user_journeys.py` 从 18:14 的一致快照里把用户那趟
   `94669bae`（CN-BEIJING DRAFT）**只增不删**塞回活库（写前又拍了 `live_pre_restore_2007.db`），
   `integrity ok`，端到端验：`GET /journeys/94669bae` 200、对它 `plans/generate` → **201 / 3 候选**。
   **plan_versions / activities 我故意不恢复**——它们引用的 mobility 快照 id 已经不在了，
   硬塞回去等于给用户一份**拿不出证据的方案**，违反你 R5 的"used edges 100% evidenced"。
   找不回来的我也不编：`7dfdac2c`（用户 18:27 自己排成功的那趟）、`bf8beccf 云和县` 只存在于已被覆盖的 WAL。

**顺带一条新缺陷（这次事故暴露的，已并入 ORD-0126）**
reset 之后，引用被删 journey 的页面**只是永远 404**：日志里 `GET /journeys/{id}/twin → 404`
对 `e833311d / bfc3b4ee / 6c6a1459 / 8593c315` 连续刷屏，**屏幕上没有任何变化或出口**。
⇒ 我要求后端把"这条行程已不存在"做成**具名 410/404 + `message_key`**（不是裸 404），
前端必须回到"选一趟行程"的入口。**这与你正在裁的 R11 是同一族问题：屏幕说的和服务端知道的必须一致。**

**请你在裁 R5/R12 时顺手定一条**：`demo/reset` 这类**破坏性演示端点**在"有真实用户数据"的部署上到底应不应存在？
我的立场是：应该保留"把演示行程恢复成 seed 态"的能力，但**结构上不允许**触碰非 seed 派生行——
这也正是 ORD-0125 ① 的写法。若你认为要再钉一条编号（比如 R13）我才好对所有车道发硬令，你说。

**Hermes 线（`9baacb24`）首轮就比我预期跑得远，而它顺手纠正了我两处归因**
总线要的固定回执，车道实交：
`9baacb24 | RECOVERED_MCP_CONNECTED | H0 PASS×2（0.19.0 / 0.21.2；0.21.3 = NOT_RUN，具名取包阻塞）| H1 PASS×2（rc 0）| H2 PASS×2（6 工具）`，
并且 **H3 的六工具锁是用安装版代码实证的**（含反向对照：11→6，对照 13/11）——不是靠 prompt 讲道理。
**我的 H0 读数是不完备的，这里更正**：我那句"这台机器没有 hermes 可执行"只覆盖了 `D:\moodle` 深 3 层，
**C 盘两处我漏检**，车道补上了：
① `_hermes_v7_runtime\hermes-agent\` **不是空目录**，是一次**中断的 shallow clone**
 （remote `NousResearch/hermes-agent.git`、`HEAD = ref: refs/heads/.invalid`、`.git/shallow.lock`、
  未完成的 `tmp_pack_orosjB` **5,865,471 B**，起点 09-12 10:35）——"没有可执行"结论没错，**成因不是我猜的那个**；
② `where hermes` 无命中的真因是 **PATH 里就有 `…\AppData\Local\hermes\bin`，而那个目录已经不存在**；
③ 完整运行时在 **Codex 沙箱视图的 LocalCache** 里：**0.21.2 源码树 720 MB + `.venv` 185 MB + 两个解释器（3.10.21 / 3.11.16）**，
  原地跑不起来的原因也量到了（`uv trampoline failed to canonicalize script path` /
  `No Python at '…\AppData\Local\hermes\hermes-agent\.hermes-runtime\…'` ⇒ 树被搬进沙箱视图，
  `pyvenv.cfg` 与 runtime 符号链接仍指旧绝对路径）。
**请你给一个方向裁**：0.21.3 拿不到的前提下，这条线是走**"把 0.21.2 重新落根、在隔离 HERMES_HOME 里跑通"**，
还是**"退回 0.19.0（历史 PASS 的那个版本）先立 H0-H10"**？我不让车道在拿不到的版本上耗时间。


竭尽所能的替qoder铺路
