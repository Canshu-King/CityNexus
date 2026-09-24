# ORD-0282 · K8 那一处回填守卫在落地代 `45b0a5e2` 的重跑（唯一变量 = 树）

lane F `8ccd71d8` · run `O282S-250612-226b4c` · 2026-09-25T06:18:19+08:00

## 判级（判据 ④：由 A_filled / B_filled / bytes_survive 派生；B-1 不自签 derived_result）

```text
K8_SEAM_ON_LANDED_GENERATION = FLIP_OBSERVED   （claimed_result；闭单判级归 verifier）
  守卫在位 3 轮 : A 的回执字节存活 = [True, True, True]  B 覆盖行数 = [0, 0, 0]  B 被拒 = [409, 409, 409] 「agent idempotency record is incomplete」  A 填到的行数 = [2, 2, 2]
  守卫拆掉 3 轮 : A 的回执字节存活 = [False, False, False]  B 覆盖行数 = [2, 2, 2]  B 被拒 = [None, None, None]  A 填到的行数 = [2, 2, 2]
  顺带一条产品事实：plan_versions 轮末计数 guard=[3, 3, 3] vs mutant=[6, 6, 6] ⇒ 拆掉守卫不只是覆盖别人的回执，还让第二发重新生成了一整套候选（副作用翻倍）
  非空转三道 : 检测器自证（带外真改一次 A 的字节，每轮都必须看见）= True；每轮 main.py blob 与状态相符 = True；每轮三个 pid 互不相同 = True
  突变 : before 416ea4f210e967130710a900cdecd20e7a1b5eca → after 784599fdb406b4242c2d202868b5eefd10861287；hunks=1 @@ -4770,8 +4770,7 @@（只有一处）；py_compile=True；行数 [11417, 11416]；跑完逐字节还原 = True
```

## 树（判据 ①：独立来源，逐字节核对）

```text
镜像尖先读 45b0a5e281cae9c37715173afd3ac5778f309ca7 == 期望 45b0a5e281cae9c37715173afd3ac5778f309ca7：True
commit tree 039e5eafa260a6c30dc186947c1c1d1f0145a8a1；父 63b7702f47917be6da98b29e5a56a6646891184b
来源 GitHub tarball：50,284,763 B（sha256[:16] 9fa38ba757b163e8）；车道工作树 0 座、包工头那棵 _qoder_wt_45b0a5e 未复用
compare(7c806fa…45b0a5e2) = diverged (ahead 35 / behind 1)
导出字节 == 提交字节（逐件重算 git blob sha1）：
  backend/app/main.py                                      416ea4f210e967130710a900cdecd20e7a1b5eca   482,850 B  equal=True
  backend/tests/test_qoder_ord0272_continuation.py         efa783397e6105ca8f15be9a5701e60e5ace0296    24,562 B  equal=True
  backend/app/schemas.py                                   2e6e26ce17a9e25a40dd8d686f64def5ef1bff0e    25,591 B  equal=True
  contracts/openapi.yaml                                   484c64cdaaa41e72d252563b84cef915cb4e80eb   106,971 B  equal=True
  live_checks/audit_closure_coordinates_r3.py              NOT_IN_THIS_GENERATION                           0 B  equal=None
（第五件 `live_checks/audit_closure_coordinates_r3.py` 不在这代树里：contents API 与解包两侧都是 404 ⇒ 判据 ⑥ 我是按包工头分支上的那枚 blob 取回后跑的，不是从本机副本拿的）

## 两代并贴（判据 ⑤：候选代那份不覆盖、不删）

```text
候选代 7c806fab5 : main.py ad13f4395…, 门文件 799fbd2fe…, 缝已抽出, 载体 G9, KILLED_CANDIDATE_ALL_ROUNDS_RED, 红轮 [3]
           HJ-P3 跨进程读数 blob fbb154cf9ce598ad1d3a4241b0f1b96181f0037b
落地代 45b0a5e28 : main.py 416ea4f21…, 门文件 efa783397…, 缝符号在那一代 不在（实测 0 命中）, 那道门收集到 8 格（没有 test_G9），守卫在 Phase B 里内联 main.py:4770-4779
⇒ 本件的落地代读数不是『同名格的同代复现』，是『同一处回填语句 + 同一个两进程形状』在落地代的行为。这句写在判级旁边，不冒充前者；两代语义一致 ⇒ 结论可以并排读。
```

## 另一面（HTTP）：两态都不翻，那是射程不是守卫没用

```text
A 的回执字节存活 guard=[True, True, True] mutant=[True, True, True]；B 自己那把键被填 = [False, False, False, False, False, False]
机制：腿 B 的占位在 `idempotency_keys` 唯一索引上先撞回 ⇒ 走回放门 ⇒ 到不了回填语句；同 mission 并发那一发（两进程同时进）恒为两发都 201 且 cont 键只被一户填。
⇒ 红队的 HTTP_FACE_CANNOT_REACH_K8 在落地代同样成立——这条是量出来的，不是引来的。
```

## 第二观察者（判据 ⑥：先证明是他的尺，再原样报数）

```text
audit_closure_coordinates_r3.py 重算 blob fc35335aadffb8f0de6f8030e9fc5a747f24f463 == 申报 fc35335aadffb8f0de6f8030e9fc5a747f24f463：True（8,589 B；来源是他分支的 contents API，不是本机副本）
实跑 ⇒ claims=50 failing=0  branch=commander/control  rc=0；逐行 OK=50 / FAIL=0 ⇒ 与包工头 04:3x 申报的同一个数，我这台机独立复现
```

## 复跑

```text
python o282_phase1_tree.py                                              # ① 取尖 + tarball 导出 + blob 核对
python o282_seam_face.py --rounds 3 --json o282_seam_readings.json      # 主面（判级用的那一面）
python o282_rig.py --rounds 3 --json o282_rig_readings_v2.json             # HTTP 面
python audit_closure_coordinates_r3.py                                  # 第二观察者（先重算它的 blob）
```

## 纪律与不越界

```text
demo/reset 0 次；_live/_preview 库 0 读写；凭据 0 打印；权威线 0 次写；一次性库跑完即删；main.py 每轮逐字节还原并回验 blob；候选代与既有发布件 0 覆盖 0 删除。
不自签 derived_result（B-1）；用户面到不到得了 K8 仍按红队射程声明，不折算成『用户面已验』。
```

