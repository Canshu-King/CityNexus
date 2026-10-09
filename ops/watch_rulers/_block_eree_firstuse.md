## commander 记账 @2026-09-22T19:06+08 —— 新规第一次实战：HJ-P1 申报坐标并**发现比"没 push"更深一层**（这条集成线的 origin 本身是本地路径）；我代它发布三份证据

### ① HJ-P1 按 `EXTERNALLY_READABLE_EVIDENCE` 申报，并且比我们昨天那条更狠

它写（我照录，不加工）：

```text
git branch -r --contains 522c414 => 0 条 ;  25165d9 => 0 条
git remote -v => origin = D:/moodle/CityNexus, iso = D:/moodle/_qoder_th_20260918   ← 都是本地目录
⇒ LOCAL-ONLY, no resolvable coordinate。
   而且比"没 push"更糟一层：这条集成线的 origin/iso 本身就是本地路径，
   所以 refs/remotes/* 里永远不可能出现 GitHub 可解析的引用。
```

**我核过这句话**：`git remote -v` 在这个树里确实只指向本地目录（`D:/moodle/CityNexus` 与 `_qoder_th_20260918`），没有 GitHub remote。
⇒ **这条发现比"我们忘了 push"更根本**：即使车道想 push 也没地方 push；**外部可读坐标只能由我经 contents API 发布**。
这条我记进账本，并说明**它不是我发明的补救、而是这条线的结构**——所以 `publish_evidence.py` 不是"锦上添花"，是**唯一通路**。

### ② 它请求代发的三样，我已发（它只读，不 push）

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/hjp1_0220
  delivery_block_1902.md            2,830 B  blob 7594b01f1ba7cb8c
  o219-stale-hint-step3.png       110,410 B  blob a1084e68ef22ff97
  o219-hint-scrolled.png           70,891 B  blob 0f5b20434d95c354
```

**两张截图我自己看了**（不是只听它说）：`o219-hint-scrolled.png` 显示手动滚动后「还需要填写：总预算」确实进入视口、`下一步` 就在下方；`o219-stale-hint-step3.png` 显示第 3 步确认屏（目的地 成都 / 人数 1·1 / 总预算 450 / 节奏 轻松·我们替你填的 / 兴趣 —），**屏上没有那句残留提示**——与它"可见实例数 0、只有 `.v8-sr-only` 里还有"的读数一致。

### ③ 它这轮的两格读数（我按它的数记账，不重复开枪）

| 格 | 结果 | 累计 |
|---|---|---|
| **ORD-0220 ③** 被拦时提示渲染在折叠外（`y=1221` vs 视口 844、sticky 按钮 `y=652`、`scrollY=0`、产品不滚不聚焦） | **仍在，2/2** | **4/4**（与 `50b35e0` 同型） |
| **ORD-0220 ②** `sr-only` live region 不随修正重算（字段改好后读屏节点仍写「还需要填写：总预算」） | **仍在，2/2** | 2/2 |

它按第 9/10 条自己钉了形制：**pass 2 之前先 `localStorage.removeItem('citynexus.v8.trial_draft.step')` 再 reload**，两遍不是同一份草稿状态；两遍都是"重载 → 进向导 → 回第 2 步 → 总预算写 0 → 被拦 → 改成有效值 → 进第 3 步"，各一次独立页面会话。
**它给 D 的两条断言可直接抄**（都不依赖 `innerText`；它特意避开 `toHaveCount(0)`——那条本车道记过会挂）：① 被拦瞬间 `hint.boundingBox().y + height <= innerHeight`；② 改成有效值后 `.v8-sr-only` 里该句计数为 0。

### ④ 现场

working tip `25165d9`；链**鉴权 health 200 / 首页 200（bundle `index-BCF4ptyk.js`）**（我 19:04 走隧道实测，不用 401 证 upstream）；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
**一件我评估后决定不做的事**：tip 比线上新 3 笔（含 `3e259bd` 文案修复），但 `53fe8e8..25165d9` 的 backend 差集是 **29 个文件** ⇒ 全量部署必须重启后端、会有中断；而用户能感觉到的那条（主页那句废话）**已经在线上了**。所以我不做这次高风险换包，**等 ORD-0222 落地后与前端一起换**，避免两次中断。
