**e345b9d6（lane D）候选交付：ORD-0261 + ORD-0264（走我自己的分支，权威线未动）**

**候选分支** `agent/d-e345b9d6-candidates`（本地 worktree `D:/moodle/_qoder_d_lane_20260923`，权威树 0 写）：
- `a0fbe03` ORD-0261 只读复现 spec（就是你问路径的那份：`frontend/e2e/qoder-ord0261-overlap-readonly-reproduction.spec.ts`，HJ-P3 可直接拿去复用量，不用重写）
- **`6daceb1`** 产品修复 + 门：`frontend/src/styles.css`、`frontend/src/features/setup/JourneyTrialSetup.tsx`、`frontend/e2e/qoder-wizard-advanced-is-tappable.spec.ts`（新）、`review/run_spec.py`（本 worktree 副本加了 `CNX_LANE_ROOT` 覆盖，见下）

**① ORD-0261（sticky 条压住 summary 行）——按你裁的"布局"修，没有删任何东西、没有动 summary 的尺寸**

```text
修法：滚动内容底部给 sticky 条让位（.cn-onboarding .trial-steps { padding-bottom: calc(76px + …) }，
      移动层再加 var(--cn-sim-float-clearance)，和 sticky 条自己的 bottom 让位同一条媒体查询）。
      条还在原位、还盖渐变，但它盖住的只剩自己的 padding，不再盖任何控件。
代价（写清）：向导页可滚动余量少 76px（移动层 ~208px）——这是"动作条永不压控件"的直接成本；
      换代前 HJ-P3 走一次向导就能验出有没有伤到别的布局。
```

**② ORD-0264（同名 button 永久折叠之下）——按你批的"移进可达区域"**

```text
trial-show-advanced 从页面最底的 .trial-secondary 行挪进 step 1 卡片内、紧贴它打开的那块 details。
test id / 文案 / onClick 逐字节没动；宽度还是 350×44。
删按钮那条我没走（也没有已验收门引用它，grep 过；但你只批了移动，就没动删除选项）。
```

**③ 门与读数（全在我 worktree 的字节上跑，`CNX_LANE_ROOT` 指我的树；权威树的 run_spec 副本一字节没改）**

```text
判据照你给的形状：同屏按标签枚举，逐枚要求 elementFromPoint(中心) 命中它自己（或其子节点）。
一把仪器教训写进门里：390×844 上这页本来就长——在 scroll-top 量，summary 中心 y≈885，命中空是
"还没滚到"而不是"不可点"。所以门先 scrollIntoView 居中、等 sticky 条落定、再打中心（并记录 scrollY）。
修后读数（run run 开头 4590 那批，3/3 passed）：
  高级设置 summary 348×44  scrollY=463 中心(195,422) 命中 SUMMARY「高级设置」自己 ✓（修前：命中 <BUTTON>「下一步」）
  高级设置 button 348×44  scrollY=531 中心(195,422) 命中 BUTTON 自己 ✓（修前：中心 y=1208 在 844 视口外、命中空）
  看支持的目的地 summary  91×44  ✓（正控）
killer 位置：`ord0261` 那格的失败消息就是"中心命中 <TAG> '文案' 而不是它自己"——把 reserve 删掉或把
  button 挪回页底，两格当场各自变红（我可以再补正式的三臂矩阵，等你定killer粒度后跑）。
回归：向导已有四道门全绿（hint-surface 6、speaks-human 6、blocked-next-a11y 8、city-basis 6 passed）；
  tsc 两配置 exit 0。我的 worktree 干净（candidate tip = 6daceb1）。
```

**④ 求你裁的一格（不裁我不跑正式矩阵）**：0264 的"button 中心必须在视口内"我用的是"scrollIntoView 居中后仍在视口内 + 命中自己"两个断言合起来表达——严格说"视口内"这一半在滚动后是恒真的，真正有牙齿的是命中自己那一半 + 0261 格里同 button 的位置。如果你要"不滚动也必须可见"那种更硬的口径（初屏即可见），说一声，我把 0264 那格改成"加载后 1s 内不滚动、button 的 rect 必须与视口相交"。

**权威树状态**：`git status --porcelain -- frontend` = **0 行**（那份复现 spec 已入库我分支 a0fbe03 并从权威树删掉未跟踪副本）；你随时可以出发布包。0250/0251 我不催——等第三方复验，规矩照走。

竭尽所能的替qoder铺路
