## 亲测 @2026-09-25 09:1x+08 —— ORD-0299（B 把 0280 真跑了 + 反件）：收据 **10 格、我的 Q38 尺 GREEN（硬 0 软 0）**，反件真的咬了；**但候选 ref 还没推上线，所以它现在没有可落地坐标**

### ① 我量到的（三个 blob 都按 40 位取回、现场重算 sha1 == 申报值）
```text
`evidence/ord0299-attribution-run/ord0299_attribution_run_receipt.json`  31,760 B  blob `02dfbb817e5add8577c4c47a7e898983743b7202`
`evidence/ord0299-attribution-run/counter_arm_rendered_readings.json`      1,427 B  blob `56c6abec0ad5a7e902db16a38dc5d228c6d6432b`
`evidence/ord0299-attribution-run/baseline_rendered_readings.json`         8,264 B  blob `8788ddf8bc1b4805c1cc85b0bd41dc90ed532ead`
我的 Q38 尺输出（独立跑，不是引它的自检）：`cells 10 | overall Q38_GATE_GREEN | hard 0 | soft 0`
```
### ② 反件形状正是我要的那种（不对称，不是"全红"）
```text
counter-arm：两枚 hunk 落在渲染行 929 与 931 ⇒ 标签不再看"谁说的"；组件 sha256 2e2a6d346d73d680 -> 6d898a5250dc66e1
   device 臂 **A1 / B1 / C1 / D 全 FAILED**；server 臂 **A2 / B2 / C2 仍 passed**；跑后还原 byte-exact=True、src clean
⇒ 这才是"标签选择真的在干活"的证据：如果反件让所有臂都红，那说明判据没区分来源；只红 device、server 不动，才证明 `from` 是唯一变量。
每格 `why` 里用到的具名值都在该格自己的 `readings` 里（尺量的：10 格各自命中），`derived_result` 全格留 null ⇒ B-1 合规。
```

### ③ 现在卡住的那一步（不是它的错，是坐标规则）
```text
收据写候选 = `review/0280-attribution-label-r2` @ `549ac8f1b20bc04e70eadbd238ade737eefbff01`（parent 声明为落地代 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`，`merge-base --is-ancestor rc=0`）
我这边外读：`GET /repos/.../commits/549ac8f1…` -> **HTTP 422**；分支表里只有旧的 `review/0280-attribution-label` = `48827a9d6402aaabffc5ff47b1540407fafed620`
⇒ **r2 那枚 ref 还没推上线 ⇒ 按 EXTERNALLY_READABLE_EVIDENCE，一个只在车道本机存在的 sha 不是坐标，我不落**。（不是怀疑它存在——它刚跑完，推 ref 是下一步。）
```
### ④ 时间账（09:1x 起，我把话说明白，不硬赶）
```text
若 @B 在 09:30 前把 `review/0280-attribution-label-r2` 推上线并贴出 https `ls-remote` 行：
   我立刻（a）外读尖 == 549ac8f1、（b）核它 parent == 5c4608ce、（c）跑尺仍绿 ⇒ ff-only 落地；
   然后**是否做第二次换代**由我按风险决定：管线现在很熟（干净导出→build→并集→切 index，约 5 分钟 + 逐字节回读），
   但第二次换代的唯一收益是"手机上多一格归因标签"，风险是 09:40 之后动手机面。
   ⇒ 默认：**能落就落，落得晚就不换**（手机继续跑 `5c4608ce` 那一代，它健康、且已带 0274 三格）。
若推不上来：0280 保持 `STATIC+EXECUTED_ON_DEV_FACE / 未落地`，我不签 CLOSED。
另：face 那一格它自己写清了 `DECLARED`——这批读数来自产品自己的 e2e hook（:4391/:8191 与 :4392/:8192，两库两 run id），**属"规格会红会绿"，不属发布级证据**，这个自我限制我照抄进状态里。
```

### ⑤ 记一笔车道贡献（不是套话）
B 今晚直接往共享项目记忆里加了三条**实测**教训，其中一条我今晚就会被用到：
`git rev-parse <rev>:<path>` 在文件不存在时**照样把参数回显**（rc 128、stdout 有文本）⇒ 配 `or 'ABSENT'` 就变成"假存在"；判存在要用 `[0-9a-f]{40}` 匹输出，或用 `git ls-tree`（不存在时什么都不打）。
还有"把事实写成 F1 形式让 Q43 尺能量到（`claims checked 4 / CLEAN`），写成散文会得到 `NO_CLAIM_FOUND_NOT_APPLICABLE`——那不是通过"。**这两条我保留，不回滚。**

**纪律**：权威线本节未动（`5c4608ce…`）；本节 0 次 PUT；用户库 0 读写；`demo/reset` 0；凭据 0 打印。
