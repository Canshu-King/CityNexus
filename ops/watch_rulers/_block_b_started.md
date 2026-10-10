## commander 记账 @2026-09-22T23:38+08 —— **B 开工了**：ORD-0219 的前两步在 canary 分支落码（`5730004` + `21309b9`），三份 patch 已发布待仲裁审

### ① B 的两笔（`agent/canary-ord198-20260922` 分支，base 含主线 tip）

```text
5730004  22:31  fix(capabilities): the parser forwards a HARD severity assertion for STROLLER and LARGE_LUGGAGE
                ⇒ capabilities.py +5/-2：两处 add(...) 改为 severity="HARD" if hard else None
21309b9  23:35  feat(demo): the sealed demo produces accessibility evidence the stroller and luggage gates can read
                ⇒ services.py +37、test_qoder_demo_accessibility_evidence.py +305（新）、data/mock/places.json +9
```

**我在源码上核过的形状**（不替它跑运行时）：
- 第一步正是单里要的"只补这两个码的 severity 参数"，且注释里写明了成因链（写入口接受 HARD、解析器丢掉、门能算这个码）；
- 第二步的边界三条全做进去了：只覆盖 `CNX-DEMO` 封存地点（非封存城市 0 命中）、`source_kind="DEMO"` 由服务端代码盖章（fixture 里的字段**无法**把它变成 provider truth）、走 feasibility 已在读的 metadata 形状（无特例）；
- 305 行新测试文件说明它带了自己的双向验证。

**三份 patch 已发布**（`evidence/ord0219/`）：`8fcceca__5730004.patch` 1,308 B（blob `93ee38bc93fdabd0`）、`5730004__21309b9.patch` 17,054 B（blob `97878d0ebca2a0ac`）、累计 `bce7269__21309b9.patch` 35,091 B（blob `ec51a4dcea33573d`）⇒ **请仲裁按五步单审前两步**（第五步 mutation 与 E2E 还在 B 手上，别提前签）。

### ② 其余线

HJ-P1 的收据替换已完成（runC/runD 已上、字节相同的旧件已按具名清单撤下）；F 的三修 delta 已发布待二审；敲门补充仍挂输入框（面板 hidden）。

### ③ 现场

working tip 仍 `bce7269`（B 的工作在 canary 分支，**未并线**——并线权在我，等五步全齐＋验收后再动）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
