仲裁: SESSION=494abfd7（Commander）— 一轮里三件事：ORD-0211 亲测接受（三条读数）、`g3` 的另一半真相（**干净库也绿过**，请改验收口径）、以及**我已经换包把用户点名的那句废话从手机上拿掉了**（真机链已指向新 bundle，P0 未动）。镜像 sha1 `46259ee47c3650da`，board 164；部署与 canary 收据在账本「commander 亲测＋部署 @15:4x」块。

## ① ORD-0211 ＝ ACCEPTED（只签机制层，不签"隔离已解决"，边界照你原文）

全部在 `git archive` 干净导出树上量，解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14），收据 `live_checks/ord0211/receipt.json`：

- **M1 对照（父提交 `0cd697b`，没有钉）**：植入带 canary 行的 `backend/citynexus.db`，跑一道写库门 ⇒ sha256[:16] `7c8c09284dffd5ba` → `73aa25d9bd451015`。**泄漏是真的**，所以 M2 不是空判定。
- **M2 交付（`0a4cb23`）**：同一植入文件跑完**逐字节不变**；收集期收据原文打印解析后的绝对路径 `ORD-0211 test database: resolved=C:\Users\…\Temp\cnx_pytest_rko0g_8g\suite.db | exists=False | declared_by=conftest temp dir`；目录里没有新 sidecar。
- **M3 拒绝分支（双向都试）**：声明 `CITYNEXUS_DATABASE_URL=sqlite:///<不存在的临时目录>/_live.db` ⇒ `exit=4` ＋ `RuntimeError: ORD-0211 boundary: the test suite must never open '_live.db' (preview/live target)`，且那个路径**跑完之后仍不存在** ⇒ 先拒绝，再谈打开。
- 我自纠一条仪器错：第一版脚本用了 `pytest -q`，`-q` 正好把打印收据的 header 段压掉 ⇒ 我把 `receipt_names_temp_dir` 误判成 false。那是量具红，不是 C 的交付红。

## ② 请求把这条门的验收从"一次绿"改成"一批绿"（附 14 个进程读数；与 HARNESS 15:18 独立收敛）

`gates::test_g3_five_concurrent_hydrations…`，每次新进程＋新 `cnx_pytest_*` 临时库（14 次 14 个不同目录）：**15:15 1 红｜15:16 手工 3 次 1 红 2 绿｜15:18–20 burst 8 红｜15:24 同树预热后 4 红 ⇒ 14 次：12 红 / 2 绿**。红时门自己报 **2–4 枚** operation_id。我试过的解释"**冷树/热树**"已**反证**：新树与跑过 12 次的树都全红，差异只有 `.pytest_cache/**` 与诱饵库。

HARNESS 15:18 在同一靶子上量到 `952ec40` 后 **6 轮×2 遍共享库 0 个、照样翻 3/6 且两向都有**，并给出更准的命名：两遍 `resolved=` 路径相同才允许叫 `DIRTY_DB_FALSE_*`，路径不同还翻就该具名 **`FLIP_WITHOUT_SHARED_STATE`（时序/并发）**。两条读数合起来 ⇒ 建议冻结：

```text
GATE_ACCEPTANCE_STREAK
any concurrency/timing-sensitive door (g3 family) => 10 independent processes, all green
each receipt row lists that run's exit code and its resolved absolute temp DB path
a single green never signs the door closed
DIRTY_DB_FALSE_* is only allowed when both passes resolved to the SAME db path;
otherwise the finding name is FLIP_WITHOUT_SHARED_STATE
```

这不新增 ORD，只改 ORD-0210（F）与 ORD-0213（C，我刚下）的验收措辞；两件互不顶替。**要你说一句"照此冻结"或给出更好的那条。**

## ③ ORD-0213 → C（一道门，尺寸锁死）

先机制判定再谈修法（五个并发为什么拿到 2–4 枚），复现命令逐字在账本 `- id: ORD-0213`（`if_head: 952ec40`），四条禁令：不许 sleep／加重试／降并发／改断言哄绿；反例走 `mutation_anchor_guard.py`。

## ④ 用户点名的那句废话：我已经换包，并自己当用户走了一遍（这条是"用户能感觉到"的那半）

- working tip 现在是 `56d20ec`（D 的 ORD-0212，15:22：`frontend/src/app/V8Experience.tsx` −45/+… ＋210 行三档 e2e ＋ `review/add-ord0212-mutant.py` 反例 ＋ 把 ORD-0064 旧门**改指向确认屏**而不是删覆盖——这三件正是我在单里钉的形状）。
- **我没有再等**：02:10 的旧包 `index-CnfHH2K_.js` → 新包 `index-BCF4ptyk.js`（`56d20ec` 构建）。备份 `dist_bak_1538`（10 文件）后整目录换，**未重启任何后端**：`53fe8e8..56d20ec` 差 29 个 backend 文件，所以 :8693 仍钉在 `53fe8e8`，`http://127.0.0.1:4782/` 与隧道 `/` 都 200 且回读到的 bundle 名＝新包。
- **真流程亲测在 canary 上做**（ 后端码＋ 副本库＋:4184 静态服务，绝不拿用户库做点击实验）：390×844 下**三次独立的"重进向导 → 点入口"循环**——每轮  命中自身（，335×44）、**14 条请求全 GET、POST＝0**、每轮第一条业务请求都是 、落点 ；三轮合计 **POST=0**，canary 库 journeys/travelers/plan_versions 跑前跑后 **3/3/19** ⇒ **ORD-0209 这一格我签 （canary 运行时，不是用户库）**；主页屏上「Demo之旅 · 1 位旅行者 · 1 天」，**没有**  那一行。
- 仍未做的两件我说清楚：① **tight 那一档的保留我只做到代码级**（D 的三档门在它自己的 e2e 里，我没在运行时构造出 tight 场景）；② 用户手机上若仍看到旧样子＝**旧 service worker 缓存**，重开一次即可——这一条我按"未验证到真机"处理，不签 REPRODURED(手机)。
- **换包之后真机链仍在**：**鉴权**走隧道  → **200**（这是能穿过上游的那条——401 只证明护栏，我在 13:17 被这条骗过一次）， → **200 且 index.html 里 bundle＝**；用户  只读复查仍 **3/3/19**。canary 两进程验完已停（清理计划兑现），副本库与  留在  作证据。

- **形状提醒仍然有效**（HJ-P1 15:10 的陷阱，我实时也证实按钮会随跳页消失）：谁写这道门，都要用**三次独立"重进向导→点入口"循环**，同一页上点三次会天然通过——我 15:5x 那三遍就是照这个形状做的，D/HARNESS 的读数请与之并排而不是互替。
## ⑤ 巡逻点名（用户令 §6；15:25 `list_chat_sessions` ＋ 15:31 叫醒）

running＝`e345b9d6` D（ORD-0212 已交 `56d20ec`，下一步 ORD-0209 的三循环形状）｜`d2305848` 红队（四件新靶）
ready＝`8c66aa92` C（ORD-0213 刚下）｜`c01d72a3` B（g14a/g14c/city_failure＋未闭 g10）｜`1a986a24` HJ-P1（journeys 已 9 条，并新报一条 HUMAN_MISLEADING：**"还需要填写：总预算"会带进第 3 步并在创建成功时仍挂在屏上，2/2**）｜`4e974ae5` HJ-P4｜`aad2d1f2` HJ-P3｜`d291c9dc` HARNESS（转达块第一步已给）
**cold → 15:31 已逐条叫醒**（各一行窄定位，不含任务正文）：`8ccd71d8` F（ORD-0210）｜`9baacb24` HERMES｜`5ea3bedc` LAB｜`d4b04a0f` HJ-P2。
LAB 已经回了：换底到 `952ec40` 完成、Mission A 在新底**不成立**（"命名"那半被主线 `_provider_resolution` 取代，终态迁移读数作废归 `1cce4bf`），新底上具名阻塞＝**精确名相等门**而非 provider ⇒ 我 14:5x 那三行催办**结案**。（它把用户 15:00 的抱怨也记进了账本，见 DELIVERIES。）

## ⑥ 现场与 P0

`P7=false`、reference tip `c0d7e3d`、working tip `56d20ec`；那把 key 仍未轮换（只有你能做；F 的字面量常驻门在位）；15:35 巡逻：匿名 `/api/v1/demo/scene` **401**、鉴权 `POST /api/v1/demo/reset` **403 PREVIEW_GUARDED**、用户库 journeys 3 / plan_versions 19 / travelers 3（与我 15:45 换包后复查同数）、places `CN-BEIJING 8 / CNX-DEMO 8`；本轮我 **0 次**触碰 `_live.db`（只读计数除外）、**0 次** `demo/reset`、**0 次** provider 出网，所有点击实验都在自己的副本库 canary 上。

竭尽所能的替qoder铺路
