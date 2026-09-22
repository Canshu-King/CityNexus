### 🔬 e345b9d6（SESSION=e345b9d6）ORD-0222 追加两条硬要求：① 瞬时滚动早已落码（`c4a4001`）；② 那条 3/3 我量到的是**部署代次**问题，不是守卫失效——并补了一条"创建成功之后"的门（`fbbc21d`）@2026-09-22 20:5x +08

**① `behavior:"smooth"` → 瞬时：已完成，就在你这条追加之前**。提交 **`c4a4001`**（20:40）把 `JourneyTrialSetup.tsx` 的 `revealReason()` 改成 `hint.scrollIntoView({ block: "center" })`，门的等待界从 4s 收到 1.5s 并注明"这是守卫不是动画计时器"，`killZ1` 锚同步改到新行。读数（`review/ord0220-instant.txt`）：`qoder-wizard-hint-surface-readings.spec.ts` **5 passed / exit 0**；`killZ1` **KILLED**（`anchor_hits=1`、`anchor_bytes=46`、`bytes_changed=+27`、`restored OK`）；`tsc` exit 0（`review/tsc-0220f.txt`）。⇒ 这条现在**可测**了；真机有头读数我仍然没有，那一格不签。

**② "live region 仍未按值重算（3/3）"——我按你的分寸办：不猜原因，先去下断点，结果量到的是代次。** 判别读数（不碰 `:4781` 的进程，只 GET 它正在服务的字节）：

```text
GET :4781/            -> index.html 引用 assets/index-BCF4ptyk.js（1,230,082 B）
GET 该 bundle 扫标记：
   「使用封存的天津演示」  1 次   ← 这句在 18:27 的 `3e259bd` 就被换成「使用封存的演示行程」
   「使用封存的演示行程」  0 次
   「未识别的出行方式」    0 次   ← 20:10 的 `f7ce8ff` 才有
   「每人每天约」          1 次   ← 主页 tight 档（56d20ec 代）在
```

⇒ 手机上正在跑的这把包**早于 18:27**，而 `spokenKey` 守卫是 **19:37 的 `dfdc5d5`** 才进源码的。**HJ-P1 三次读到的那句陈旧播报，来自一把没有这把守卫的包**——不是守卫在真树上失效。所以：`REPRODUCED(tree)` 我签，`FIXED(phone)` 我**不签**，因为那一代还没部署（换包按你 16:4x 的 `DEPLOY_BUNDLE_RETENTION` 顺序做，我不代做）。

**同一棵树上的正向读数**（authoritative 链，`run-run081697.log` **6 passed / exit 0**）：`ord0220-2-the-announcement-retires-when-the-field-is-fixed` —— 强制按下被拦的 下一步 ⇒ `#trial-next-reason` 写入「还需要填写：总预算」（1×1、`insideSrOnly=true`）⇒ 把预算改成 1500 ⇒ 该句**退休** ⇒ 进第 3 步仍不含该字段。

**我补的一条你我都还没量的路径**（HJ-P1 的原话是"创建成功后仍会听到"，我原来的门只走到第 3 步）：新节点 `ord0222-6-the-announcement-is-still-gone-after-the-trip-exists`（提交 **`fbbc21d`** 20:55）——拦下→播报→改值→进第 3 步→**真的点创建并等到行程出现**，然后读那个区域：

```text
today-heading = 「天津之旅」          ← 行程确实存在
#trial-next-reason  exists=false  text=""
```

⇒ 创建成功后**没有陈旧句子可播**，但我要把话说准：它不存在是因为**向导整块卸载**（区域随宿主一起没了），不是因为守卫在那一刻主动清了。两种情况对用户结果相同，但机制不同，所以我把它写成读数而不是"我修好了"。

**现场**：未碰 `:4781/:4782/:8693` 的进程（只对其产物做只读 GET）；未碰 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；产品分支仍 0 次 push（`c4a4001`/`fbbc21d` 的 SHA 在两仓 422，要可读我再走一次 `publish_evidence.py`，你说一声即可）；账本只追加本块。

status: ORD-0222 追加两条 —— **① DONE**（`c4a4001`，门可几何咬住、突变仍杀）；**② 已定界**：真树上守卫有效（6/6）＋手机侧读到的是 18:27 之前的包 ⇒ 待部署后由 HJ-P1 重读，我不提前签。
evidence: `review/ord0220-instant.txt`、`review/run-run081697.log`、`review/evidence/ui-overnight/ord0222-after-create.json`、`review/served-bundle-markers.txt`（代次标记计数）、`review/tsc-0220f.txt`、`review/tsc-0222e.txt`、提交 `c4a4001` + `fbbc21d`。
