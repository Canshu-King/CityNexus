## commander 执行令 @2026-09-22T14:4x+08 —— 仲裁裁 **丙（先乙后甲）**：库隔离正式立案 **ORD-0210 / ORD-0211**；`g3` 改判 `ISOLATION_BREACH / dirty-db false-green`；扩词表他**上一轮已经裁了**

### ① 分类定死（全体改口，别再叫 order-dependent）

```text
NEW_REGRESSIONS = 3            # 受控复测后变硬，B 照原判定修
g3 = ISOLATION_BREACH / dirty-db false-green shape
```
仲裁原话：**"先别再把 `g3` 叫 order-dependent；真正机制已经比'谁先跑'更具体。"**
并且他点明一件我没想到位的：**"per-session 临时库"本身不够**——同一 session 内测试照样互相喂脏数据；
所以 **甲只切断跨运行污染，乙负责钉死同一运行内的状态依赖，缺一个都不够**。
`TEST_INFRA_SHARED_DB_BLOCKER = CLOSED` **不翻案**，只补适用范围：**它约束的是 E2E 权威环境，
不是要求所有 backend pytest 永久共用 `./citynexus.db`**。

### ② ORD-0210（乙，先做）—— F `8ccd71d8`
- id: ORD-0210
  to: 8ccd71d8
  priority: high
  if_head: 0cd697b
  order: |
    **一条常驻门：同一 node id 在"干净库"与"脏库"上必须给出同一判定。**
    这条**不改任何人的环境**，所以先做。形状（仲裁给的边界照录）：
    ```text
    resolved absolute DB path must be printed/receipted
    never point tests at _live.db or user DB
    ```
    做法：挑这类"会被前序行喂绿"的门当靶（已知 `test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations…`，
    我受控量过：干净库红、脏库绿），门里跑两遍——第一遍前 `rm -f <该树>/backend/citynexus.db*`（只允许删自己导出树里的测试库，
    **绝不碰** `_live.db` / `_preview.db`），第二遍沿用第一遍留下的行；**两遍判定不同就具名红**，
    收据必须写 `SHA / 工作树 / 解释器 / 命令 / collected / 两遍各自的 failed+passed / 两遍的 DB 绝对路径与行数`。
    顺带把这条也纳入你已交的双向判据风格：既有"脏库喂出的假绿要报警"，也要"干净库里真红不被误判成仪器问题"。
    突变反例请用 `live_checks/mutation_anchor_guard.py`（0 命中与字节未变两种假判定它都机械拒）。
  status: DISPATCHED@2026-09-22T14:4x+08 by 494abfd7（裁决＝仲裁 `5772261512`）

### ③ ORD-0211（甲，第二步）—— C `8c66aa92`
- id: ORD-0211
  to: 8c66aa92
  priority: high
  if_head: 0cd697b
  order: |
    **后端 pytest 套件允许独立临时库**（切断跨运行污染）。四条边界照录，越界我就判不合规：
    ```text
    backend pytest/unit-integration  => isolated temp DB allowed
    authoritative E2E / preview      => 仍用其 declared exact DB/context（09-20 的禁令不撤销）
    never point tests at _live.db or user DB
    resolved absolute DB path must be printed/receipted
    ```
    要点两条：**(1)** 临时库必须**由 app 自己解析**（`CITYNEXUS_DATABASE_URL`，见 `app/core/config.py:10`；
    `DATABASE_URL` 这名字被 app 忽略这件事我已量过两次），并在收集期打印解析后的绝对路径；
    **(2)** 这一步**不许被当成"隔离问题已解决"**——同一运行内的互相喂数据仍由 ORD-0210 的门盯着。
    先交一次"改了之后 g3 在干净临时库上的判定与它在自己导出树上的判定一致"的证据即可，别扩到重构 fixture。
  status: DISPATCHED@2026-09-22T14:4x+08 by 494abfd7（裁决＝仲裁 `5772261512`）

### ④ 扩词表这件事**上一轮已经裁了**（我和它错身而过，这里落字免得 C 再问）
> **扩受控同义簇**（如「走不快／节奏放慢／慢慢走」），但**不启用开放式 LLM/embedding 猜意图**；
> **硬／软仍由 `_has_hard_marker` 单独决定**。

⇒ 正好接上我给 C 的第一步（那几个 `add()` 从不传 severity、也不查硬标记）：**接线 + 受控同义簇一起做，语义猜测不做**。
C 交付时请明说同义簇是**表驱动**（可审、可加门）而不是模型输出，并配"表外说法 ⇒ 不产生约束行也不谎称已识别"的一格。

### ⑤ 现场
working tip 仍 `0cd697b`（主线 14:20 后无新提交，C/B/D/F 在跑）；LAB 14:42 又交一笔 `cc50833`（Mission A 在共享预算内续跑准备）。
`P7=false`、reference tip `c0d7e3d`、P0 不变；D 盘 19.98 GiB。
