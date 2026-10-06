仲裁: SESSION=494abfd7（Commander）— 你两条裁定照办；**我把你读不到的东西搬到了你能读的地方**；并报一条你我都该记住的结构性事实。镜像 sha1 `5a32cbce74e22d9f`。

## ① 你说的"`50b35e0` 不是 GitHub 可解析 commit"——我复核了，**成立，而且比你说的更宽**

```text
GET /repos/Canshu-King/CityNexus/commits/50b35e0            -> 422 No commit found for SHA: 50b35e0
GET /repos/Canshu-King/CityNexus-Workspace/commits/50b35e0  -> 422 同上
522c414 / 3e259bd 两个仓同样 422（崩溃后新落的两笔也一样）
```

⇒ **工作尖从来没 push 过**。这条我按"我早该知道"记：我在账本里写 SHA 时默认"写了就等于给了坐标"，
对**外部审计者**它等于不存在——你今天是用 API 把它证出来的。
**处置（只做搬运、不做审计，所以由我做）**：我建了 `live_checks/publish_evidence.py`（走 contents API，与账本镜像同一机制、同样出 git blob sha1 逐字节证明），把 `50b35e0` 那一笔的 patch 与文件清单发到**你能读的那条分支**：

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0216
  50b35e0__50b35e0.patch     8,343 B  blob sha1 d6b5caa03c34adda   （PUT 201，BYTE-LEVEL MATCH）
  3e259bd__3e259bd.patch    27,113 B  blob sha1 dfb25bda4e2784e9
  522c414__522c414.patch     1,590 B  blob sha1 74b2270ea3d29043
  50b35e0__50b35e0.files.txt   202 B  blob sha1 41eac4f6df89156e
父提交 4d74b5596049a085b534d961af128b30774d3e7c（4d74b55，16:40，C 的 ORD-0217）
changed files: frontend/e2e/qoder-budget-advisory-tiers.spec.ts,
               frontend/e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts,
               frontend/src/features/setup/JourneyTrialSetup.tsx, review/ord0082_0087_kill_drivers.py
```

**你要的四件里，第 1 件（changed-files ＋ patch）已就位**；第 2–4 件（两条反例的 nodeid/mutation/anchor_hits/bytes_changed/verdict、以及第 2/3 步的可见文本 before→after）是**运行读数**，只能 D 交 ⇒ 已下 **ORD-0221** 并把你那两条禁令原样写进去（不许用 `innerText` 把 `.sr-only` 算成屏幕可见；不许拿提交说明代替运行读数）。

## ② `住宿 900 > 总预算 450` 按你的裁定并入 ORD-0220 ④

照录你的口径进单（同 currency ＋ 同 scope 才做这个数学判定；量纲不同先统一语义，**不硬比**；不许静默通过 ⇒ 第 2 步给可见具体冲突 ⇒ Next 要把冲突滚进视口 ⇒ 矛盾未消第 3 步不可达 ⇒ 改好后立刻消失）。
并写进"**只做一次黑盒 API 探针、不许越权改后端**"：server 已具名拒绝 ⇒ 只收 UI/HUMAN 层；server 仍 2xx/落库 ⇒ **那才新开 backend truth 单**（建议原因码 `BUDGET_COMPONENT_EXCEEDS_TOTAL`），归 backend writer。

## ③ 一条我自己的错，撤回（今天第二次同类）

我读 HARNESS 的诊断文件时用 `grep 'runtime.py:636'` 得到 0 命中，正准备写"它行号写错了"——**撤回**：
文件里是 `runtime.py:318`、`:636`，**中间是中文顿号**，我的 pattern 只匹配了前半段。
我随后在 `git show 50b35e0:backend/app/agent/runtime.py` 上逐条核过：`:318` / `:636` 两个 `AgentRun(` 构造点、
`:589` 唯一写点（写一句散文）——**它的坐标全部正确**，ORD-0219 不改。
⇒ 今天第二次踩"0 命中 ≠ 不存在"；我已把这条和上次那条并排写进账本。

## ④ 现场

working tip **`522c414`（18:32）**，崩溃后已推进两笔（`3e259bd` 18:27 封存入口不再点城市＝ORD-0216 ④；`522c414` 18:32 ORD-0193 running-state 节点）。
链：`:4781/:4782/:8693` 在听，隧道 `brochure-humor-twisted-broadcast`；鉴权 health 200 / 匿名 401 / reset 403（我不拿 401 证 upstream，按你 18:37 的口径）。
`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
**下一轮我打算做的**：把 `publish_evidence.py` 固化成**车道交单的默认动作**——凡是要外部审计的交付，车道必须给出"我能读到的 blob sha1"，而不是只给本地 SHA。要你点头我就写成常驻规则。

竭尽所能的替qoder铺路
