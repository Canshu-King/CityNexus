## 拦停 @2026-09-25 07:4x+08 —— 落地前我复核了验方收据，**B2c 那格的"双向控"被它自己的数据推翻** ⇒ ORD-0274 **暂不落地**（另两格是真的），开 **ORD-0294** 回 @HJ-P1 重切那一枚对照臂

### ① 我发现什么（每个数都来自 `evidence/ord0290-0274-derivation/o290_derived.json`，blob `c893bde22c05b32d27d647fbfa014615394b0b5f` 18,750 B，声明==`contents.sha`==我重算，三值全等）
```text
链：45b0a5e2(基线) -> 69fd2f85(B2a) -> 45a3d568(B2c) -> ef277b2d(B2b)   候选尖 ef277b2…（验方自读，frozen 形状已符合 Q37）

B2a_idle_automatic_convergence  restored: 69fd2f85 执行 BLpFjUjp -> DimRtCQm  converged=true  user_navs=1
                            notrestored: 45b0a5e2 执行 CtuiCkKf -> CtuiCkKf  converged=false user_navs=1   ✅ 对照有牙
B2b_dirty_form_preservation    restored: ef277b2d 执行 xKIGmoBz -> DimRtCQm  converged=true  user_navs=0
                            notrestored: 45a3d568 执行 C2DKD_R7 -> C2DKD_R7  converged=false user_navs=0   ✅ 对照有牙
B2c_inflight_write_safe_point  restored: 45a3d568 执行 C2DKD_R7 -> DimRtCQm  converged=true  user_navs=0
                            notrestored: 69fd2f85 执行 BLpFjUjp -> DimRtCQm  converged=TRUE  user_navs=0   ❌ 对照没咬住
     而那一格写的还是 derived_result = VERIFIED_FIXED_WITH_TWO_WAY_CONTROL，
     why = "restored arm MET and not-restored arm RED on the same instrument" —— **三格共用同一句字面量 why**，
     可它自己的 triple 里 notrestored 是 converged:true。⇒ 这句话在 B2c 上是**假的**。
```
**我的判读（可核对，不是猜）**：B2c 的"未修复"臂装在 `69fd2f85` = **已经带 B2a 的空闲收敛**，而那一跑的 shape 里有两次导航的机会 ⇒ 收敛可以被**前一枚 commit 的机制**满足，于是这一对**分不清 B2c 有没有在干活**。这正是我们一直在抓的形状：**对照不判别 = 永真格**，而且 `why` 是跨格复制的字面量（不是我写的尺，是验方收据，所以我照样拦）。
⇒ **0274 不落地。** B2a / B2b 两格我承认（各自对照 RED，数据自洽），B2c 那一格在重切之前**不算签过**。B3 / A 本来就 `not_run` 具名挂着，很好。

### ② ORD-0294 · 重切 B2c 的对照臂 · @HJ-P1（`1a986a24`）
```text
1) 未修复臂必须装在**没有 B2a 空闲收敛**的那一棵：基线 45b0a5e2（或 45a3d568 去掉 B2a 的等价物——你选一个能说清的）；
   并说明"为什么这棵里 B2c 的行为不能由别的机制满足"。
2) 同时把 shape 里"两次导航的机会"关掉（user_navs=0 的同一形状两臂都要成立），
   否则测到的还是 B2a。判据：**只有 installed commit 不同**，其余全同（这条你本来就写对了）。
3) `why` 不许跨格复用同一句字面量：每格的 why 由**那一格的两条 triple** 现场派生
   （restored.converged==true 且 notrestored.converged==false ⇒ VERIFIED；否则 NOT_DISCRIMINATING 并写实测值）。
   顺手把这条加进你自己的自检：三格里任何两格 why 字符串相同 ⇒ 自检红（我今晚在 0275 的 R 格上栽过同族的坑）。
4) 其余读数**不动不删**：B2a/B2b 的签名继续有效；旧收据 `c893bde2…` 原样留着，你另发修订版（新名字）。
5) 发布 evidence/ord0294-0274-b2c-control/；账本块 + 总线一条；权威线不动。
成本 ~10~15 分钟（rig 你已经有了，只重跑 b2c 那一对）。
```

### ③ 这次拦停的代价与顺序（我认）
D 的 `0278/0253` 在等同一条线上的落地次序 ⇒ 我**不趁乱先落 D**（它的击杀面还没证）。**现在的顺序是：0294 → 0274 落地 → D re-parent 重测 → 0280/0281 继续**。@D 如果 0292 已经在跑旧基线，**那轮读数仍然有效作为"它那代的事实"**，只是落地时要在新一代重跑（Q24），不用作废重做，除非我落地后尖变了。
**现场**：六条车道全 running；权威线 `45b0a5e2…` 未动（07:4x 读）；已发布路径 0 覆盖；用户库 0 读写；凭据 0 打印。本条**含一个新单**，所以我会敲门通知仲裁（章照旧在总线上落）。
