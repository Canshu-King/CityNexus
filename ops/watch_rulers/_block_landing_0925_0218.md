## commander 落地 @2026-09-25T02:1x+08 —— **ORD-0272 落进可读权威线：`mirror/integration-frontend-apple-pass1` 从 `1f44408` 快进到 `dcae1bc96…`（ff-only，服务端校验）**；我用自己的手在落地那一代复跑出 GATE-GREEN 8/8

### ① 动手前三件前件我都实测为真（红队 02:02 的派生件是最后一件）
```text
修正后继枝：refs/heads/review/ord0272-continuation-corrected -> dcae1bc964125c3a975916f6bf667794cc19622a
lineage：父 = c79e2b4f4efe（权威尖）；tip tree d96c2974924d == aa29612c8 的 tree（没硬摘）；
        44b428d 非祖先（双向 compare 都测）；相对权威尖只改 4 文件、frontend 0 命中
外读：F 六件在 evidence/ord0272-nodeid-correction/（她的坐标补件，全量扫出 29 条错根并改成整条相等 + 反向探针）
派生：红队 221c6372db22c8ac1f9e02604055358758fe49d1（8,452 B）=> 门 GATE-GREEN(8/8) + 四腿 ALL_FOUR_LEGS_HOLD
        + 载体 21/21 可收集；K8 记 UNPROVEN_AS_KILL；它明说"不自宣 CLOSED、动不动尖是你的手"
F 补的坐标债：她的 r2 工具我已用（blob 562bac0844834426ac16e5719b328e303fa15f68，取回重算 blob 相符）
```
### ② 我怎么落的（以及两处我自己先撞错的地方，都写下来免得别人再撞）
```text
a) 我的 land_authoritative_ref.py 第一次跑直接 REFUSE（0 写）：它去查 `integration/frontend-apple-pass1`，
   而 GitHub 上**根本没有这个名字的分支**——可读镜像叫 `mirror/integration-frontend-apple-pass1`。
   ⇒ 事实纠正（也纠正我自己的记忆）：这条线在 GitHub 上的可读 ref 是 mirror/ 前缀那个；
      34 条 refs 我列过一遍：integration/baseline、integration/qoder-truth-frontend-v6-apple-ab、
      mirror/integration-frontend-apple-pass1、commander/control，其余都是 review/*。
b) 第二次 PATCH 路径写错（少了 /heads/）-> 结果是 422 "Reference does not exist"，回读尖未变，0 写。
c) 第三次：GET 先读 tip=1f44408（等于我申报的 base 才继续）-> PATCH force=false -> 200 -> 回读 tip = dcae1bc96…
   ⇒ force=false 让 GitHub 自己在写入那一刻检查"必须后代"，等价于我手工的 ff-only，且没有本地竞态。
   这一次快进**同时把 ORD-0263 那一笔（c79e2b4f）带进可读线**（镜像原本落后一笔），所以我申报的是 +2。
落地面（GET commits 回读）：parents=['c79e2b4f4efe']；文件 backend/app/main.py、backend/app/schemas.py、
   backend/tests/test_qoder_ord0272_continuation.py、contracts/openapi.yaml。
```
### ③ 同代复验：我自己跑的那一遍（不是转述红队）
```text
导出：codeload tar.gz(dcae1bc9) 50,240,091 B -> 只解 backend/data/contracts/tools（398 条；少任一项会造出假红）
工具：F 的 o272_reverify_r2（blob 562bac08… 取回重算相符）；解释器 D:/moodle/CityNexus/.venv（3.12.14）
自测两向：有门 -> GATE-GREEN（8/8）；没门（用本地 c79e2b4 那棵树）-> NOT-PRESENT；
          她新加的"错根探针 backend/…::x"-> BITES；SELFTEST_PASS
真跑落地那一代：verdict=GATE-GREEN；8 passed, 2 warnings in 2.65s；cells 的 (nodeid, exact_sha, result, run_shape) 齐全
   exact_sha 8/8 = dcae1bc964125c3a…；silent_alarms=[]；files_before == files_after（只读为真）
   套件库头：ORD-0211 resolved=%TEMP%\cnx_pytest_*\suite.db，exists=False，未出现 _live/_preview
外读收据：evidence/ord0272-reverify/commander_samegen_reverify_landed_dcae1bc9_r2.json
          16,308 B  31996a40d57c4f3c33f0e32ce02cdc5159993808  commit 9ba6548a8f85  BYTE-LEVEL MATCH
```
### ④ 一枚我这侧发现、要回给 `@F` 的工具形状问题（不是产品缺陷，我先不自己改她的工具）
我最初把快照解在 `…_qoder_cmdr_ref_20260921\live_checks\` 底下，跑出来的 **cell 级 exact_sha 变成了 `e9efec6bff2f…`（我那台 ref 仓库的 HEAD），不是落地 sha**；把快照搬到 `D:\moodle\` 下（外面没有 .git）再跑，8/8 才都是 `dcae1bc96…`。
⇒ 她的工具是从树的**上层**取 `git rev-parse HEAD` 的，快照若嵌在另一个仓库里就会拿到别人的坐标。**建议她加一道兜底**：拿到的 HEAD 不等于 `--gen`/申报 sha 时判 `SHA_SOURCE_MISMATCH` 而不是继续盖章。第一份带错 sha 的收据我已当场删除（它是我 5 秒前的派生物，从未上架），只发修正后那一版。

### ⑤ 各车道新基线
`@D` `@B` `@C` `@HJ-P1` `@HJ-P3` `@红队` `@F` `@HARNESS`：从现在起请以 **`dcae1bc964125c3a975916f6bf667794cc19622a`**（= `mirror/integration-frontend-apple-pass1` 尖）为落地基线；你们手上仍指着 `c79e2b4f…` 的候选分支需要 re-parent 后再自证（这一步归你们，我不会代改）。ORD-0272 现在仍**不算 CLOSED**：K8 是 claimed-survivor，HJ-P3 的跨进程面是行为证据而非反突变证据；升格需要 F 补一枚 K8 突变体 + 跨进程定向观测。
纪律读数：`demo/reset` 0、用户库写 0（复验走一次性临时库）、凭据 0 打印、已发布路径 0 覆盖 0 删除（本轮新增 1 件收据）、产品码 0 写；权威 ref 只由我移动，本次是服务端校验的快进（非 force）。

