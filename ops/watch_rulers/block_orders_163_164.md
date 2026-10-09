- id: ORD-0163
  to: 8ccd71d8
  priority: P0-critical
  if_head: d26933c
  order: |
    【全量红集合的分母要由你重定 —— 我手上"14 条基线"这句话已经不能当尺子用了】
    现状读数（lane C 21:3x 交 ORD-0125 时顺带量的，我按 tip `d26933c` 复算同意）：
    - `eef24d9` 上当时的 14 条红，有 **4 条**是后来 `94aee5d` 修断言时顺手改绿的；
    - 今天全量（两次独立跑一致）= **10 failed / 1083 passed / 15 skipped in 136.98 s**；
    - 那 10 条全在两个文件：`backend/tests/test_qoder_anywhere_gates.py`（5）与
      `backend/tests/test_qoder_anywhere_capability_from_store.py`（5），根因同一：
      **门没关外部 HTTP 端点**（Photon 真被打到，一次 1.13 s）。
    ⇒ 请你在 `d26933c` 上把基线**逐条 nodeid** 重钉一次（10 条，或你认为正确的那 N 条），
      并明确"新增红必须点名理由"这一条怎么判；然后**由你更新** ORD-0131 C 项与 ORD-0149 里
      "必须是 `eef24d9` 那 14 条子集"的原话（我这边先按"10 条 + 逐条点名"执行，你的新基线一到我立刻全线广播）。
    【硬门，别把门做松】不要为了数字好看去改这 10 条的断言、不许加 skip/xfail；
    正确修法是把**端点关掉**（测试内注入假 provider 或显式禁网），并把"门能感知 provider 在场"
    单独钉成一条突变（把 resolver 摘掉 ⇒ 门必须红 —— 今天这条**还不成立**，见 ORD-0156 里我给你的调用点级口径）。
    顺带：你 ORD-0149 已有提交 `9c9c0e6`（20:59，`agent/f-ord149-20260921`），我还没验；
    交付时请把"跑了哪个树/tip、红集合原文"贴在块首，我按子集口径复算。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7

- id: ORD-0164
  to: e345b9d6
  priority: high
  if_head: d26933c
  order: |
    【并入 ORD-0126 的一个现成复现样本（我 21:30 在验收包里量到的，不是转述）】
    `GET /api/v1/journeys/ca0f1ed1-485a-4d65-8c19-0087ce5e29fd/experience → **404**`，
    而该 id 在 `_live.db` 里**不存在**（库里只有 `22222222…` ACTIVE CNX-DEMO / `6cbdbc65…` PLANNED CN-BEIJING / `94669bae…` DRAFT CN-BEIJING），
    页面**既不恢复也不引导**——就是你报过的"reset 后 journey 404 刷屏"同一族，现在有最小样本了。
    要做（都算 ORD-0126 的 (a)(b)(c)，别再开新单）：
    ① 屏幕上的**诚实恢复态**：存的行程 404 ⇒ 明确告诉用户"这趟行程已经不在了"+ 给出屏幕上真实存在的下一步（列表/新建），
       **不许**静默回落到演示那趟，也不许把 404 说成网络问题；
    ② 存储侧**自洁**：读到 404 就清掉本地存的 journey id（否则刷新继续撞），并给一条门断言这一行为；
    ③ 门禁：两条先红后绿 —— (甲) 拿一个不存在的 id 打开页面 ⇒ 现在红（刷屏/哑屏），修后必须是具名恢复态；
       (乙) 清 id 后刷新 ⇒ 不得再次撞 404。突变：把"清掉失效 id"那一步摘掉必须判红。
    我给你的现场指针（我自己量的，你可以直接接着用）：`JourneyInboxWorkbench.tsx:441`
    `decision = draft?.smart_intake?.decision ?? "NEEDS_REVIEW"`、`:450` 只在 `AUTO_APPLY|APPLY_WITH_NOTICE` 放行、
    `:242` 注释说走同一条 preview→confirm；`V8Experience.tsx` 有**两处挂载**（`:1479`、`:1713`）⇒ 两条路都要走一遍，别只验一处。
    另两条提醒：
    - **ORD-0146① 的验收我不改**：lane C 说服务端的 `REVIEW_NOT_ENABLED` 分支"不可达"，我**没能复现**该说法
      （HEAD `d26933c` 的 `V8Experience.tsx` 里 `REVIEW_NOT_ENABLED` **0 命中**，全仓也没有审核/提升为承诺的后端路由）。
      仍按你原计划：**用你 `:85xx` 台跑 OPTIONS/405/404 判定**，量出来再决定走 ①（真入口）还是 ②（诚实文案 + 屏幕上真存在的下一步）。
    - 用户预览 21:29 已换到我自建的 `index-BVbc7LUF.js`（含你的 `4176e7b` 单指拖图）。
      真机复验请在**换包后的这一版**上做，并在报告里写 bundle 文件名；旧包备份在 `dist_bak_2129`。
    - `manifest.webmanifest → 401` 我在**本机 `:4782`** 上量到 2 条（派生 cookie 不覆盖该子资源），
      **隧道侧未量** ⇒ 别把它当已确认缺陷；你或 E 在手机上复验一次再立单。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7（并入 ORD-0126，不另计一单）

- id: ORD-0165
  to: aad2d1f2
  priority: high
  if_head: d26933c
  order: |
    【手机口径复验：预览已换到我自建的 `index-BVbc7LUF.js`（21:29），请只验三件事，别再扩面】
    这版含两笔你今天骂过的修复：`4176e7b` 地图手势所有权（单指拖图）、`2d3b3fb` AI 卡尺寸与页脚。
    验收要**你当用户走真机流程**，不是读 API：
    ① **单指拖地图**（390×844 + hasTouch，生产包）：手指落在地图画布上拖 ⇒ 地图平移、页面不滚；
       手指落在地图以外的正文上拖 ⇒ 页面滚、地图不动。两条都要**读数**（`lat/lng` 前后值 + `documentElement.scrollTop` 前后值），
       并且要说清**手指是否落在文字叠层上**（那三个叠层现在是 `pointer-events:none`，落在字上也算落在地图上，别误判成"没修"）。
    ② **AI 规划那张卡片**：手机上打开 ⇒ 卡片顶部可见、底部按钮不跟着滚走、里面"举例地点"是按名字排的（不是读数据顺序）。
       断言只读**渲染出来的文字**，不许读 `data-*` 属性。
    ③ **你上轮报的两条仍要复验有没有好**：`TRUTH_DEFECT`（AI 把我的预算当 0）与 `HUMAN_STATE_LOSS`（创建成功后草稿不清除，刷新落回第 3 步）。
       没好就照原样再报一次读数，**别为了好看改口**；预算那条 lane C 正在按 ORD-0158 查，你只出屏幕证据。
    【必带的分母】bundle 文件名（`index-BVbc7LUF.js`）、tip、你用的设备/视口/UA、库（只能是你自己的副本）、端口、解释器版本。
    【禁令】不碰 `:4781/:4782/:8693` 与 `_qoder_cmdr_gate_20260921\backend\_live.db`（用户此刻在用）——
    手机预览的**只读**浏览可以（它就是给手机看的），但**不许**在里面做写实验；全线禁 `demo/reset`（R13，我在 `:4782` 装了 403 护栏，别绕）；
    不新开第二个隧道（隧道只有 `:4782` 这一条）；不许动 `CityNexus\**` 与权威树；不对 github.com 用 git 网络操作；不调真 AI provider、不读凭据值。
    交付写进 `## DELIVERIES`：只追加你自己那块，`io.open(..., newline="\n")`，并附"把我的块拿掉必须逐字节还原前一份文件"的回读证明
    （这文件今天被整体重写成 CRLF 三次，插之前重测锚点）。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7（预览换包后的定点复验，三件事做完就交）
