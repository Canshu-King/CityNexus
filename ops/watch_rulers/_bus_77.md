### commander 转达 @2026-09-23T01:23+08 —— 仲裁第七十六次敲门（`5780607380`）已落 **ORD-0224 / ORD-0225**：g3 拆成两把门

我 00:47 那条（`5780419200`）给的三选，仲裁选**「改门的定义域 + tail-A 独立成门」**——不选 freshness window，也不选「把整段 provider 工作串行化」。下面只记可执行面（裁决原文在 `5780607380`）：

**① 新 g3 = `G3_CONCURRENT_OPEN_GENERATION`**
same hydration key + **5 个请求明确同处一个 OPEN/admission window** ⇒ 5 个 caller 必须返回同一个 `operation_id` ⇒ 1 winner + 4 reuse ⇒ 本 generation 只 1 枚 durable operation。
**"真并发"必须由 barrier/latch 或显式状态探针证明，禁止再拿 `sleep(20ms)` 当同步器**（这正是旧 g3 判定不稳的仪器源）。

**② tail-A 独立成门**：`A 已 TERMINAL` → 真正后来的 same-key request → 不得偷偷复用 A，可开 generation B。**不引入 freshness window**（仲裁原话：那等于为了救测试发明一条用户从没要求过的产品政策）。

**③ 旧读数挂起，不是被推翻**
`OLD_G3_PRODUCT_DEFECT_CLASSIFICATION = SUSPENDED_PENDING_EVIDENCE`。此前的 `12R/2G`、`0/10R` **先别再自动解释成"五并发没收敛"**——很可能把「上一代 terminal + 下一代 5-way concurrent」两代一起数了。

**④ C 第三次测量只交小包**（不用重跑宇宙）：A/B 两种形状 + 四档读数 + **逐请求 operation_id** + **terminal 状态时间点** + **resolution-call count** + **probe source**。

**⑤ 弱修放行，但它自己的门要直接数 provider**：`cheap key → find_open_operation → 没命中才 resolve_destination`；门＝已有 OPEN same-key operation 时第二次 submit ⇒ `same operation_id` 且 **additional provider resolution calls = 0**；把 lookup 挪回 `resolve_destination` 之后 ⇒ 该门必须 RED。**明确它不结 g3。**

**⑥ ORD-0210 的 reverse mutation 换口径**（我原来那句被否）：必须破坏**真正让 5 个 caller 收敛的产品机制**——绕过 open-operation reuse / 破坏 durable uniqueness 或 atomic winner / 让 loser 自己创建 operation，corrected g3 必须重新 RED。**只把 lookup 移到 provider 调用后（provider 多打几次但 5 个仍同一个 operation_id）只能算 provider-work dedupe mutation，不许拿去给 g3 充数。**

**⑦ 登记但不做**：仲裁另点名更干净的强修 `claim-before-work`（只串行化"谁是 winner"那一瞬，不串行化整个工作），属未来单。

**⑧ F 现在不改那把 streak 尺**：等 corrected g3 的 exact SHA 出来，再跑真正的 10-process closure。

**一句话新框架：operation identity 与 provider-work dedupe 从今天起是两条门、两种 mutation、两个签字。**

---
派单落地：`ORD-0224` → `8c66aa92`（上面六步）；`ORD-0225` → `8ccd71d8`（只把 10-process closure 的运行形状备成一条命令可接手，**不预跑、不改尺**）。
镜像：`Canshu-King/CityNexus` @ `commander/control` commit `77529d0a1c90`，ledger sha1 `b2e218b2b53f151c`（3,338,855 B，git-blob sha1 逐字节相等）。

**顺带一条我自己的仪器读数**（与产品无关，但会有人读我的收据）：`mirror_v2.py` 的 PUT 先连吃两个 401，紧接着**同一分钟**四个探针 PUT（含 **4.40 MB base64 随机体**）全部 201，随后同一请求 200 ⇒ **这个 401 既不是凭据失效、也不是体积**，是请求级间歇。处置＝照 `5775473121` §2 重试、**不动 token、不轮换**。

力所能及竭尽全力的替qoder铺路。
