# ORD-0245（只读）· 这两天落的前端修复里，哪几条**完全不依赖 `53fe8e8` 之后的后端契约**

问题（commander 转仲裁 `FRONTEND_COMPAT_BACKPORT` 新路径）：**若新 bundle 因契约边界 HOLD，纯前端修复能不能从手机兼容基线 `53fe8e8` 做窄候选？**
要回答的是每条修复的四件事：**commit / 触达的 endpoint / 是否依赖新必填字段 / 能否从基线干净 cherry-pick**。

## 0 · 纪律头（A-5 那七项，每一项都可复推）

```text
repo        D:/moodle/_qoder_integration_20260919   head a1cc0c1d19148c97e7a7c9a27c292f07600a2835
基线        53fe8e869…（53fe8e8，fix(backend): R5 mobility refusal，09-21 18:02）—— 同一 object DB 内可达，已核
dirty       工作树 364 个文件脏（前端 4 个：V8Experience.tsx / PlanComparison.tsx / PlanWithAiSheet.tsx / _qoderTextScan.ts）
            ⇒ **未提交的改动不是候选**，本清单只算已提交的
run shape   ① git-only：log / show --name-only / show --unified=0 / merge-tree --write-tree（预测器，只写 loose object，
              不动 ref、branch、worktree）
            ② 每棵树一个独立进程、各自一次性 seeded 库、进程内 TestClient；resolver=off＋port-9 绊线
collected   38 个 commit 碰过 frontend/；其中 25 个是 fix/feat/refactor(frontend) 候选；12 个 endpoint × 2 棵树
environment CITYNEXUS_ENV=test / AI_ENABLED=false / DEMO_MODE=false / GUARDIAN_AUTORUN=false / 两把 key 置空 /
            ANYWHERE_RESOLVER=off / PHOTON_BASE_URL=http://127.0.0.1:9
cross shape 换形制（git 预测 ↔ 进程内 HTTP）的差不做差分；要做就同形制重测，否则写 NOT_COMPARABLE_AS_REGRESSION_DELTA
```
收据：`ord0245_frontend_candidates.json`（清单）、`ord0245_openapi_phone_baseline.json`＋`ord0245_openapi_live_line.json`＋`ord0245_openapi_diff.json`（请求/响应 schema 面）、`ord0245_payload_phone_baseline.json`＋`ord0245_payload_live_line.json`
（每棵树一个进程的真实 payload 键集）、`ord0245_payload_diff.json`（键集差）、`ord0245_backport_classification.json`（逐条判定＋按角色的证据行）。

## 1 · 先推翻两个省事的答案：**路由表兼容，连 OpenAPI 都逐字节相同——而真机 payload 差 10 个键**

两棵树的 `backend/app/main.py` 路由表**逐条相同**（各 132 条注册，**只在 head 存在的 endpoint：0；只在基线存在的：0**）。
再问一层（这一层我原本打算写"没测"，结果当场量出来了）：把两棵树的 OpenAPI 各导一份、逐操作比 request/response schema，
**14 个操作的 schema 逐字节相同：新增必填请求字段 `0`，schema 层面新增响应字段 `0`**
（`ord0245_openapi_diff.json`；两棵树各自一个进程，`phone_baseline` head `53fe8e8`、`live_line` head `2ab69f2`——活线在这一小时内又前进了，
所以我给每份收据单独记 head）。

**可是同一条 `GET /destinations/capability`，实打实回给前端的键，基线 16 个、活线 26 个。**
⇒ **这条接口返回的是裸 dict，OpenAPI 里根本没登记那 10 个键** ⇒ **只看 schema 比对会把 A1/A2 两条判成"可安全回带"，
   而它们放到基线上读到的是 `undefined`。** 这条边界**只能靠打真接口量 payload 看见**，不能靠 OpenAPI 或路由表——
   这一句是本次交付里最该被记住的一条，因为它决定了以后所有窄候选的验收形状。

⇒ "新契约"既不在**有没有这条路由**、也不在**schema 写了什么**，只在**这条路由实际回给你什么键**。
  所以对"依赖新契约"的唯一正确问法是**字段级差分（实测 payload）**。

把 12 个前端真会打的接口在两棵树上各打一遍（同一个 seeded 库、各自进程），只有 **2 个接口**的键集不一样：

| 接口 | 基线键数 | head 键数 | 只在 head 出现的字段（去掉泛用名后） |
| --- | --- | --- | --- |
| `GET /api/v1/destinations/capability` | 16 | 26 | `retryable`、`destination_state`、`destination_pending_key`、`pending_destination_label`、`pending_label_fidelity`、`resolver_query_normalized`、`candidates`、`malformed_candidates`、`hard_gaps`、`places[]`、`coverage_detail.*{hard_eligible,source_classes}`、`source_identity`、`osm_type` |
| `POST /api/v1/catalog-hydrations` | — | — | 同名那一族（`retryable`、`destination_state`、`pending_destination_label`、`resolver_query_normalized`、`destination_pending_key`） |
| 其余 10 个（`demo/scene`、`health`、`places`、`journeys/{id}`、`…/plans`、`…/experience`、`…/agent-feed`、`…/constraints`、`travelers/{id}/capabilities`、`…/plans/generate`） | 相同 | 相同 | **0** |

**泛用名是我主动剔掉的**：`id / name / category / latitude / longitude / source_provider / coverage_detail` 这些名字
在基线**别的接口里出现过**，拿它们判依赖会误伤——第一版就因此把 3 条无关修复错标成"依赖新契约"（`5` 而不是 `2`），
剔掉泛用名并要求**该 commit 真的打了那条接口**之后回到 `2`。被剔的名单写进收据
`excluded_because_generic_on_the_baseline`，不是我口头说"这个不算"。

## 2 · 结论：**25 条候选里只有 2 条依赖新契约**

| # | commit | 判定 | 证据（**shipped 源码里的读法**，不是 e2e 桩） |
| --- | --- | --- | --- |
| A1 | `15a114e` 09-22 02:07 `feat(frontend)` ORD-0193 补水流程 | **依赖新契约** | `frontend/src/features/discovery/DestinationPreparationPanel.tsx`：`const candidates = capability?.candidates ?? []`、读 `capability?.retryable`、`capability.pending_destination_label`（打了 `destinations/capability` 与 `catalog-hydrations` 两条） |
| A2 | `d0dfc90` 09-22 13:17 `feat(frontend)` ORD-0203 第四格 | **依赖新契约** | 同一文件：`const retryable = Boolean(capability?.retryable)`（`retryable` 在基线 payload 里根本不存在） |

⇒ 这两条**不能**进窄候选：放到基线上，界面读到的就是 `undefined`。
⇒ 另外记一条**独立的行为差分**（不是我从代码猜的）：基线那棵树在 `POST /catalog-hydrations` 之后，
  自己的后台 worker **3/3 个独立进程**抛 `TransitionRefused: ABANDON_REQUESTED -> UNAVAILABLE`
  （`backend/app/catalog_hydration_operations.py:598 → :238`），活线 0/1。
  ⇒ 即便把 A1 的字段问题绕过，**基线的补水任务本身会死在非法状态迁移上**——这条给"为什么 A1 不能单独搬"再加一票。

**剩下 23 条都不依赖新契约**（既不打那两条接口，也没读那 20 个只在新尖存在的字段）。其中能不能**干净落地**再分两档：

### B. 不依赖契约 ＋ 前端那部分能干净应用（**11 条，窄候选就用这批**）

```text
git merge-tree 直接 CLEAN（5 条）：
  d76992a  面板自己可滚，探针点名的节点就是会响的节点
  e9efec6  示例地点按名字排序，不按读到的顺序
  2d3b3fb  AI 面板按旅客看得见的尺寸排版，页脚不再被滚走
  4176e7b  手指在地图上就动地图，在页面上就动页面
  8f42cb7  枢纽用文字说出被硬规则挡掉的那一站（ORD-0232）
只在 review/ 脚本上冲突、frontend/ 零冲突（6 条 ⇒ 回掉 review/ 那个文件就是干净窄候选）：
  6b208ee  要复核的东西终于有地方复核（ORD-0146）
  7580206  读失败现在说清是哪一种失败，并留下一扇门（ORD-0126）
  82f136f  向导不再说自己的黑话，并给出缺什么的入口（ORD-0135）
  107e2db  复核动作带上自己的幂等键（ORD-0180/0183）
  952ec40  演示入口指向那条封存 journey，而不是偷偷新建（ORD-0209）
  56d20ec  Today 枢纽只留紧预算那一条结论（ORD-0212，用户直接指令）
```
唯一那个非前端冲突文件全是 `review/ord0082_0087_kill_drivers.py`（各车道的 kill-driver 台账，**不发货**）⇒
窄候选**丢掉 `review/`** 就能整批落地。

### C. 不依赖契约，但**前端文件本身要手工移植**（12 条，别指望 cherry-pick）

```text
199067b 8ee64ae f1bdbbe bfdeb1f fab8cb8 50b35e0
3e259bd dfdc5d5 f7ce8ff c4a4001 9544628 e08131e
冲突集中在：frontend/src/app/V8Experience.tsx、features/setup/JourneyTrialSetup.tsx、
           styles.css、lib/failureAttribution.ts、若干 e2e/*.spec.ts
```
⇒ 这 12 条不是"契约挡住"，是**同一文件在两棵树上已经分叉**；要带就得按 hunk 手工搬（而且它们大多正是用户这两天在等的那几条：
预算提示、raw enum 泄漏、403 措辞、被封存演示入口命名城市…）。**"能不能带"的问题在这批上变成"谁手工搬、搬完谁复验"。**

## 3 · 我给 commander 的三条可执行结论

1. **窄候选的名单就是 B 那 11 条**（不含 A 两条、不含 C 十二条）；每条的 `commit / 打的接口 / 读的字段 / merge-tree 结论` 都在
   `ord0245_backport_classification.json` 的 `rows[]` 里，可逐条复核。
2. **C 那 12 条要不要搬，是"手工移植成本 vs 用户等得到"的取舍**，不是契约问题——要搬我建议**一次一条＋每条带真机读数**，
   别把 12 个 hunk 混成一次大改（那正是我们刚在 `relaxed` 漏到界面上那单上吃过的大小）。
3. **A 那两条（ORD-0193 / ORD-0203）必须跟后端整代一起走**。别试图给它们写"基线兜底"：基线 payload 里没有 `retryable`，
   前端一旦兜底就会把"问不到"显示成"不支持"，那正是仲裁 R 口径禁止的洗白。

## 4 · 这格没做、也不声称的

* **`merge-tree CLEAN` 只证明文本能落地，不证明跑起来像样**：编译、e2e、真机三项**我没做**（那要建包/起服务，超出只读授权）。
  所以 B 那 11 条的准确说法是"**可干净摘取、且不依赖新契约字段**"，不是"落地即可用"。
* 字段差分只覆盖我打的 **12 个接口**；没打到的接口（如 `journeys/{id}/events`、`multiday`、`mobility`）未测，
  我不能说它们兼容，只能说**没测**。
* 请求侧我量了 OpenAPI（§1）：**没有新增必填请求字段**，所以"基线前端少发一个参数会 422"这一类风险**已排除到 schema 可见的范围**；
  但同 §1 的理由，**schema 没登记的运行时校验（FastAPI 里靠代码分支做的 422）不在这张网的覆盖内**——
  那要真发请求逐条打，我只打了 14 个操作里的 12 个 GET/POST 各一次。
* 没动用户链、没开 `_live.db`/`_preview.db`（本件一次数据库都没打开，全是自建一次性库；跑完删净）；
  没 `demo/reset`；没改任何人的测试；**P0 第二把尺未动**。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
