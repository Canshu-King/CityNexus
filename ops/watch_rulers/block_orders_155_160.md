- id: ORD-0157
  to: 8c66aa92
  priority: P0-critical
  if_head: d26933c
  order: |
    【ORD-0151 的更正与收敛——本单覆盖 0151 的"两处都要改"前提，其余判据照旧；两单一起结】
    我 20:5x 自己探针推翻了我给你的前提：**identity 早就只有一个主人**。
    `catalog_hydration_operations.py:37` 就是 `from app.anywhere_capability import resolve_destination`，
    调用点在 `:293`（受理算指纹）与 `:527`（作业 RESOLVING_DESTINATION），`is` 比对 = True，
    两条端点今天对同一输入返回同一个 canonical ⇒ **不要再"接两处"，也不要新造第二个 resolver**。
    要做（按仲裁 `docs/anywhere_capability.md` @ `5238911f` 的 R10 段）：
    ① 在**那一个** `resolve_destination`（`anywhere_capability.py:165`）里接 Photon：
       `resolve_destination(raw) -> RESOLVED | AMBIGUOUS | NO_MATCH | RUNTIME_FAILURE`，
       RESOLVED 必须带真实 provider id + canonical display name + WGS-84 centroid/extent + resolver provenance；
       顺手把 `:166-173` 那句 docstring（"using only sources already in this process"）改掉——它是设计自述，不改就会有人当契约。
    ② 四类必须分开，别再折叠（我实测现状只有前两类的形状）：
       resolved + 本地证据不足 → **HYDRATABLE** + `recommended_action=PREPARE_DESTINATION`；
       resolved + 共享 planner 已能出 SELECTABLE → READY + START_PLANNING（**不许为流程再跑一次 hydration**）；
       resolver 健康 + 0 candidate → UNAVAILABLE + `NO_CANONICAL_IDENTITY`（**canonical=null**）；
       resolver 超时/不可达 → 具名运行性（`REASON_RESOLVER_UNAVAILABLE` / `DESTINATION_RESOLVER_UNAVAILABLE` 已在词表里，
       且已在 `TRANSIENT_REASONS`）→ 503/retryable，**不得**报结构性 UNAVAILABLE、**不得**写 hash。
    ③ 枚举纪律：机器码只用现有 `PREPARE_DESTINATION`（`anywhere_v1.openapi.yaml` 的 `RecommendedAction` 里有），
       **禁止**新增 `START_HYDRATION` 第二个枚举；UI 文案可以写"准备目的地"。
       今天未解析县答的是 `CHOOSE_ANOTHER_DESTINATION`——那是对真实存在的县说"换个目的地"，必须消失。
    ④ **挂起项（等我或仲裁裁，别自己拍）**：`pending:<原文>` 现在被写进 NOT NULL 的
       `catalog_hydration_operations.canonical_destination_id`（`db/models.py:1174`）并被 sha 进 `fingerprint`，
       且 `zzxqvw-不存在县` → `pending:zzxqvw不存在县`（原文被归一改写）。这与仲裁的
       "canonical=null" + "raw text is not identity" 两句**不能同时成立**。
       在裁定前：新代码路径**不许**再往 fingerprint 里喂用户原文；已落库的 `pending:` 行**不许删**（R10：兼容读 + 就地回填）。
    验收：仲裁 R10 的 7 条门逐条（含"摘掉**任意一边**的 resolver 调用门必须红"——今天两边同源，
       所以这条要用"调用点级"突变：把 `:293` 或 `:527` 任一处换成不经 provider 的本地路径必须判红）；
       三例真输入（云和县/贡山/乱码县）+ 一例注入 timeout；**不许 mock 出 canonical**；
       先红后绿（红基线 = 我 21:0x 的读数：provider 调用 0、三例全 `pending:`、`NO_REGISTERED_SOURCE`）；
       全量红集合 ⊆ `eef24d9` 的 14 条基线。
    【顺序】0157 > 0158 > 0125 > 0112 > 0155。禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`、禁 `demo/reset`（R13）、
    解释器 3.12.14、凭据全清、不改 `data/mock/**`、交付只追加自己那块（`newline="\n"`，带"拿掉我的块必须逐字节还原"证明）。
  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7（覆盖 0151 的"两处"前提；provider 调用 0 是我自己量的）

- id: ORD-0158
  to: 8c66aa92
  priority: P0-critical
  if_head: d26933c
  order: |
    【ORD-0152 的验收升级——仲裁契约 `docs/planning_constraint_input_truth_policy.md` @ `52d7ccb6`，原单判据保留】
    排查顺序必须是**边界链**，找"第一个把 1600 变成 0 的地方"，不许只在最后一层打补丁：
    `raw user input → extraction → normalization → persistence → readback → planner request → feasibility core`，
    每个边界都打印预算值 + 单位（minor/major 写明）。
    硬语义：显式 0 才是 0；未提供 = null/UNKNOWN；抽取不确定 = NEEDS_CONFIRMATION/BLOCKED；抽取失败 = 具名 parse error；
    **三种都不许 fallback 成 0**。产品自己丢了预算时 UI **不许**说"你去调整预算"，更不许把方案判成数学上不可行。
    固定回归句（原样，一字不改）：`两个人三天全部加起来别超过一千六百块`
    九条断言：①归一化 1600 CNY；②minor 表示正确（160000）；③party_size=2；④scope=TRIP_TOTAL（不是人均/不是按天）；
    ⑤持久化后读回同值；⑥AI 入口与直接规划入口看到**同一个** normalized budget；⑦planner 除用户显式 0 外永不受 0；
    ⑧突变"缺失/解析失败→0"必须被杀；⑨产品丢预算时不得吐出"预算太低"文案。
    【与 0155 之外的那条已定位机制】我 20:4x 已把一处**捏造 0/1** 写进账本 `block_budget_zero_2046.md`：
    `app/stay_mobility.py:159-176` 在 `JourneyTripContext` 缺失时凭空写 `party_size=1`、
    `occupancy_json={"adults":1}`、`stay_budget_amount_minor=0`，并在 `:1774-1780` 把它发给 provider
    （`models.py:801` server_default="0"；`operations/v9.py:1137` 也写 0）。
    ⇒ 本单必须**分别**回答两问：(A) 行程总预算 `journeys.budget_amount_minor` 这条链有没有丢；
    (B) 住/供应商侧 `stay_budget` 这条链是不是 0 的来源。两条都要读数，不许合并成"预算问题"一句。
  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7（与 0157 同 owner，排在 0157 之后）

- id: ORD-0155
  to: 8c66aa92
  priority: high
  if_head: d26933c
  order: |
    仲裁已裁 d6b（5760739440 ① + `docs/accessibility_evidence_mapping_policy.md` @ `fdda90d2`）：**选 A——加一层
    OSM 标签 → canonical accessibility 证据的适配层**，而且**不要**新增 `source_kind=OSM_TAG_INFERRED` 去破坏现有 provenance 枚举。
    要做：
    ① 规范化边界：`raw provider record → accessibility evidence adapter → canonical predicates + provenance → hard-feasibility policy`；
       planner 不许自己 parse OSM tag 字典，前端与 LLM 更不许各自解释原始 tag。
    ② 谓词级映射（v1 最小集）：`wheelchair=yes` 只证 wheelchair 这一项；`no` = 冲突；`limited` = PARTIAL/LIMITED，
       **不得偷升**为完全可达；无 tag / 看不懂 = UNKNOWN；`highway=steps` 这类显式冲突继续优先（`ACCESSIBILITY_CONFLICT` 是正例锚点，必须仍绿）。
       不得从一个 tag 推出无关谓词（无障碍厕所/电梯/盲道/无障碍车位/协助人员都不许被发明）。
       若将来要定义"wheelchair=yes ⇒ 无台阶入口"这类更宽关系，必须是**服务端版本化策略 + 有测试**，不能由调用方假设。
    ③ provenance 必填：`source_provider`（用仓库现有 provider 标识）、`source_entity_id`、
       `source_kind` 按获取方式取**现有**值（live 取 `REMOTE_PROVIDER`，冻结快照取 `OFFLINE_SNAPSHOT`/现有 fixture kind）、
       用到的 tag key/value、`observed_at/fetched_at`（可知则填）、`fact_quality` 按现有服务端证据策略、
       以及 derivation 标识 `OSM_ACCESSIBILITY_TAG_MAP_V1`。
    ④ 冲突优先级：显式冲突/负证据 > 显式正证据 > UNKNOWN；冲突必须在 details/provenance 里看得见，不许折成"缺证据"。
    验收 = 仲裁文档 §7 的八条（16 地点 × 6 措辞固定 corpus：现有两种形状不变、OSM 正例不再判缺证据、
    缺失/无关继续 UNKNOWN 且**不得默认变可达**、冲突仍 `ACCESSIBILITY_CONFLICT`、limited 不升级、provenance 齐全、
    三条突变必红：摘掉映射层⇒正例红；把 UNKNOWN 变 accessible⇒红；忽略冲突优先⇒红）。
    §8 的屏幕语义也要：UNKNOWN 说"未核实"，不许说"不可进入"；冲突要说清冲突。
    【顺序】排在 0157/0158/0125 之后；不许为过任何门而放宽 `UNKNOWN != ACCESSIBLE`。
  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7（按 to: 落 C；harness 侧量化见 ORD-0153/0160）

- id: ORD-0156
  to: 8ccd71d8
  priority: high
  if_head: d26933c
  order: |
    ORD-0155 的**门**归你（F），别让实现方自己给自己发通行证：
    ① 把仲裁 `accessibility_evidence_mapping_policy.md` §7 的八条做成常驻门（固定 corpus 16×6，逐条断言 reason_code，
       断言读**渲染出来的语义**不是内部字段）；
    ② 三条必红突变写进门的 kill 清单：摘映射层 / UNKNOWN→accessible / 忽略冲突优先级；
    ③ 加一条**边界不动**门：`UNKNOWN != ACCESSIBLE` 在映射层落地后仍须成立（缺失/无关 tag 的格子不许变绿），
       这条是防止 A 方案被实现成"看见 OSM 就放行"的唯一保险；
    ④ 契约侧：把 `OSM_ACCESSIBILITY_TAG_MAP_V1` 写成版本化 derivation 字段进契约（与 `readiness_policy_version` 同族），
       并核 `source_kind` 只能用**现有**枚举值——仲裁明确不许新增 `OSM_TAG_INFERRED`。
    红基线就用 ORD-0128 已交的 96/96（`{"tags":{"wheelchair":"yes"}}` 全判缺证据）。
    【顺序】排在 ORD-0131、ORD-0133 之后；突变与门的写域只在 `backend/tests/**` 与 `contracts/**`，不改产品码。
  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7

- id: ORD-0160
  to: d291c9dc
  priority: medium
  if_head: d26933c
  order: |
    ORD-0153 解锁一条：**仲裁已经裁了**（5760739440 ①，A 方案 + `docs/accessibility_evidence_mapping_policy.md` @ `fdda90d2`），
    你单里"在仲裁裁定之前不得改读法"这句的前置消失——但**读法不在 harness 里改**：
    映射层落地归 C（ORD-0155）、门归 F（ORD-0156），你只做三件事：
    ① 把 96 格证据形状表做成 lab 内常驻可复跑门（换 HEAD 能自测、与基线逐项 diff、变了 RC≠0）；
    ② 扩到非轮椅硬需求（婴幼儿车 / 静音·感官 / 无阶梯路线 / 大件行李 / 开放时间硬要求），给同分母
      （格数、被挡数、reason_code 分布）⇒ 判这是"无障碍专属"还是"证据形状通用缺陷"；
    ③ 0155 落地当天**换树重测**并把新增被挡格子的具名 reason_code 贴回来（如果 `limited` 被偷升成 fully accessible，
      你那 96 格表是唯一能抓到它的量具）。
    禁令不变：不放宽断言、不加 skip、不许在 harness 侧接受裸 OSM 标签当"已核实"；
    node_modules 只准真复制（禁 junction/symlink，D-7）用完删并回报剩余；端口只 :850x；
    不碰 `:4781/:4782/:8693` 与 `_live.db`；全线禁 `demo/reset`（R13）；不调真 AI provider、不读凭据值；
    不对 github.com 用 git 网络操作。
  status: DISPATCHED@2026-09-21T21:0x+08 by 494abfd7（覆盖 ORD-0153 里"等裁定"那句）
