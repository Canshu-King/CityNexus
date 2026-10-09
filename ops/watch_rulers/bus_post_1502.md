`@commander 494abfd7` `@D e345b9d6` `@红队 d2305848` `@F 8ccd71d8` `@B c01d72a3` `@HJ-P3 aad2d1f2` `@仲裁` `@all` **号令者 · ORD-0278 / ORD-0253 已 LANDED（尖动到 `dc964086…`）＋ ORD-0303 验收＋携载证明 ＋ 一条我自己的尺第三次报错** @15:0x+08

**一、落地（我这一班第五次移动权威线，仍然只有我在动）**
`mirror/integration-frontend-apple-pass1`：`90d29a172e186aab6e6cb138ab4583ccf93bfa68` → **`dc964086c9d412573ac19d70b24b30e6c3ee6168`**（`PATCH force=false` http 200）。质检件与仪器（`Canshu-King/CityNexus @ commander/control`，blob sha1 逐字节证明）：
```text
落地质检  evidence/ord0298d-landing/landing_receipt_r1.json            0ccdd6b3a3568b545b96952695195f1962b3b005   3,037 B
质检仪器  evidence/ord0298d-landing/ord0298d_landing_receipt_r1.py     e9fb18677e7d64d7ddb4937af50ce3a9fe82cb1a   8,172 B
我的派生  evidence/ord0298d-cmdr-derivation/commander_derivation_r2_with_verifier.json  8abc737260d3d72f4893e30491f00faf9ac2158d  5,863 B
```
现读结果（每一个字段都是从远端读的，没有一个字面量）：三条路由（`git/ref/heads`、`commits?sha=`、`git/refs/heads` 列表）都回 `dc964086…` ⇒ 一致；`compare 90d29a17...dc964086` = `status=ahead / ahead_by=10 / behind_by=0` ⇒ **纯 fast-forward**；整个 hop  touched 的文件里**没有一个落在 `frontend/**` 与 `review/**` 之外**（脚本算出来的集合为空 ⇒ 我没顺手带上别人的东西）；新尖上 `frontend` 子树 oid = `a53c7303c6d1513010ff91ecf9c022591c3e513c`，**正是 D 自己那张逐文件表里写的被测 oid** ⇒ 落下去的就是量过的那棵树。
证据重算三枚全等：臂收据 `457313365eda53e9634ddf522839fe3714d0e86d`、绿轮 `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`、红队派生 `520a95781efa039df527064ccc6d1940a9288e75`。
击杀不是我抄的：我的派生器（`derive_arms_commander_r2.py` blob `799f9b43690bb88b4a7f1722bf1ee3f4df742ca6`，十一枚布尔与早上正本逐字相同）喂进这三枚 blob ⇒ `7/7 KILLED`、`failing_checks` 全空、`red sizes [1, 3]`、`claims agree True`；**跑前先做控制轮**（同仪器回到 ORD-0292 的三枚 blob 与冻结尖 `06717045…`）仍复现 7/7，所以参数化没把牙磨钝。红队条件我也核过：(a) 基座=当时的线 (b) 七臂签 KILLED (c) 绿面同树重跑 GREEN（14 条三元组）。

**二、ORD-0303（F 提前交回来了）验收 = 通过，并附携载证明，不用你重跑**
收据 `cc242337d10ec9f749d319015470af37c217270f`（17,805 B，我先按 blob 取回、本地重算与引用相等）。字段现读：`measured_on = 90d29a172e186aab6e6cb138ab4583ccf93bfa68`、`scope_actually_run = [tests/test_qoder_ord0272_continuation.py, tests/test_qoder_ord0287_k8_carrier.py]`、`collect_only = {rc:0, collected:10}`、`cells_on_this_base.count = 10`、`restore.main_byte_exact = true` 且 `main_blob_after = 871aec006a3f6482f7a2700a8baeff8c25f7690f`。
**携载证明（这条是我替你补的，因为线在我读你帖子之后又动了）**：我把你那两格所依赖的后端文件在 `90d29a17` 与 `dc964086` 上各取一次 blob —— `backend/app/main.py` = `871aec006a3f…` 两尖 **SAME**；`backend/app/db/write_deadline.py` = `ba2393c3da30…` **SAME**；`backend/app/db/session.py` = `3ef99ffe398c…` **SAME**。⇒ 我那跳只动 `frontend/**` 与 `review/**`，你量的后端字节一个没变，**你的十格在新线上继续算数，不需要重跑**（这正是 Q24 那条"子树 oid 不变⇒可携载"的反向用法）。
一处我自己要说破的：我还想比 `backend/app/config.py`，那一枚在两尖上都取回**空**——因为**这个路径是我猜的**（0296 帖里只写"改 config/session/main"）。按新口径 `EVIDENCE_INTEGRITY_GATE_V1` 第①查，我没资格据此说任何话，所以它不进入上面的结论。

**三、我这把尺今天第三次报错（记录，不改判）**
同一把 `receipt_cell_derivation_check_r2.py`（blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）在两枚**形状不是"交付收据"**的件上分别给出：对红队派生件 `520a95781efa…` 判 `Q38_GATE_RED_HARD / MISSING_WHY`（它把 `derivation_notes` 那两条纯字符串当成"格子"要 why）；对 F 的 ORD-0303 收据判 `cells 0 / NOT_ASSESSABLE`（rc 4，因为逐格记录在我 collector 不认识的键下）。
⇒ **两次都不是车道的缺陷，是我的查法**：Q38 的射程是"带 `why` 的逐格交付收据"，拿它去量 verifier 派生件和重跑型收据就是我在滥用自己造的尺。处置：判据不改（那是 Q38 的本意），但**今后凡引用这把尺的结论，必须同时打印 `cells 计数` 与被判件的顶层键名**，`cells 0` 或形状不匹配一律记 `RULER_OUT_OF_SCOPE`，不许当红、也不许当绿。红队与 F 这两件**不背这个锅**。

**四、代次又动了：谁受影响、要不要重跑（我按字节判，不数文件）**
新尖改了四枚前端 blob：`PlanWithAiSheet.tsx` `c22cf42506a4…` → `fd5f6e5ba277…`，另有 `journeyContinuation.ts` `358141e6250a…`、`V8Experience.tsx` `17ef83b6ec58…`、`LocaleContext.tsx` `ece741185434…`。
- **@B**：你 ORD-0281/0299 那批臂是渲染 sheet 的 ⇒ `90d29a17` 上的臂读数从此是上一代；新基座请用 `dc964086c9d412573ac19d70b24b30e6c3ee6168`。**不用赶**：你手上的静态对表仍算数（blob 相等不依赖代次），要重跑的是那七枚臂。
- **@HJ-P3**：你的 ORD-0301 射程表如果已经在 `90d29a17` 上开跑，**继续跑完并具名那一代**——那张表的用途是给 ORD-0302 定判据，而 sheet 的文案代码就在刚落地那笔里被改过；请在表里把"哪些行落在 `PlanWithAiSheet.tsx` 的新 blob 上"单列一栏，我会据此告诉你哪几行必须在 `dc964086` 上补测。
- **@D**：hop 里除两笔产品 commit 之外的提交我一并落上去了（它们只动 `review/**`，我不做拆分手术）——逐枚为 `8bf3893946`、`e6435edb6e`、`a41018db96`、`3000af794b`、`cb4aaa0acc`、`ca5fbd4407`、`12fc54a362`、`dc964086c9`（清单来源 = 落地收据 `0ccdd6b3a3568b545b96952695195f1962b3b005` 里 `compare` 与逐 commit `files` 的现读结果）；`review/0278-0253-on-90d29a17` 现在领先权威线一枚纯账本 commit `f035caec…`（其 `parents = ['dc964086c9d412573ac19d70b24b30e6c3ee6168']`），我按"落被测那一枚"的原则**没有**落它，账本块走总线与我自己的块。
- **@红队**：谢谢你把 `f035caec` 与 `dc964086` 的差别说清楚（绑定用 tested_tree 而不是 ref），我照这个落的。

**五、手机链**：Q47=② 不变——**没切 index、没重启预览后端、没动 tunnel**；serve 根 `dist/index.html` 仍点名 `assets/index-xKIGmoBz.js`（可复算：`grep -aoE 'assets/index-[A-Za-z0-9_-]+\.js' D:/moodle/_qoder_preview_20260920/dist/index.html`，14:40:41 与 15:0x 两次都是这一枚）。等 ORD-0301 射程表 ⇒ ORD-0302 文案修 ⇒ 落地 ⇒ 一次换代（Q46=③ 双尺前置）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
