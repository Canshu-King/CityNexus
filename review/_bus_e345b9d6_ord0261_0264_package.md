**e345b9d6（lane D）交付包：ORD-0261 + ORD-0264 候选（照 B 那套七件形状）**

## ① 来系（lineage）

```text
候选尖（candidate tip）  = 6daceb19d36691000f19189f8ebd51067e225643  (6daceb1, 17:10)
其父                    = a0fbe030494a027de85c92f462e1e1d4ea6c2a42  (a0fbe03, 16:52, 你已见的复现 spec)
基点                    = dea8410（= 我分支的起点，也是权威线当前尖；merge-base --is-ancestor dea8410 6daceb1 ⇒ YES）
分支                    = agent/d-e345b9d6-candidates（本地，未推送）；worktree = D:/moodle/_qoder_d_lane_20260923
权威线 integration/frontend-apple-pass1 本轮 0 写；权威树 status -- frontend = 0 行。
```

## ② 动了哪些文件（`git diff --numstat a0fbe03..6daceb1`，逐条）

```text
172  +0    frontend/e2e/qoder-wizard-advanced-is-tappable.spec.ts   (新门，2 节点：0261 sticky 条格 / 0264 opener 格)
 +18  -14  frontend/src/features/setup/JourneyTrialSetup.tsx        (0264：opener 从页底 .trial-secondary 挪进 step1 卡片紧贴 details；
                                                                      test id/文案/onClick 逐字节未动，只挪位置 + 注释写明为什么)
 +14  +0   frontend/src/styles.css                                  (0261：.cn-onboarding .trial-steps 底部让位 calc(76px+…)，
                                                                      移动层再加 var(--cn-sim-float-clearance)；条与 summary 尺寸一行未动)
  +1  -1   review/run_spec.py                                       (仅本 worktree 副本：ROOT 改为 os.environ.get("CNX_LANE_ROOT", 权威默认)；
                                                                      权威树的 run_spec.py 一字节未改 —— 这格是仪器，不是产品)
backend/ 0 文件；:4781 正在服务的 dist、_live.db/_preview.db、公网 0 触碰；未 demo/reset。
```

## ③ 门禁命令与退出码（全在本 worktree 字节上，`CNX_LANE_ROOT` 指我的树）

```text
CNX_LANE_ROOT=D:/moodle/_qoder_d_lane_20260923 python review/run_spec.py e2e/qoder-wizard-advanced-is-tappable.spec.ts 4610
  ⇒ exit 0，"3 passed (16.3s)"（run155129；2 节点 + real-seed setup 那格）
CNX_LANE_ROOT=D:/moodle/_qoder_d_lane_20260923 python review/run_spec.py e2e/qoder-ord0261-overlap-readonly-reproduction.spec.ts 4612
  ⇒ exit 0，"2 passed (11.7s)"（run155147）
  ⚠ 注意这一份的 verdict 字段仍是 "REPRODUCED"：它是只读复现 spec，量法在 scroll-top（量 scroll 位置，不是可点性）——
  它的用途是把"修前是什么样"钉住；修后的判定以 4610 那份门为准（它先 scrollIntoView 居中再打中心并记录 scrollY）。
  两份并存，我没有把复现 spec 改成"修后口径"，免得它失去复现能力。
npx tsc -p tsconfig.check.json --noEmit ⇒ exit 0；npx tsc -p tsconfig.typecheck.json --noEmit ⇒ exit 0
回归（同字节）：向导四道已有门全绿 —— hint-surface 6 passed / speaks-human 6 / blocked-next-a11y 8 / city-basis 6
```

## ④ 每臂 killer 的 primary / collateral

```text
0261 格 primary = "sticky 条盖住 summary"：删掉 .trial-steps 的 padding-bottom ⇒ summary 中心重新被条的渐变盖住、
  命中条的 <BUTTON>下一步 ⇒ RED（修前实测就是这条红；修后 GREEN）。
0264 格 primary = "opener 在折叠之下"：把 button 挪回页底 .trial-secondary ⇒ 中心回 y≈1208、
  844 视口外 ⇒ inViewport 断言 RED。
collateral：两格在对方突变下都存活（挪按钮不影响 sticky 覆盖；删 reserve 不影响 opener 位置）——
  这是形状判断，正式三臂矩阵我还没跑：上一条消息里求你裁的"0264 视口内用滚动后表达还是初屏硬口径"你还没回，
  我等口径定了一次跑完，不跑两遍。
```

## ⑤ 我自己 worktree 的 `git status --porcelain -- frontend` 逐字输出

```text
（空 —— 上一行与 [END] 之间没有任何字节）
```

## ⑥ 具名一句（照你要求）

**发布代仍是 `027d65ed…`（`index-DJEINrOl.js`），不含 ORD-0250/0251/0261/0264** ⇒ 本候选的用户可见状态 = **NOT-DEPLOYED(phone)**，我只按"候选已交、等待验收"写，任何验收词都不写"已上线/用户可见"。0261/0264 的执行口径（sticky 不压 summary 行、button 只移不删且已证无已验收门引用它）已照你上一条回执办完。

竭尽所能的替qoder铺路
