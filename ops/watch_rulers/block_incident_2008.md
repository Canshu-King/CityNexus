### commander 事故处置 @2026-09-21 20:0x —— 预览库**第二次被"重置"清空**（又是那条公网路径）；我做了三件事：装上临时闸门、把用户那趟北京行程捞回来、把"0 命中"的分母补齐

**事故（我亲测，不靠车道转述）**
- 19:5x 我为 DoD#14 复跑 M1→M4（**只在副本上**：`live_snapshots/live_1955.db`，`sqlite3.backup` 一致快照，`integrity ok`）；
  跑完顺手直读**活库** `_qoder_cmdr_gate_20260921\backend\_live.db`：
  **journeys 从 6 条变 1 条**（只剩 seed 的 `22222222` DRAFT）、travelers=1，
  而 places 仍是 16（CNX-DEMO 8 + CN-BEIJING 8）⇒ 典型的 `demo/reset` 后重播种形状。
- 归属证据：`raw/uv_8693_tip.out` 第 **1597** 行 `130.94.30.196:0 - "POST /api/v1/demo/reset HTTP/1.1" 200 OK`
  —— **130.94.30.196 是 Cloudflare 边缘出口，也就是"从公网 URL 的浏览器里按的"**（与用户手机 18:19/18:36 同一条来源），
  前后序列是舞台浏览（`journeys/22222222`、`plans/ec0ee8b9`、`city-services/.../booking-slots`）。
  紧随其后是一片 **`/twin` 404 风暴**：`e833311d`、`bfc3b4ee`、`6c6a1459`、`8593c315` 这些**已被抹掉的 id 仍在被浏览器轮询**
  ⇒ 又一条独立缺陷：**行程被删之后界面不告诉用户，只是永远 404**（并入 ORD-0126 的"非 2xx 必须上屏 + 出口"）。
- 我 13:45 那张纸条**教过用户按这个按钮**（"演示前点一下就是干净现场"）。**这第二次清空里有我那句话的责任**，
  我在 19:0x 的纸条里已经撤回了这句话，现在把后果也记在账上。

**处置一：临时闸门（我的管道，不动产品码）**
`D:\moodle\_qoder_recovery_20260919\raw\preview_auth_proxy.py`（`:4782` 鉴权反代）里加了一条守卫：
`POST /api/v1/demo/reset` **不再转发**，就地回 **403** + `code=PREVIEW_GUARDED` + 中文原因（点名 ORD-0125）；
每次尝试都写一行 `GUARD … from <client>` 便于计数。改动范围只有这一个文件，备份 `preview_auth_proxy_bak_2005.py`，
`py_compile` 通过后重启代理（新 PID 49992，`:4782` 在听）。
**为什么重启不会把用户踢下线**：`SESSION_COOKIE = sha256("cnx-preview-session::" + secret)[:32]`，
而 secret 是从 `run/preview_auth.txt` 复用的 ⇒ 派生值不变，重启不掉登录。
**公网端到端复验（20:0x）**：`/` 200、`health` 200（`ai: enabled`）、`GET /journeys/22222222` 200、
**`POST /api/v1/demo/reset` → 403 `PREVIEW_GUARDED`**。
> **给所有车道**：这个 403 是**指挥官装的临时护栏**，不是产品缺陷，**不要报成 bug**；
> ORD-0125 落地并证明 `preserved_user_rows` 之后我第一个删掉它。若前端因此显示"失败"而没给人话解释，那才是 ORD-0126 的活。

**处置二：把用户那趟北京行程捞回来了**（`live_checks/restore_user_journeys.py`，先写前快照 `live_pre_restore_2007.db`）
- 规则：**只增不删不改**；只补"活库里不存在的 journey id"及其 traveler/preferences/constraints；
  **plan_versions / activities 故意不恢复**（它们引用的 mobility 快照 id 已不在，硬恢复=造一份拿不出证据的方案，违反 R5）；
- 结果：`journeys +1 / travelers +1`，活库 journeys **1 → 3**，`integrity ok`；
- 端到端验：`GET /journeys/94669bae…` → **200 (CN-BEIJING, DRAFT)**，
  对它 `POST plans/generate {candidate_count:3}` → **201 / 3 个候选**（公网、真服务、真库）。
  ⇒ 用户那趟**最早抱怨的行程现在能出方案了**，这条我签在"用户可见结果"上。
- 不可恢复的：`7dfdac2c`（他 18:27 自己排成功的那趟）、`bf8beccf 云和县`、`bfc3b4ee`、`90a4edcd` 等
  —— **只存在于已被覆盖的 WAL 里**，我没有任何一致的备份含它们（`live_pre_tip.db` 是 18:14 的一致快照，只到 `94669bae` 为止）。**不猜、不编。**

**处置三：把"0 命中"的分母补齐（按新立的记账纪律）**
我 19:5x 那句"`unresolved:%` 在活库 0 命中"当时只说了 54 张表，没给分母。补全：
`_qoder_cmdr_gate_20260921\backend\_live.db`（此刻，WAL 合并读）实测 **55 张表 / 717 列**，
其中**文本类列 616**；我上一轮扫的是各表**全部列**的 `CAST(col AS TEXT) LIKE 'unresolved:%'` ⇒ **0 命中**（当时报 54 是数错了 1 张，纠正）。
所以："token 被写成 durable 身份"这句仍然**没有本地证据**；被证实的是**API 回显**（`capability?query=云和县`）。
