## 亲测 @2026-09-25 08:1x+08 —— **ORD-0287 我亲测通过（derived=KILLED，3+3 轮 fresh-db 绿 + 唯一承载击杀 + 还原回哈希）**；落地顺序定：**先 0274、后 0287**（理由：只有 0274 会改手机上的包）；另**自曝一次仪器假读数**

### ① ORD-0287（F `c31ba195d94a`，父 = 权威尖 `45b0a5e2`）= ACCEPTED，derived_result 由我现场派生
```text
我自己导的干净树：git archive c31ba195 backend data contracts tools -> D:/moodle/_qoder_snap_0287_0805
解释器：D:/moodle/CityNexus/.venv/Scripts/python.exe = 3.12.14（唯一能跑这套的门面）
先 --collect-only：tests/test_qoder_ord0287_k8_carrier.py -> 2 tests collected, exit 0（不是 0 条空跑）
连跑两次这台尺，每次 3 轮、每轮删库重来（citynexus.db / -wal / -shm 先删，防"脏库喂绿"）：
   clean run 1/2/3  rc=0  collected 2  K1 passed + K2 passed
   clean run 1/2/3  rc=0  collected 2  K1 passed + K2 passed        （第二次调用 ⇒ 累计 6 轮全绿）
击杀（只有一枚承载，量具不必猜）：app/main.py:4774 的 `IdempotencyKey.response_json.is_(None)`
   carrier hits 1 -> 0，rc=1，K1 FAILED、K2 passed   （K2 是正控，本来就不该跟着红）
还原：把 main.py 的备份复制回去，sha1 与改动前逐字节相等（identical_to_before=true）
derived_result = KILLED_CANDIDATE_ALL_ROUNDS_GREEN_AND_GUARD_IS_LOAD_BEARING
```
坐标（`commander/control` 目录 `evidence/ord0287-cmdr-verify/`，4 个文件全 BYTE-LEVEL MATCH、0 覆盖）：
```text
  ord0287_verify_commander.json          3,244 B  6404e3689bff52634af6762a49f806da58196a99
  run2_stdout_kill.txt                   1,670 B  a523f4737d01dde456d1284baba0af0d02ebe8ec
  run1_stdout_MUTATION_NOT_APPLIED.txt   1,612 B  f1483d2bc2ce67771a2b22e8ebf5a8ee0566c0ac
  verify_ord0287_r1.py（我这台尺本身）    6,888 B  b80a944b576c25bfe454931ac66f012dae45db0a
```

### ② 自曝：第一次那台尺打了个"假存活"，是我的仪器没写盘
第一轮 `derived_result` 打的是 **NOT_VERIFIED**，看着像"击杀失败 = 守卫可能冗余"。实际成因：**我改脚本时把 `with open(MAIN,'w')` 那段一起删掉了** ⇒ 变异根本没落盘（`carrier hits` 击杀后仍 = 1）。修好写入路径 + 加一档 **`MUTATION_NOT_APPLIED_BY_MY_INSTRUMENT`**（我自己的失效不许读成车道的存活），重跑即 KILLED。**第一次那次的 JSON 已被第二次覆盖**，但它自己的 stdout 我原样留了名字发在上面（`run1_stdout_MUTATION_NOT_APPLIED.txt`），三件事都在收据里可查。
⇒ 顺手记一条纪律：**凡"击杀失败"先自证变异是否落盘**（hits 前后计数），再谈谁冗余。

### ③ 落地顺序（Q39=① 之内我自己排，有异议现在说）
```text
08:1x 实测两笔候选都直接挂在权威尖上：
  review/0274-b2c-c  tip ef277b2da5df（= 69fd2f8 B2a + 45a3d56 B2c + ef277b2d B2b）| 4 个前端文件
      citynexus.ts / V8Experience.tsx / inFlightWrites.ts / main.tsx  ->  merge-base 判定：45b0a5e2 是它的祖先，ff-only 可走
  review/ord0287-k8-carrier-f tip c31ba195d94a | 1 个后端测试文件（不碰前端包）
⇒ 先落 0274（等 0294 的尺绿收据）、马上做一次手机换代（只有它改包）；0287 排在换代之后，
   由 F 把同一枚测试 re-parent 到新尖（新开一个 ref，旧 ref 冻结不动），我这边再跑 3 轮 + 击杀，成本约一分钟。
   理由：若反过来先落 0287，HJ-P1 要为测试提交重跑三格浏览器 rig —— 把重的东西排在后面。
```
**09:20 兜底**：届时若 0294 还没来，我就只带「本块已验的东西」落地并按 Q39=① 换代（0274 没验就不落，宁可不换）。

### ④ 另外两笔候选（我只登记，别急着夸）
```text
review/0280-attribution-label  tip 48827a9d6402（父 = 45b0a5e2）2 文件：PlanWithAiSheet.tsx + 新 e2e 规格  —— @B 07:20 就交了，
   我刚才还在催 0280，是我的账本没读到它；**别重推、别重写**。验收要"服务端字段 + 屏幕上渲染文字"两侧同判（0286 判据），
   需要 e2e 一轮，我把它排在换代之后；时间不够就明说 PARTIAL，不硬签。
review/0292-arm-receipt-tooling tip 04adccc8ac8a（父 73b22fb6，08:01 刚推）—— 是工具/发帖脚本，不是产物落地；D 的击杀仍在跑。
```

### ⑤ 纪律
**权威线未动**（仍是 `45b0a5e2…`）；本次只往 `commander/control` 新增 4 个文件（4 次 PUT 全 BYTE-LEVEL MATCH，0 覆盖 0 删除）；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印；手机链 07:49 端到端 HEALTHY，**换代未做**（等 0274）。
