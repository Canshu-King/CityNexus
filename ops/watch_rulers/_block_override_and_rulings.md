## commander @2026-09-22T13:0x+08 —— **用户优先级凌驾令已采纳**（总线 `5771352224`）＋ 仲裁 49 敲门的三条裁定（`5771378382`）＋ 我亲测的两笔交付

时间一律 Python 生成、显式 `+08`。本节不新建 ORD（照 §7「别为每个小发现开单」），只做三件事：落裁定、改派五线、记我量到的读数。

### ① 采纳 USER PRIORITY OVERRIDE：五线不再被 P7 冻着

`5771352224` 明文撤销「sleep until P7 / 只交第一步」这类把 HARNESS、HUMAN JOURNEY、HERMES、REVOLUTION LAB
按住的规定。**P7 只能限制"必须有完整 resolver 集成"的那类结论，不能限制这些线的存在、清醒、自主与有用工作。**
我之前写的「继续睡」一律作废，不再出现。现在的施工令（每线一个可执行动作，不是文书）：

- **HARNESS `d291c9dc`**：跑真东西 —— 恢复历史 EAC/Harness 运行时、在隔离工作树里对当前构建过
  Today/Live/Map/Wallet/AI/Simulation 面、跑 Provider Evidence 与 Live Shadow（当前产品支持的范围内）、
  审计产品/供应商真值不匹配；确认缺陷才在**自己的**隔离树里打补丁，产出可复放证据＋候选修法。
  resolver 场景被堵就**换下一个实验**，不是睡。60 分钟检查点：runtimeState｜实际用的可执行/运行时｜
  隔离工作树｜完成的一个实验｜一个发现/修复/证据工件｜下一个已在跑。
- **HJ P1 `1a986a24` / P2 `d4b04a0f` / P3 `aad2d1f2` / P4 `4e974ae5` 全部现在起**：
  P1 预算型 ≥2 个 journey（含一个空/降级恢复例）｜P2 承诺型（建/护承诺→中断→replan→接受/拒绝→刷新重进）｜
  P3 急躁移动型（先 390×844：双击、返回、刷新、后台/回来、地图手势、慢操作，盯可见恢复与重复提交）｜
  P4 偏好型（晚出发/少走路/饮食/风景/休息；硬偏好与软偏好的可见性与解释；故意用有营业时间约束的行程）。
  **碰到 blocker 记录后继续下一个场景，不许一堵就停**；本工作块目标 ≥8 个拟人 journey 总计。
  隔离要求不变且优先：只在自己的一次性 DB 副本/独立 profile 上走，证明不齐不许开始点（`GET /experience` 读时写）。
- **HERMES `9baacb24`**：manifest 只是必要杂务，不许吃掉整条线；并行推进 H4 只读真值平价、
  H5 proposal-only replan、H6 有界接受正/负、H7 幂等、H8 提示注入边界、H9 断供/兜底、H10 planner 平价；
  只有当存在安全的进程内既有凭据时才试 H11 模型支撑。检查点：最高真实执行到的 H 门＋逐条通过/失败证据。
- **REVOLUTION LAB `5ea3bedc`**：停止只做第 0 步文书。隔离证明展示之后，DeepSeek Builder 与
  Hermes Operator/Critic 在**四条已冻结边界内**拿广谱实验室自主权：允许在 LAB 仓内改架构、删陈旧层、
  合并拆开的 planner/AI 路径、换内部 API、用兼容的开源供体改 UI、跑测试/浏览器/shell。
  2 小时目标＝Mission A（没见过的目的地：可见产品→provider 身份→准备→诚实计划或**具名精确 blocker**）
  真跑一遍＋提交；某架构堵超 20 分钟就**换架构**，不等权威线。禁止只交一篇架构感想。
  四条边界照旧：不碰权威工作树/受保护历史、不对活库做破坏性实验、不漏密钥、不碰真钱/真预订。

### ② 仲裁 49 敲门三条裁定（原文在 `5771378382`，这里只落执行令）

1. **能力第四格＝选 B，仍冻结 `UNKNOWN_RETRYABLE`**（理由：`NOT_ANSWERED` 描述的是"provider 有没有答"这条证据事实，
   capability 轴要覆盖 DNS/429/5xx/transport 等 transient，名字得比证据事实更稳定）。
   **C 改：enum ＋ 两份契约 ＋ emitter ＋ 任何 parity/type surface；不加别名、不双写。**
   `P7_UNKNOWN_RETRYABLE_CAPABILITY_ACCEPTANCE.md` 不改。**D/F/E 继续与字面值解耦**（我已这样下了），
   改完由我复跑才签——我此刻的读数仍是 `NOT_ANSWERED` 在 `e0fc697`（enum `:67`、发射 `:1391`）。
2. **参考尖改口 `e0fc697`，但它不叫稳定基线**：`CURRENT_INTEGRATION_REFERENCE_TIP = e0fc697`、
   `NEW_FAILURES_VS_116a031_ON_MATCHED_NODEIDS = 0`。全量只有我这一把，仍是 observation；
   要 baseline 得 ≥3 次可比跑＋交集/区间/游名。
3. **§8 的 `{}` 拆适用性**（这道题我原本要 F 交回给我，仲裁直接裁了）：
   `attribution_applicable=true && {} => RED`；`attribution_applicable=false && 无 attribution 对象 => GREEN/N_A`，
   且 **N/A 必须由外层已有结构化状态自证**，不许靠 helper 内部 `return {}` 表达。
   ⇒ **F**：把 ORD-0200 的 test_5 从"选择题"升级成这条双向判据（两个方向都要反例：漏报躲进 `{}` 必红；
   为过门给 N/A 伪造四字段也必红）。

### ③ 我刚亲测的两笔交付（都在 `git archive` 干净导出树上跑，解释器 `.venv` 3.12.14，`DEEPSEEK_API_KEY` 已 unset）

- **F `agent/f-ord200-20260922` @ `c79304d`**（父＝`e0fc697`，只加 253 行门）：
  `--collect-only` ⇒ **1184 collected**（= 1178 ＋ 它自己的 6 条，对得上）；
  `pytest tests/test_qoder_attribution_fields_hard_door.py` ⇒ **6 passed in 0.57s**，六条名字分别是
  五种真形状落冻结语义／每种 RED 形状各有一个咬合反例／实现确实写 null 不写 0／成功路径也带 attempt 历史／
  **门是承重的**／第 5 条把 `return {}` 当选择题交回（**它没有替仲裁选，这条纪律我记功**；现在按 ②-3 升级）。
  ⇒ 判 **PARTIAL：等 ②-3 的双向判据**，未签。
- **B `agent/canary-ord198-20260922` @ `7167ef6`**（父＝`45c8462` ＝ `e0fc697` 的 merge）：
  `provider_identity.py:98-99` 加 `features_viewed: int|None` ＋ `candidates_before_filter: int|None`，
  `:303-304` 用 `len(features)` 与目的地分级计数填，`anywhere_capability.py:569-570` 把两个计数随
  attempt 一起交给 C 的载荷 ⇒ **字段是真的，不是摆设**。
  ⚠ 但我在**含 B 这笔的导出树**上跑 C 的那条 strict xfail：结果仍是 **XFAIL（6 passed / 1 xfailed），没有 XPASS**
  ⇒ 说明**光有计数不会自动让"畸形"与"确实没有"分开**，C 必须真的消费它（把 `features_viewed>0 且
  candidates_before_filter=0` 判成 `MALFORMED_EVIDENCE` 而不是 `PROVIDER_NO_RESULTS`）。
  这正是 C 的下一步，不是 B 的缺陷。**给 C**：接上它，接上后那条 xfail 才该以 XPASS 报错、由你摘标记。
- **LAB `197a27d`**（12:33「用测量重交隔离证明，并更正我写错的一行」）：我还没读它的证据内容——按 ① 的新令它已属过去式，
  下一份要看的是**能跑的 Mission A 代码**，不是又一轮文书。

### ④ 环境急事（我自己造成的，已处置，报给你）

12:52 我建导出树时撞上 **`No space left on device`（D: 剩 0.255 GiB / 307.4 GiB，99.9% 满）**，
`git archive | tar` 中途失败（`v_e0fc697` 当时不完整）。处置：删掉我自己 12 个 `git archive` 导出树
（`v_*`，每份 105–118 MB，共 **1,405 MB**，全部是可从 git 重放的纯拷贝，无任何唯一内容）＋一次自检目录；
然后**重新完整导出**三份（`e0fc697` / `7167ef6` / `c79304d`，各 6,846–6,847 文件）后才跑上面的数。
现在 D: 剩 **1.487 GiB**。**给全体车道的提醒**：`git archive` 一份全树≈110 MB，
请复用已有导出目录、别各自堆新的；这条现在就要成立，因为五条线同时开始跑。
（我此前删的都是自己的导出，权威树、车道工作树、用户库一个字节都没动。）
