## 今天这一代手机上真人走过：旧两件逐字重测（与上一代像素同一）、ORD-0357 用了一次真链接、三件新缺陷带接口与字节 · HJ-P3 aad2d1f2

四元组：**scope** = 死 stored journey id 那一屏、「已保存」这类话背后的设备行、ORD-0357 复制行程链接后在干净设备重开、以及新缺陷；**generation** = 链上两入口此刻都点名 `/assets/index-D3j0mgvR.js`（1276676 B，sha256 前缀 `acfd43158bcaa41a…`，与你给的包名一致 = True；镜子 ref 此刻 = 6ee21eddba60303e8f0f46907df9501ee0149e6e；这枚包由哪一笔切出我不证，换代归你）；**artifact** = 末段那几条 40 位；**method** = own Chromium 390×844@3 touch zh-CN 走公网入口，每格一个全新上下文，本车道这一代一共起车 6 次 ⇒ 我**不**对底图/瓦片下结论。

**旧事两件，逐字重测**：
· 死 id 那一屏仍然具名说「不存在」= True，屏上文本与上一代逐字相同 = True，两张截图（不开与开了折叠）也与上一代同一枚 sha256 = True / True（见证件）；拒收后 id 被清 = True。屏上那句话原文我抄进了块里。
· 服务器那条腿 GET `…/experience` 答 状态 404、正文 235 B，字段 `error.code=NOT_FOUND`、`error_receipt_id=CNX-FM7GYKRT`；屏上（不开与开了）CNX 号仍然 0 枚 = True，而且这枚号与上一代同一路线读到的是同一枚。
· 「已保存」那一件：设备里 `citynexus-offline/journeys` 行数 = 1、workbox 条目 8 条 = True；我走的五屏（今天/我的/行程/预订/行程工作台）没有一句含「已保存」= True —— 这是「这五屏没渲染」，不是「这句话不存在」，其余屏我没到过。

**ORD-0357 我当真用了一次（这是验收，不是审查）**：控件在 `/v8/trips` 的「预订」子页之后，`data-testid=journey-link-copy`、`data-cnx-field=journey_link_url`、文本「复制行程链接」、距顶 315 px、未禁用且在视口内；按下 → 剪贴板拿到 `https://jets-saints-tomatoes-eric.trycloudflare.com/v8/fa5cebdc-fabc-4067-ab02-4812ddb950e5`，屏上那句逐字 = `行程链接已复制到这台设备的剪贴板，可以发给同行的人。`；一台没见过的设备打开这条链接 → 落点行程首页、`citynexus.v8.journey_id` 就是我创建那趟 = True，屏上出现行程标题「天津之旅」。一格如实分野：重开后的屏与按下复制那块面板文本不同 = True（269 vs 605 字）—— 产品主张是「同一趟行程」，这条成立；「同一块面板」不是它的承诺。

**三件新的（一步可重现，带接口与字节，你可直接开单）**：
· 缺陷一 · 底栏「行程」把有候选方案的行程说成没得看：落地屏 134 字，写着「还没有可看的行程」与「这个行程还没有选定的方案」；同一趟行程在首页渲染了 2 天逐日预览并明写「以下只是其中一个候选方案的预览，你还没有采用它」。接口：`GET /api/v1/journeys/<id>/plans` 200 / 2 B、`GET /api/v1/journeys/<id>/experience` 200 / 132102 B、`GET /api/v1/places?city_code=CN-TIANJIN` 200 / 2 B。
· 缺陷二 · 屏上把用户指向运维已关掉的路：`/api/v1/health` 200 / 113 B 里 `ai=disabled`、`ai_state=DISABLED_BY_OPS`，而「AI 帮我规划」未禁用、按下开出的 sheet 里写 `这台服务已接入 AI 模型。` 并给「开始规划」；我**没有**按它（更长流程与开关不归我试穿）。该按钮发了 `GET /api/v1/agent/runtime-status` 200 / 408 B。
· 缺陷三 · 手机上到那枚复制控件要 2 跳：顶 0 px 那组（桌面侧栏）含今天、实时行程、地图、行程工作台、住宿选择、城市探索…，移动底栏只有 今天、行程、地图、Copilot、我的 五枚；标签「旅行票夹」用 DOM 文本命中 1、用 role 命中 0（即那份入口在 390 宽不可达）。

**我自己这一代记 4 笔仪器错**（含两趟未命中的探索，件都按新名交了）：把「控件不存在」报错过一次（真因是子页没点到）、把 role 命不中当成读屏命名缺口一次（真因是桌面侧栏不可达）、页面里调 Node 助手一次、把代理挡路当成入口没起来一次。

坐标：评分件 `evidence/hjp3-d3j0mgvR-walk-0926/r7_scored.json` 066df562dcee4018d093a2ac2982b80b012cbc65；入口与包身份 `evidence/hjp3-d3j0mgvR-walk-0926/r7_entry_check.json` 4d6f3309652a8d38ccc1dbc7a0e0094589a16197；四格走路 `evidence/hjp3-d3j0mgvR-walk-0926/r7_walk.json` 2f551d741212b6b9af85a01fadaf8c699b049233；验收 `evidence/hjp3-d3j0mgvR-walk-0926/r7_copy_link_r4.json` 5658664006ec72393d0563ca083af56a81ac073c；AI 引导 `evidence/hjp3-d3j0mgvR-walk-0926/r7_ai_disabled.json` 6fb18d62a2c7570619b251e9d8b65ef1eec63168；跨代像素同一 `evidence/hjp3-d3j0mgvR-walk-0926/r7_pixel_identity_with_previous.json` b5468ddd79d5da9c391ae6903761426872c913a5；块 aad2d1f2_1900.md（13289 B，门 claims 16 / findings 0，rc 0），回执随后按新名上架。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
