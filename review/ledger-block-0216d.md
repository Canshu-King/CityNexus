### 🪞 e345b9d6（SESSION=e345b9d6）ORD-0216 ④ 交付：封存演示入口不再替服务器说城市 ＋ 重启后的运行时亲测（含我自己那条门的 race，按新第 9/10 条报形制）@2026-09-22 18:3x +08 → 提交 **`3e259bd`**（产品）＋ **`522c414`**（门）

**报数六要素**：树 `D:/moodle/_qoder_integration_20260919`（有 .git）；`git log -1` = **`522c414 2026-09-22 18:32 +0800 test(frontend): the ORD-0193 running-state node waits for the state instead of racing it`**（其父 `3e259bd 18:27 fix(frontend): the sealed-demo entry stops naming a city the server never chose (ORD-0216 ④)`）；`git status --short -- frontend` **空**；解释器 = Node/Playwright ＋ `D:/moodle/CityNexus/.venv/Scripts/python.exe` = **3.12.14**（`sys.version` 实测；**更正我 16:2x 块里那句"`.venv` 3.12.14"**：本树根本没有 `.venv` 目录，run_spec.py 指的是 CityNexus 那个 venv——路径我当时没写全）；命令 `python review/run_spec.py "<十张 spec 的引号列表>" 4512|4516|4518|4520|4522 --config playwright.prod-gate.config.ts`，收集=执行=**42 节点**（1 real-seed ＋ 41）；执行读数见下；`git status --short` 另有两个**不是我的**脏文件我原样留着：`backend/tests/conftest.py`、`tools/verification/mutation_campaign.py`。

**④ 先量（`review/probe-ord0216-scene-city.py`，自有端口 :8731、自有临时库 `_ord0216scene181335.db`，不碰 `:4781/:4782/:8693`、不碰 `_live.db`、0 出网）**：

```text
seed 那趟（CN-TIANJIN）经 create→generate→select 后 active_plan_version_id 有值、status=ACTIVE
再建一趟 CN-GUANGZHOU（DRAFT，无 plan）→ GET /demo/scene 两次都回答天津那一趟
=> scene 选哪趟完全由数据决定（main.py:6331-6335：有 ACTIVE 方案的那趟，否则最近 seed 的那趟）
   收据 review/evidence/ui-overnight/ord0216-scene-city.json
```

⇒ 入口在服务器回答之前**无从知道**城市，所以任何写死的城市名都是一个未证声明。修法按你给的二选一取**第 1 条（文案城市无关）**：zh `使用封存的演示行程` / en `Use the sealed demo trip`。**不选第 2 条**（让入口显式选中天津那趟）：那等于让前端推翻服务器自己的选择——而 ORD-0209 刚把硬编码 UUID 去掉、规定 id 只从 `/demo/scene` 读；按城市去挑那趟要么新增寻址端点（后端），要么在前端二次猜。**也没改成"广州"**：读数已经说明广州那趟在当前规则下根本不会被选中，改了只是把不一致挪个地方。

**改了什么（三处渲染面）＋一条坦白**：入口按钮（活的，已证）、`discovery.genericCityLiveNote` 同族句（zh/en，「这个城市没有封存回放…」）；我把 prop 名 `onUseTianjinDemo` → `onUseSealedDemo`（`data-testid` 原样保留：那是门禁钩子不是屏上文字，改名会打断别的车道的引用）。**坦白**：`trial.title / trial.lede / trial.liveNote` 这三条我一开始也改了，随后量到它们在 `src/` 里**没有任何引用**（向导的标题/副标题走的是组件内 inline 串，截图读数里那句是「新建行程」）——即改动**不影响屏幕**，我保留它们（表里再留一句写死天津的话迟早被人当真相复制），但**不声称修好了三句**：真正上屏被改的是**入口按钮那一句**，而且只有它有渲染证据。

**门（新 `e2e/qoder-demo-entry-copy-matches-the-stage.spec.ts`）＝4 节点，全读 `innerText`，无 `data-*`**：
① `ord0216d-zh`：向导整屏渲染文字里 11 座城市的中英名字**一个都不许出现**（placeholder「例如：天津、东京、新加坡」不是 innerText，天然不算——它是输入示例，不是对封存演示的陈述）＋ 按钮仍要说清自己是什么（含「封存」「演示」），防止用删空来蒙过；② `ord0216d-en` 同形状；③ 落地臂：用产品 API **真建**一行 CN-GUANGZHOU 的 DRAFT 行程（不 generate/select ⇒ 舞台自己的 scene 不变，别的车道不受影响），**只把 `/demo/scene` 里 `journey_id` 这一枚指针**指向它（其余字段原样透传服务器答案），点入口后 `today-heading` 必须渲染出 **`广州之旅`**（城市由 `journey.city_code` 投影，不是我写的字），并且入口文案里出现过的城市名必须能在落地屏对上——**旧文案在这里必红**（说天津、落广州）。fixture 与产品真值的边界写在门名注释和收据 `ord0216-entry-copy-landing.json` 里。读数：`label="使用封存的演示行程"`、`named=[]`、`landingHeading="广州之旅"`。

**突变（`review/ord0082_0087_kill_drivers.py`，anchor hits=1、on_disk=True、跑完 restored OK）**：`killW1-entry-copy-names-a-city-zh`（`src/i18n/LocaleContext.tsx` zh 行改回「使用封存的天津演示」）→ `qoder-demo-entry-copy-matches-the-stage.spec.ts :: ord0216d-zh…` 由绿转红，原文 `the wizard screen names cities in traveller-visible copy (["天津"]); … Entry label: "使用封存的天津演示"` = **KILLED**；`killW2-…-en` 同形杀 `ord0216d-en…`，原文带 `["Tianjin"]` = **KILLED**。2/2，无 survivor。

**⚠ 我这条链里量到的一条红是**我自己的门**，按新第 9/10 条（跑法形制入收据）报**：`ord0193-starting-the-preparation-shows-the-servers-own-phase-and-no-invented-progress` 在**十文件链形制**下首跑 **RED**（`the job block reports status "QUEUED"`，`run-run072593.log`）；同一 SHA 单节点形制复跑 2/2 **GREEN**（`run-run072724`、`run-run072766`）⇒ 形制内 `FLIP_WITHOUT_SHARED_STATE`，不是恒红也不是"复现不出就算别人的"。根因是我自己的量具：作业块第一次上屏吃的是 **POST 自己**的答复（`DestinationPreparationPanel.tsx:116`，那时 `QUEUED` 是诚实的），而我的 route 只钉了轮询的 `GET` ⇒ 首画那一瞬读一次就会翻。修法 `522c414`：换有界 `expect.poll` 等 RUNNING 上屏（消息点名"没到来的东西"），**下面每条断言原样保留、0 放宽**；修后链形制 **3/3 GREEN**（`run-run072997`、`run-run073136`、`run-run073262`，各 **42 passed / exit 0**）。这条不是我今天才有的毛病，但它此前只在满载时才翻，所以以前那些绿是运气。

**运行时亲测（你 17:5x 说 `50b35e0` 还没做，我这轮全做了）**：十文件链（copy / demo-entry-addresses / wizard-city-copy / wizard-city-basis / wizard-speaks / wizard-blocked-a11y / reset-from-wizard / speaks-travellers-language / budget-advisory-tiers / destination-preparation）**42 节点**，522c414 之后连跑三把全绿；`tsc --noEmit -p tsconfig.check.json` exit **0** 两次（④改动后、门修复后）。

**现场读数（不是回忆，全部 18:3x 实测）**：D: 空闲 **18.15 GB**（16:4x 那波 0 字节已不是现状）；`:4781`(PID 40756) / `:4782`(48120) / `:8693`(21900) **三个端口现在都在监听**——你 17:5x 写的是"全部无监听"，我按读数报，**我一个都没动**；`GET :4781/` 200 且 `index.html` 引用的仍是 **`assets/index-BCF4ptyk.js`**（= `56d20ec` 那把包）⇒ **手机上今天这四件一件都看不见**：ORD-0216 ①②③（`50b35e0`）与 ④（`3e259bd`）都只在树上，没进部署。按你 16:4x 的 `DEPLOY_BUNDLE_RETENTION` 口径，换包（先 union → 再切 index → 再出 A–E 收据）是你的动作，我没有代做。**未 push**；未 `demo/reset`；0 次 provider 出网；账本只追加本块。

**移交与残留（不自己扩范围）**：① 若你要入口直接印出真实城市，需要 `/api/v1/demo/scene` 带目的地标签——那是后端字段，我没有在前端猜（新门③已经保证：城市只能从 `city_code` 投影）；② `RealCityDiscoveryPanel` 的内部标识 `supportsTianjinReplay` 与 `["CN-TIANJIN","TSN","CNX-DEMO"]` 白名单仍在（屏上文案已中性，代码命名归对应车道）；③ `killV1` 仍是 DOCUMENTED SURVIVOR，要一条能杀的突变需要 HJ-P1 原路（先卡后经跳转按钮回填）节点；④ ORD-0126 补项、ORD-0088①、ORD-0096 HELD 状态不变。

status: ORD-0216 ①②③（`50b35e0`）＋**④ DONE@2026-09-22T18:3x+08 by e345b9d6**（提交 `3e259bd` ＋ 门修复 `522c414`；四件齐）；本车道无待我确认项。
evidence: `review/probe-ord0216-scene-city.py`、`review/evidence/ui-overnight/ord0216-scene-city.json`、`ord0216-entry-copy-zh.json`＋`.png`、`ord0216-entry-copy-landing.json`＋`.png`、`frontend/e2e/qoder-demo-entry-copy-matches-the-stage.spec.ts`、`review/ord0082_0087_kill_drivers.py`（killW1/killW2）、`review/run-run072593.log`（形制 RED）/`run-run072724.log`/`run-run072766.log`（单节点 GREEN）/`run-run072997.log`/`run-run073136.log`/`run-run073262.log`（修后链 3×42 GREEN）、`review/chain-0216d-second.txt`、`review/tsc-0216d.txt`、`review/tsc-0216d2.txt`。**未 push**。
