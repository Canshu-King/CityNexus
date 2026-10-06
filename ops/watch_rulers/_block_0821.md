## 亲测 @2026-09-25 08:2x+08 —— 换代用那把尺也有"零根仍报绿"的洞，已出 r2 并双向验死；手机链换代前置检查 **READY_TO_SWITCH**（三面全测），命令与环境写死在这里

### ① 换代尺 `bundle_selfreference_check` 的 r1 假绿（我自己写的，08:1x 撞出来的）
同一枚调用（只给 `--serve`、一个 `--look` 都不给）：
```text
r1  -> rc=0，JSON 里 overall = "ALL_SELF_REFERENTIAL"，并打印 checked=0     ← **零个根目录被判成"全都自洽"**
r2  -> rc=6，NOT_MEASURED_NO_USABLE_LOOK_ROOTS，roots_actually_measured=0
```
这是我自己那把尺的洞（不是我冤枉别人）：**"什么都没量"和"量了都过"共用一个退出码**，谁都能在换代前把它念成绿。r2 打 `roots_actually_measured`，为 0 就退出 6；r2 没有 `--selftest`（r1 也没有，我不假装有）。
双向证明（真盘，不是构造）：给它一个旧快照 `dist_bak_0125` ⇒ 量到 1 个根、**3 条悬空引用 ⇒ WHITE_PAGE_WAITING**（正是 ORD-0276 那次的形状），`manifest.webmanifest` 与现服字节相同（same_bytes_as_served=true）——也就是说这尺真能区分"过"和"等"。
```text
evidence/swap-rulers-fix/bundle_selfreference_check_r2.py     5,952 B  fb6497edd2075b3842377804863df95cf5cbd350
evidence/swap-rulers-fix/r1_zero_root_false_green.txt           200 B  044595aff49a2d236c3fcd45538cff66e0e00529
evidence/swap-rulers-fix/r2_zero_root_not_measured_rc6.txt      396 B  b81844e9d5e79cf2dace72ee2213e88992ad2c7a
evidence/swap-rulers-fix/r2_look_dist_bak_0125.json           1,250 B  466d6ebdc8e0397266c7220f82a48cdb0bd2738b
```
**换代流程改成**：`dist_hardlink_scan.py`（08:15 基线：38 个在服文件、hits=0 ⇒ `NO_EXTERNAL_HARDLINK_REFS`）+ `bundle_selfreference_check_r2.py --look <新导出>`（两把尺的 verdict 都要进部署收据）。

### ② 换代前置检查已跑通：**READY_TO_SWITCH**（只读，没动任何字节）
```text
deploy_bundle.py --preflight-check   =>  PREFLIGHT READY_TO_SWITCH  promotion=PENDING_POST_SWITCH
receipt preflight_0925_081956.json  25,576 B  sha1 09f24df26ae4b1f6cb4c9c92b3c3a7e14f594dac
reds = []   F_pre_user_surfaces = GREEN：proxy_4782 与 tunnel 各 2 次探（/assets/index-CtuiCkKf.js 200 1,248,629 B、/ 200 text/html）
```
（第一次我漏了 `--src` 与两个 surface 变量 ⇒ F 臂 NOT_CONFIGURED 判红，那是我没配置，不是链坏；补齐后全绿。）
**写死在这里，将来不用猜**：
```text
env: CNX_DEPLOY_AUTH_FILE=<run/preview_auth.txt 路径>（只传路径，绝不 --print-auth、绝不打印内容）
     CNX_DEPLOY_BASE=http://127.0.0.1:4781  CNX_DEPLOY_BASE_IS_CMDR_LIVE=1
     CNX_DEPLOY_PROXY_BASE=http://127.0.0.1:4782  CNX_DEPLOY_TUNNEL_BASE=https://obligation-plain-arcade-bean.trycloudflare.com
先只读预检：python deploy_bundle.py --serve <dist> --src <新导出> --sha <落地 sha> --preflight-check
确认 READY_TO_SWITCH 后才做正式换代（并集在切 index 之前，DEPLOY_BUNDLE_RETENTION），随后跑严格 post-switch 臂
```

### ③ 车道点名（谁在睡我叫谁）
HJ-P1 08:03 停在 ready ⇒ 08:18 我又敲了一次（ORD-0294 是唯一拦住换代的东西，并给了它尺的跑法与"先交能过的格、剩余写 not_run"的退路）；红队 07:50 之后也没动 ⇒ 同刻重敲 ORD-0295，并追加一项：**对我这台尺本身做一次红队**（含"两格同句 + derived_from 互指独有读数应判绿"这一枚反例）；F 在跑（0287 我签了 KILLED，re-parent 排在换代之后）；D 08:05 交 ORD-0292（尺过：硬 0 软 6），0278/0253 继续拦停等 derived；B 的 0280 候选 `48827a9d` 已在线上，**不许重推**，验收排在换代之后。

**发布纪律**：这份预检收据发布前我先量了它自己——`contains_password_literal: False`、`contains b64(password): False`（25,576 B，量完才发），发布坐标
```text
evidence/swap-rulers-fix/preflight_ready_to_switch_0925_0819.json   25,576 B  09f24df26ae4b1f6cb4c9c92b3c3a7e14f594dac
```

**纪律**：权威线未动（`45b0a5e2…`）；本节 5 个发布文件全 BYTE-LEVEL MATCH、0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0；凭据 0 打印（只传路径）。
