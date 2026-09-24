# ORD-0287 · K8 回填守卫在权威线上的回归载体（test-only 候选已交）

lane F `8ccd71d8` · 2026-09-25T07:11:09+08:00

## 一句话

权威线上现在有一格守着 `IdempotencyKey.response_json.is_(None)`：**同一格在权威字节上绿、把那半个条件拆掉后同一格红、正控两态都绿 ⇒ 红可归因**。候选只加一个测试文件，产品字节 0 改动。

## 判据 1：父 = 权威尖（我自己先读）

```text
base（先读到的权威尖） 45b0a5e281cae9c37715173afd3ac5778f309ca7
候选 tip             c31ba195d94ae6ab0cd0a50e17470bebc7587f44   tree f26f35091433a1d4b19fe8361b97d50bb707d63f   parent 45b0a5e281cae9c37715173afd3ac5778f309ca7
parent == base ⇒ True   候选里 backend/app/main.py = 416ea4f210e967130710a900cdecd20e7a1b5eca（与落地字节相等 ⇒ True）
commit subject：test(ord0287): give the plans/generate receipt guard a regression carrier on the shipped line
```

## 判据 2：只加测试文件

```text
git diff --name-only c31ba195d… 相对 45b0a5e28… = ['backend/tests/test_qoder_ord0287_k8_carrier.py']
numstat = ['220\t0\tbackend/tests/test_qoder_ord0287_k8_carrier.py']（+220 / -0，一个文件）
所有路径都在 backend/tests/ 下 ⇒ True；产品路径改动 = [] ⇒ 0 件
上一单那道 0272 门文件未被改动 ⇒ True（仍是 efa783397e6105ca8f15be9a5701e60e5ace0296）
载体 blob = 894c6d54e345dabdc4050a38f413fdaaa1a92748 与提交里那枚一致 ⇒ True
创建方式：只用 plumbing（hash-object / read-tree / update-index / write-tree / commit-tree）⇒ 任何工作树 0 次 checkout；本道工作树跑完 `git status --porcelain` 仍是 0 行
```

## 判据 3：同一格两态可跑（2 轮 × 两棵树都量过）

```text
候选自己的导出树（git archive c31ba195d… → backend/data/contracts/tools）：
  守卫在位：K1 rc=0（1 passed, 2 warnings in 1.82s）  K2 rc=0（1 passed, 2 warnings in 1.60s）
  拆掉守卫：K1 rc=1（1 failed, 2 warnings in 1.82s）  K2 rc=0（1 passed, 2 warnings in 1.90s）⇒ 正控仍绿、只有那一格红
  突变：before 416ea4f210e967130710a900cdecd20e7a1b5eca → after 784599fdb406b4242c2d202868b5eefd10861287；hunks=1（@@ -4770,8 +4770,7 @@）；py_compile=True；行数 [11417, 11416]；每轮逐字节还原 ⇒ True
  派生：{"carrier_green_on_authoritative": true, "same_cell_red_under_mutation": true, "positive_control_still_green_under_mutation": true, "one_hunk_every_round": true, "py_compile_every_round": true, "restored_every_round": true, "verdict": "TWO_STATE_CARRIER_OK"}
落地代导出树（同一载体文件）另跑一份 ⇒ {"carrier_green_on_authoritative": true, "same_cell_red_under_mutation": true, "positive_control_still_green_under_mutation": true, "verdict": "TWO_STATE_CARRIER_OK"}
同载体 + 0272 那道门一起跑（一座库、一次进程）：10 passed ⇒ 载体不与既有门互相污染。
收集分母（改前先量）：整套件 1234 collected（= 1232 + 本文件 2 格），单跑本文件 2 collected，无 collection error。
```

## K1 / K2 各判什么（为什么不引缝也能测守卫）

```text
K1  test_K1_a_receipt_another_writer_already_filled_is_never_rewritten_and_refuses_by_name
    前置：两把键（transport + cont:<真 mission>）都由门外 sqlite 真落盘成**别人已答完**的样子；
    进的是产品自己的 Phase B（_execute_plan_generation_claimed，落地代就在 main.py:4736）；
    断三件：抛现成那句具名 409（句子是本文件自带的字面副本，不 import 产品常量）、
            别人那两行字节逐字不动、被拒那一发不许多写候选（守卫拆掉时这条会翻倍，正是 0282 量到的副作用）。
K2  test_K2_my_own_unfilled_claims_do_get_filled_and_hold_my_answer
    我占的两把 NULL 必须被真填上并留回我这一发的答案 ⇒ K1 不可能靠『永远失败』假绿；
    K2 只测回填通路本身，守卫在位/拆掉两态都该绿 ⇒ 归因干净。
为什么不走 HTTP：Phase A 的唯一索引让第二个抢键者在门前就被挡回（回放/409），根本到不了回填语句 ⇒
    红队那句 `HTTP_FACE_CANNOT_REACH_K8` 是射程；本格因此直进 Phase B，跨进程那一面仍归 verifier。
```

## 判据 5：外部可读坐标

```text
GitHub ls-remote：c31ba195d94ae6ab0cd0a50e17470bebc7587f44  refs/heads/review/ord0287-k8-carrier-f
落点 sha == 候选尖 ⇒ True   https GET /repos/Canshu-King/CityNexus/git/ref/heads/review/ord0287-k8-carrier-f = c31ba195d94ae6ab0cd0a50e17470bebc7587f44
https 取回载体文件字节数 11253（非空 ⇒ True）
未 force-push、未改写任何已发布 ref。兄弟提交披露：我先后铸过两枚兄弟提交（同一 tree、同一父、同一信息，只差 committer 时间戳）：c31ba195…（推到 ref 的那枚，本表全部按它）与 d1e06920…（第二次跑脚本时手滑重铸，未推、无 ref 指向）。外部坐标只有一个：refs/heads/review/ord0287-k8-carrier-f = c31ba195…；我没有 force-push、没有改写任何已发布 ref。
```

## 复跑

```text
git fetch origin refs/heads/review/ord0287-k8-carrier-f && git archive c31ba195d94ae6ab0cd0a50e17470bebc7587f44 backend data contracts tools | tar -x
cd backend && CITYNEXUS_DATABASE_URL=sqlite:///<一次性库> python -m pytest \
     tests/test_qoder_ord0287_k8_carrier.py -q -p no:cacheprovider -rf        # 期望 2 passed
再把 app/main.py 里 `.where(IdempotencyKey.key == key,\n ... response_json.is_(None))` 改成 `.where(IdempotencyKey.key == key)`（一处 hunk，py_compile 要过）⇒ 期望 K1 FAILED、K2 passed，然后逐字节还原
（或 O287_BACKEND=<导出树> python o287_two_state.py，一次做完两态 + 还原回验）
```

## 判据 0 / 第 0 条的边界（保留在案，不重复劳动）

```text
第 0 条答案：候选代那枚 test_G9 原样摘到 45b0a5e2 跑不起，拦路符号 `_fill_plan_generation_receipts`（落地代命中 0 / 候选代命中 2）；已发布三件：
  ORD0287_STEP0_ANSWER.md                903f0a100f533393800ebe4e6edac7a608af3dbd 3,553 B
  o287_step0_portability.py              243b66b657f58d2784d34f63f3ab65c9989b1fce 9,297 B
  ord0287_step0_portability.json         3197c26db9702a40eb773db21c42565c7f912579 3,940 B
⇒ 本候选因此**不 import 那枚缝**，只 import 权威线上真有的 `_execute_plan_generation_claimed`；
  这正是 Q35=② 要的『只依赖权威线』形状。
```

## 判据 6 与不越界

```text
权威线 0 次写（我只写自己的 review ref）；已发布路径 0 覆盖 0 删除；demo/reset 0 次；_live/_preview 0 读写；凭据 0 打印；派生 derived_result 归 @红队，我不自签。
判据 4：两进程 rig 没有塞进候选（候选只交 CI 形状那两格），两进程读数留在 ORD-0282 的证据目录。
```

