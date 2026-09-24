# Q22 · ORD-0272 corrected continuation 枝（44b428d 不进权威线）

lane F `8ccd71d8` · 2026-09-24T23:12:29+08:00

## 裁文口径与本件做的事

包工头转达的 Q22：**不 squash、不删历史，但 44b428da8 不得进入权威线**，要的是
`c79e2b4f4 →（corrected continuation branch）→ aa29612c8`。

我做的是一枚**新提交 + 新 ref**：

```text
new commit  = dcae1bc964125c3a975916f6bf667794cc19622a
parent      = c79e2b4f4efe414dba22a071a7136ae10b5c84aa          ← 权威尖，正是裁文要的父
tree        = d96c2974924d19831495f2945117d4221a1b6d62   ← 与 aa29612c8 的树**同一枚**
ref         = review/ord0272-continuation-corrected
旧枝        = review/ord0272-continuation-f 尖仍是 aa29612c8（未动、未删、未 amend）
```

**这不是 cherry-pick**：corrected 那笔带的是 aa29612c8 的**整棵树**（逐 blob 相同），不是把第二笔的
diff 摘过去。所以侧会话提醒的那个坑不存在——**没有具名符号阻塞**：
`git diff --stat aa29612c8 dcae1bc96` 为空，且两枝 `tree` 同为
`d96c2974924d…`（见 `readings.json` 的 `trees_identical`）。

## 用包工头那把尺复现的读数（`readings.json`）

```text
compare c79e2b4f4...dcae1bc96   -> status=ahead \
ahead_by=1 behind_by=0 \
commits=['dcae1bc964'] files=['backend/app/main.py', 'backend/app/schemas.py', 'backend/tests/test_qoder_ord0272_continuation.py', 'contracts/openapi.yaml']
compare c79e2b4f4...aa29612c8   -> status=ahead \
ahead_by=2 commits=['44b428da83', 'aa29612c85']
   （你测的"整枝 ff-only 必然带进 44b428d"这一条被复现：旧枝 ahead_by=2，两枚依次 44b428da83、aa29612c85）
compare dcae1bc96...44b428da8   -> status=diverged \
ahead_by=1 behind_by=1
祖先扫描（corrected 枝，walked=100）：
   44b428d 在不在 = False   aa29612 在不在 = False
   前三笔 = ['dcae1bc964125c3a975916f6bf667794cc19622a', 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa', '1f4440819a9d773da6e18f12a31412f73c6d0f55']
旧 ref 未被触碰：ls-remote = True；API head = aa29612c855c
```

## 落地坐标（GitHub https 回读行，本地 sha 不算坐标）

```text
dcae1bc964125c3a975916f6bf667794cc19622a	refs/heads/review/ord0272-continuation-corrected
aa29612c855c10f1584a333cc19526066813b072	refs/heads/review/ord0272-continuation-f
```

## 这一代**真跑过**（不是哈希推理）

用我上一条交付的那枚只读命令 `o272_reverify.py` 跑 corrected 枝的 `git archive` 导出树：

```text
gen     = ord0272-corrected-dcae1bc964125c3a975916f6bf667794cc19622a
verdict = GATE-GREEN   八格 =    警报 = 无
库路径行 = ORD-0211 test database: resolved=C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_qfzv6ncd\suite.db | exists=False | declared_by=conftest temp dir
载体可收集 = {"K1": "6/6", "K2": "1/1", "K3": "1/1", "K4": "1/1", "K5": "5/5", "K6": "5/5", "K7": "2/2", "K8": "0/0"}
顺带（回归载体两枚既存门）= 
```

⇒ 落地后你要复验，同一条命令直接吃你的落地树：
`python o272_reverify.py --tree <落地后的仓库根> --gen <bundle 名>`。

## 判级与边界

代码判据不变：八格门 + 8 臂反突变 + 3×3 A/B 的 `MET-WITH-NAMED-SWIMMER`；`derived_result` 仍归
HJ-P3（跨进程同键 + K8 覆盖守卫）。本件只解决**历史形状**这一道程序问题，不改任何一行产品码。
