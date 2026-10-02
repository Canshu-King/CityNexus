# ORD-0500 r5 -- how to rebuild the two counter-example trees (neither is ever committed)

写于 `2026-10-01T15:47:47.759946+08:00`；读数那一代的基座树 `b604f50d1645d028c2dd1d4406caee8198a3bc2d`，交付候选 `a2ae451f25a704e4c32e99425d78841ee50a21a0`。每一枚反件都跟**交付候选**比，不跟基座比——跟基座比会把我自己那笔具名拒绝混进差异行数里，那就不叫反件了。这一页由 `tools/ce2_recipe_r5.py` 对着那两枚树现算生成，不是手抄上一代的配方——上一代的页眉里写的还是它那一代的树名。

## CE-1 -- the server's own duplicate check removed（服务端那枚反件）

- 对照的两棵树：`wt22`（`wt22\backend\app\main.py`，本机字节 sha256 `3b67577e464496ad92b929929b5546ae615005c377e7f42383bfb2fb2d0a0eca`）与 `mutgen9`（`mutgen9\backend\app\main.py`，本机字节 sha256 `f9504db1b29efde1ac62b19ac36d8b423aad7eb8b229ee06cf22b96a5c27f3e1`）。
- 差异共 8 行（增 2、删 6）。sha256 是本机字节的，不是 git 物件，不可 cat-file。
- 摘掉的就是这几行：

  ```
  -    existing = session.scalars(
  -        select(JourneyCheckin).where(
  -            JourneyCheckin.journey_id == journey.id,
  -            JourneyCheckin.target_key == target_key,
  -        )
  -    ).first()
  +    existing = None  # MUTATION(ORD-0500 CE-1, throwaway tree mutgen9, never delivered)
  +        # the door's own duplicate lookup is gone; only the UNIQUE index can refuse a replay
  ```

## CE-2 -- the on-screen mark taken from the plan instead of the footprint read（屏上那枚反件）

- 对照的两棵树：`wt22`（`wt22\frontend\src\features\trip\TripItinerary.tsx`，本机字节 sha256 `84232bb39dcb7867e6d33b882e8331e872c6eb6cea0ce1e5f1c3571ca6551d04`）与 `wt24`（`wt24\frontend\src\features\trip\TripItinerary.tsx`，本机字节 sha256 `61f37abcb159d73dedf32e2a629932894cd9ee0fc3d8412bf36256692e8fe4de`）。
- 差异共 7 行（增 6、删 1）。sha256 是本机字节的，不是 git 物件，不可 cat-file。
- 摘掉的就是这几行：

  ```
  -    for (const stamp of answer.stamps) next[stamp.target_key] = stamp.id;
  +    /* MUTATION(ORD-0500 CE-2, throwaway tree wt24, never committed): the mark comes from the
  +       plan's own activity status instead of the rows the footprint door returned.  Three stops
  +       are COMPLETED in the sealed demo plan, so this face paints 3 marks on a store holding 0
  +       rows -- which is the second state machine the order forbids. */
  +    for (const act of plan?.activities ?? [])
  +      if (act.status === "COMPLETED") next["activity:" + act.id] = act.id;
  ```

## 造面与跑法（本代的实名）

- 三面由 `tools/gen9_build_r1.py` 的 FACES 建，outDir 与入口资产名回读自 `evidence/gen9_builds_r1.json`：
  - `TIP_b604f50d` ← 树 `wt23` → outDir `faces/tip9`，入口 `index-BOEFmwpL.js`
  - `O0500_R5` ← 树 `wt22` → outDir `faces/o0500_r5`，入口 `index-3R2y30xz.js`
  - `O0500_CLIENTBOOL_MUTANT` ← 树 `wt24` → outDir `faces/o0500_clientbool9`，入口 `index-lLCqupGT.js`
- CE-1 的配对跑在 `tools/gen9_ce1_r1.py`（pytest 两侧），树的差异收据在 `tools/gen9_ce1_proof_r1.py`；后者存在的原因写在其文件头：一次配对里第四枚红是被改树缺一枚文件造成的，那是仪器的事，不是结论。
- CE-2 的臂跑在 `tools/gen9_carrier_r1.py` + `tools/gen9_carrier_arms_r1.py`，会咬人的是 `ord0500-2`，它的报错句子同时带屏上枚数与门里行数。
- 曝光尺（第三种反件形制，同一枚实例三趟）：
  `node <cmdr live_checks>/ui_exposure_taint_ast_r7b.cjs --tree <tree>/frontend --out <file>`
  对基座树与候选树各一趟，两趟都必须在同一代、同一把尺上跑。

## 两枚反件树与反件面不进任何枝

- 反件树 `mutgen9`、`wt24` 与它的三面之一 `faces/o0500_clientbool9` 只是被建出来挨判的，不提交、不推送；候选 `a2ae451f25a704e4c32e99425d78841ee50a21a0` 自己一行没被它们影响（`candidate_tree_untouched` 在 `evidence/gen9_ce1_r1.json` 里）。
