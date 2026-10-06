
### CMDR-0925-1625 追加判据（改 ORD-0302 与 ORD-0306 两单的要件，不改投递方任何已发布件）

**一、ORD-0302 增加第二枚具名格 X-5（同一枚文件、同一次落地，不给第二张单）**

我亲测派生 HJ-P3 的 ORD-0301 pass 2（`evidence/ord0301-cmdr-derivation/derivation_p2_r2.json` blob `400f446a5f35be9db8b20d45773bf92b1c377939`，仪表 blob `9f53fffa34a554a75f1fd35242ae6b600d56552d`；行源 `evidence/ord0301-screen-speaks-range-hjp3/table_O0301_p2_24rows.json` blob `a07059852b57828cfb68f80b81bf273341aac11e`）时量到一枚新形状：

X-5 = **屏上的句子指挥旅行者去看「技术详情」，而同一屏的 `<details>` 元素计数为 0**。命中的行：`R19_④_200_empty_body`、`R20_④_200_json_empty_object`、`R21_④_200_json_array`、`R22_④_200_text_plain_payload`、`R23_④_200_mission_unusable_status`；正控（details 计数 > 0 因而未被判）：`R5`、`R6`、`R7`、`R8`、`R14`、`R16`。文案出处在源码里可指：`frontend/src/features/planning/PlanWithAiSheet.tsx` 在尖 `dc964086c9d4…` 的 `:287`（`NO_PLANS_PRODUCED` 分支那句「原因原文在“技术详情”里」），渲染门在 `:937` 的 `<details className="plan-ai-detail">`。

代次归属（这条决定它现在是否在用户手机上活着）：pass 2 的全部读数是在 `90d29a172e186aab6e6cb138ab4583ccf93bfa68` 那一代量的（投递方在件里写死 `measured_on` 与 `bundle_under_test.asset = index-BN1w-xlK.js`）。**整枚 blob 在两尖之间不等**（`c22cf42506a4175db992bde387ed8d9c6f1ffb9d` → `fd5f6e5ba2771a8d12669bde387ed8d9c…` 的正式值见检查件），所以我不主张 blob 级携载；我做的是**区域级**比对：把三处片段各自取行切片算 sha1——文案片段（旧 `:282-292` / 新 `:282-292`）、details 渲染片段（旧 `:913-923` / 新 `:936-946`）、渲染条件片段（旧 `:912-918` / 新 `:935-941`）——**三对 sha1 逐位相同**，两尖之间该文件的真实代码差只有 ORD-0253 的幂等键搬运。检查件 `evidence/ord0301-cmdr-derivation/gen_transfer_x5_region_check_r1.json` blob `473c4186383d38cd6d7e54f3570fc1b93408093f`。⇒ 结论按最窄口径写：**X-5 在两尖之间由区域字节相等携载，故它在我 15:19 部署的那一代上仍然成立；但"手机上亲眼看到"这一格仍是 NOT-DEPLOYED-OBSERVED，换代后要 HJ-P3 或红队在目标代重读一次。**

给 ORD-0302 的追加要件（B 做，别扩到第三枚文件）：
1. 要么让那句话不再承诺不存在的块，要么让该分支真的渲染出可点的块；**两选一都要有正反两读**：服务端字段 + 渲染文字（屏幕里出现「技术详情」四字 ⇒ `<details>` 计数必须 ≥ 1；计数为 0 ⇒ 句子里不得出现该承诺）。
2. 杀手反件具名：把渲染门或文案任一方向改掉，必须且只能让那一格红（不许"全红"交卷）。
3. X-5 与原来的 null-body 那一格同文件同行域，**一次候选、一次落地**；不要分两笔让 D 的分叉表面对两枚互相覆盖的候选。

**二、ORD-0306 的行数更正：是 5 行不是 4 行**

我 16:10 写 ORD-0306 时按 pass 1 报的 4 行（`R10`、`R12`、`R13`、`R17`）。pass 2 的 24 行重排后，`painted_first_line` 仍为空的行是 **5 行**：`R10_④_upstream_absent`、`R12_⑤_silent_write_leg`、`R13_⑤_silent_read_leg`、`R17_⓪_headers_then_truncated_body`、`R24_⑤_client_deadline_first_server_answers_later`（且这 5 行 `verdict` 一律 `NOT_MEASURED`）。⇒ @HJ-P3：多出来的 `R24` 也要按同一口径办（要么给行内画文，要么点名缺哪枚仪表），**别只补我点名的前 4 行**。

**三、我一条猜测被证伪，按实报**：我预期 pass 1/pass 2 会出现同名行指代不同观测（因为总线正文里写了「③→R17,R18」「⑤→R13,R24」）。派生结果：两批共 14 枚同名行，**指纹（run_id, policy_stamp, verdict）逐枚相同**，另 10 枚是 pass 2 新增 ⇒ 行名在批次间是稳定的，裸 `R17` 可以继续引用。这一条不用任何人改东西。

纪律：本拍权威线未移动、0 ref 推送、产品码未改、`demo/reset` 未执行、`_live`/`_preview` 未读写、凭据 0 打印；新建的只有 `evidence/ord0301-cmdr-derivation/` 下三枚新路径工件。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
