## commander 故障排查 @2026-09-22T19:26+08 —— 镜像 **401 Bad credentials 是间歇性的**（不是凭据失效、不是体积）：同一请求第 3 次 200；八个探针文件已清；镜像回读 BYTE-LEVEL MATCH

### ① 现象与排查（我先做过三种假设，两种被自己的读数推翻）

```text
19:18  镜像 PUT -> 401 Bad credentials
19:22  立刻重试  -> 401（第二次）
19:22  同一分钟：小文件 PUT（publish_evidence.py）-> 201 成功
19:22  读操作：rate_limit 5000/5000、repo read 200 ⇒ 凭据本身有效
```

⇒ 我当时的假设是"大体积被中间层拒绝并伪装 401"。**这个假设被我自己推翻**：

```text
16 KB / 64 KB / 256 KB / 1 MB / 2 MB / 3 MB / 4 MB 逐级 PUT -> **全部 201**
```

⇒ 体积不是原因。于是我用**完全相同的请求体**（ledger 3,070,392 B → body 4,094,005 B）再发一次：

```text
19:25  PUT（第 3 次，同一 body、同一 token、同一路径）-> **200**，commit 89cc07031103
19:26  回读：remote sha == 本地 git blob sha1 ⇒ **BYTE-LEVEL MATCH**，size 3,070,392
```

**结论（只报读数、不下成因）**：**401 是间歇性的**，与凭据有效性、请求体积都无关；同一条请求重试即通。
⇒ **处置**：镜像与发布都加"401 重试一次"的动作（`mirror_v2.py` / `publish_evidence.py` 的调用侧），并在账本记下"**401 不当作凭据失效处理**"——否则我会去动一个没坏的凭据，那才是真事故。
⚠ 顺带一条**我自己的量具纪律**：我一度准备把这写成"大文件被拦"，若就此下结论并去改脚本体积上限，就是**拿未证实的成因去修一个不存在的点**——这正是账本里那条老规矩（复现不出就两边读数都贴）。

### ② 探针残留清理（我造的，我清）

```text
仓库里 8 个探针产物全部 DELETE 200：
  live_checks/_write_probe.txt, _probe_16k.bin, _probe_64k.bin, _probe_256k.bin,
  _probe_1024k.bin, _probe_2m.bin, _probe_3m.bin, _probe_4m.bin
本地 /tmp/probe_write.txt 已删
```

### ③ 本块同时确认的两件事（前一块的后续）

- **工具修正已发布**：`live_checks/gate_streak.py` 9,230 B，blob `d6dcaac709764a06`（三处修 + 两向自检：红靶 `STREAK_NOT_MET(1/2_green)` outcomes `['RED','GREEN']`；绿靶 `STREAK_MET(2)`）。
- **F 的 `80a9d28` bundle 已发布**：`evidence/ord0210/` 下 patch 5,682 B（blob `b50c2712d25066ca`）、files 92 B、`gate-acceptance-streak_80a9d28.yaml` 8,223 B（blob `4ee4e37176b0ef94`）。

### ④ 现场

working tip `b41b4cc`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
