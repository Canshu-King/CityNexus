## commander 记账 @2026-09-23T00:41+08 —— 仲裁已源审 `e1580de__00bc9b5.patch`（`ACCEPTED-CODE`）；**但它审的是 C 的实现**（受我误标影响）；B 的⑤突变最小集与 C 的 ORD-0213 开工令一并转达

### ① 仲裁 `5780213489`（16:33）要点：`ORD-0219 ② demo evidence producer = ACCEPTED-CODE`，`runtime proof = PENDING B receipt`

它独立确认了补丁与冻结边界对得上，并点名三条**负约束**（来自那份 218 行门）：
```text
① DB readback：带证据的地点集合必须**精确等于** DEMO_ACCESSIBILITY_EVIDENCE
② 每个带证据地点必须 city_code == CNX-DEMO 且 source_kind == SYNTHETIC_DEMO
③ 未点名地点 metadata 里**压根没有** accessibility 键 ⇒ UNKNOWN 不是隐式 True
```
以及一条设计确认：正常 feasibility 的 `_accessibility_metadata()` 本来就先读 direct `accessibility`、再读 metadata 里的两键 ⇒ **这一笔没有另造 demo 分支，确实走正常消费路径**。
⚠ **但这些读数描述的是 C 的 `00bc9b5`**（我那份补丁就是 e1580de→00bc9b5）——它以为那是 B 的。我已在总线更正（`5780285014`）。

### ② 我的选型裁定**不变**，理由补强一条

仍**留 B 的 `21309b9`、撤 C 的 `00bc9b5`**，新增理由：冻结边界原文是 **"produced server-side from deterministic demo fixtures"**——B 把事实放在 `data/mock/places.json`（真 fixture、可分离）、provenance 由代码盖章，比 C 的表内硬编码更贴这条字面。
**同时要求：C 的两样独有件必须移植，且移植后要保住上面那三条负约束**（它们已被仲裁逐条确认，不能因为换实现而丢）。

### ③ 仲裁给 B 的两笔具体收紧（我照录转达）

**E2E 收据分两层，别混**：
```text
A. parser integration: 自然语言硬措辞 -> STROLLER/LARGE_LUGGAGE severity=HARD -> 持久化/确认
B. feasibility integration:
   sealed demo candidate with false evidence -> named blocker
   candidate with no false evidence + positive demo fact -> no false blocker
```
**第⑤步突变最小集（它替 B 钉死，四臂足够）**：
```text
M1 place-tech-art stroller False -> True      => STROLLER block gate must RED
M2 place-city-park luggage False -> True      => LARGE_LUGGAGE block gate must RED
M3 source_kind SYNTHETIC_DEMO -> LIVE_PROVIDER_CAPTURE => provenance/non-live gate must RED
M4 给一个非 CNX-DEMO place 注入 demo accessibility      => non-leak gate must RED
```
每臂照旧 `anchor_hits==1`、`bytes_changed`、restore exact。（它另说：**不要**为该 sanitizer 再造通用框架。）

### ④ 仲裁给 C 的开工令（`ORD-0213` 即刻可开）

**不要再等 F**：`ORD-0210` 量具机制已 ACCEPTED。产品修复验收保持老边界（五并发同一 hydration key ⇒ **恰好一个**持久逻辑 operation、五个调用方看到**同一个** operation_id）；**禁止 sleep／retry-backoff 伪收敛／降并发／放宽断言／只靠进程内锁**；**优先数据库层决定**（唯一键／原子 upsert／事务内 winner-readback），别拿 Python 进程锁独自承担跨 worker 真值。修后 exact SHA 上 10 个 fresh-process 全绿，再破坏**真实产品并发保护点**必须 RED——这一臂才是最终 CLOSED 所需的 product reverse mutation。

### ⑤ 现场

working tip `8b9ea04`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
