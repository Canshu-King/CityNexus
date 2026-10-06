## commander 小事三条 @2026-09-23T03:48+08 —— ORD-0239 的矩阵产物已发布；端口身份复核仍是我的链；清掉我自己三个僵尸 shell

### ① ORD-0239 的输入产物（可读）
`evidence/ord0239/city_matrix.json`（blob `0711667c0f939b09`，3,023 B）。它的**列是分归属的**：
- `place_rows_measured_by_commander_on_the_phone_chain` —— **我自己在用户链上量的**（北京 8 / 演示城 8 / 杭州·东京·福州·苏州系 0）；
- `identity_and_capability_column_measured_by_lane_4e974ae5` —— **标注为它的读数、明确写"未被我独立复测"**（含 3 座身份给不出、8 个宣传码在任何 city 列都不出现、capability 分不出能用/不能用）；
- `trees` 字段写清 **手机链＝三值**、**活线＝四值** 以及两棵树各自的 head 与文件 sha；
- `code_reading_by_commander`（`anywhere_capability.py:74/823/13`）＋ `arbiter_ruling_ref`（`5782717232` 选 (iii)、四轴事实）。
**规矩**：**矩阵里每一列都必须能追到"谁量的"**——不把我的读数与车道的读数混成一列。

### ② 端口身份复核（我一直在说的"链还是我的"这条，四小时后再验）
```text
:4781  pid 56212  vite preview --outDir D:/moodle/_qoder_preview_20260920/dist --port 4781
:4782  pid 20364  python preview_auth_proxy.py          ← 我轮换口令后重启的那个
:8693  pid 55960  python -m uvicorn app.main:app --port 8693
⇒ 三条都仍是【我的链】，PID 与 01:26 记录一致，没有车道抢用户的端口。
```

### ③ 我自己留下的三个僵尸 shell（已清）
`netstat`/进程盘点时发现：**22:51 那次重建链的命令**留下了 3 个 bash 进程（PIDs `55816` / `56188` / `57324`）——它们是 `grep … tunnel.log | head -1` 这类**在日志上阻塞**的残留，挂了约 **4.8 小时**。
⇒ 按**具名 PID**清掉，回验 `still alive: 0`。**是我自己产的、我自己清**（生产者自清同规矩）。以后重建链的命令要带 `timeout` 或用 `grep -m1`。

### ④ HARNESS 不是卡住（避免我误杀）
`d291c9dc` 的 revision 停在 24 已十余分钟，但**它正在跑三轮全套＋两门×10 进程**（长套件期间 revision 本来不涨）。按我写下的判据（revision 不变 **且** 产物 mtime 不变才算卡住），**这一格只有一半成立（缺产物侧读数）⇒ 不动它**，下一轮再看。

### ⑤ 现场
链三条端口在听；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
