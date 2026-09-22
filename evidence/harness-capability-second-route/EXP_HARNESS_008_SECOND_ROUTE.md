# EXP-HARNESS-008 · 那六个"永不成约束"的码，产品里有没有第二条进 HARD 的路
SESSION=d291c9dc（HARNESS）· 2026-09-22 19:5x+08 · 尖 `dfdc5d59205f680306ce429f73240f28e9332b1f`（本机导出 `lab/snap_dfdc5d5`，350 文件）· **产品码 0 改动**

## 0. 问题从哪来
18:5x 我交过一张 64×8 措辞分母，结论是"15 个码里 6 个永不生成约束行，因为 `app/capabilities.py:817-828` 那六行 `add(code, params)` 从不传 severity"。
那句话**只证明了文本这条路径**。还差一问：**用户/界面有没有别的方式把这条需求说成 HARD，而且说成之后产品会不会真的按它筛？**

## 1. 第二路径存在，而且是权威写入口（实测，非读码）
`app/main.py` 的 OpenAPI 里提到 capability/constraint 的**写操作共 8 个**，其中三条相关：

| 入口 | 载荷 | 实测 |
|---|---|---|
| `PUT /api/v1/travelers/{id}/capabilities` | `CapabilityInput`（`schemas.py:47-59`）里 **`severity: Literal["HARD","STRONG","SOFT"]` 由调用方给** | **7/7 码 HTTP 200** |
| `POST /api/v1/travelers/{id}/capabilities/confirm` | 同上；`_capability_input_rows`（`main.py:2158-2183`）**不 clamp severity**，HARD 还替它补 `confirmed=True` | **200** |
| `POST /api/v1/journeys/{id}/constraints` | `ConstraintInput.kind: Literal["HARD","SOFT"]`、`rule_code` 不限词表 | **201**（全部） |

回读（`GET /travelers/{id}/capabilities`，报的是服务端自己的存储）：**7 个码（6 个目标码＋控制码 `STEP_FREE_REQUIRED`）逐一 `severity=HARD`、`class=` 原类（`SOFT_PREFERENCE`/`TRIP_CONTEXT`/`HARD_ACCESSIBILITY_NEED`）、`confirmed=True`、`active=True`，`persisted_n=1`**；再经产品自己的两个消费者读出：`capability_constraint_items()` 与 `_journey_constraints_with_capabilities()` **每码各 1 条行（记作 1/1）**。（下方 §2 的 9 个用例＝这 7 个码＋两条"正向证据不误伤"的重复码，别把它当码数。）
⇒ **我 18:5x 那句"用户没有任何办法把它说成硬约束"是错的**：文本没办法，**写入口有办法**。这句在此更正。

## 2. 但是"写进去"之后，门分两类反应（这才是要紧的）
把上面真实写入的行喂回 `evaluate_feasibility`（进程内，一次性库；地点记录是我自己造的合成夹具，已在收据里标注）：

| 码 | 地点证据 | 门的反应 | passed | 判读 |
|---|---|---|---|---|
| `STROLLER` | `stroller_accessible=false` | **`STROLLER_ACCESS_UNAVAILABLE`** | False | **端到端执行了** |
| `STROLLER` | `stroller_accessible=true` | 无 | True | 不误伤 |
| `LARGE_LUGGAGE` | `luggage_accessible=false` | **`LUGGAGE_ACCESS_UNAVAILABLE`** | False | **端到端执行了** |
| `LARGE_LUGGAGE` | `luggage_accessible=true` | 无 | True | 不误伤 |
| `SLOW_PACE` | 任意 | **`UNSUPPORTED_HARD_CONSTRAINT`** | **False** | **整趟被拒，不是按需求筛** |
| `QUIET_ENVIRONMENT` | 任意 | 同上 | False | 同上 |
| `INDOOR_PREFERRED` | 任意 | 同上 | False | 同上 |
| `SENSORY_LOW_STIMULATION` | 任意 | 同上 | False | 同上 |
| `STEP_FREE_REQUIRED`（控制） | `step_free=false` | `ACCESSIBILITY_CONFLICT` | False | 正常按证据判（我第一版把它猜成 `ACCESSIBILITY_UNVERIFIED`，**是我期望写错**，已改成"必须失败且必须具名 ACCESSIBILITY*"的计算式期望；9/9 满足） |

机制在 `feasibility.py:254-266` 的 **`_CAPABILITY_GATE_CODES`（11 个）**：里面**有** `STROLLER`/`LARGE_LUGGAGE`，**没有**那四个 `SOFT_PREFERENCE` 码；`:621-624` 的注释写得很清楚——**门看不懂硬规则时绝不绕过**，于是直接失败。

## 3. 结论（三分，别再混成一句话）
1. **`STROLLER` / `LARGE_LUGGAGE`：只差解析器那一个 severity 参数。** 写入口→持久化→约束行→门执行，四环我已逐个跑通（本轮实测，不是推）。
2. **`SLOW_PACE` / `QUIET_ENVIRONMENT` / `INDOOR_PREFERRED` / `SENSORY_LOW_STIMULATION`：缺的是门的实现（进 `_CAPABILITY_GATE_CODES` 并写求值分支），不是参数。** 而且**只补 severity 会把"静默不执行"变成"整趟旅程不可规划"**——这是给任何想做那"一行修改"的人的实质警告。
3. **词表与写入口都不设防**：`ConstraintInput.rule_code` 是自由字符串，任何码都能以 `kind=HARD` 落库；本轮我只写了这 9 个冻结词表内的码，但**词表外**的 rule_code 同样能写进去，然后一律 `UNSUPPORTED_HARD_CONSTRAINT`。这条要不要收（写入端校验 rule_code ∈ 词表/可执行集）请仲裁一句话。

## 4. 复放与坐标
- `lab/tools/harness_second_route_008.py`（写入口＋逐臂归因：capability 路 / journey-constraint 路分开评，避免把 `UNSUPPORTED_HARD_CONSTRAINT` 错归给某一条）→ 收据 `lab/evidence/second_route_audit_1945.json`
- `lab/tools/harness_second_route_chain_008b.py`（端到端链条＋计算式期望）→ 收据 `lab/evidence/second_route_chain_1949.json`
- 环境：`D:\moodle\CityNexus\.venv\Scripts\python.exe` 3.12.14；导出式 `git -C _qoder_integration_20260919 archive dfdc5d5 backend data contracts tools | tar -x`

**合规**：全程进程内 `TestClient`，**0 端口、0 HTTP 服务、0 provider 出网**（两 key 导入前清空、`CITYNEXUS_AI_ENABLED=false`）；**未发 `POST /api/v1/demo/reset`**（种子走 `app.services.seed_demo`，收据里 `demo_reset_issued: 0`）；一次性库 `engine.dispose()` 后删除、**复验 `db left: none`**；未碰 `_live.db`/`_preview.db`、未写权威树与 `CityNexus\**`（只 `git archive` 单向导出＋只读 grep）；未跑突变、未放宽/deselect 任何断言、未改产品码。
