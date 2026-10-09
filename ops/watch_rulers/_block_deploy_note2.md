## commander 部署补记 @2026-09-22T16:2x+08 —— **把"手机可能白屏"这条我自己造出来的风险关掉了**（换包会让旧 bundle 变 404→HTML，这是刚量到的）

刚测到的一件与我 15:39 那次换包直接相关的事实（先报，因为它是**我引入的**，不是车道的）：

```text
换包后第一把：GET /assets/index-CnfHH2K_.js（旧包）-> 200 但只有 1200 B —— 内容是 SPA 回退的 index.html，不是 JS
=> 任何仍持有旧 index.html 的客户端（旧 SW 缓存、没被 precache 命中的子资源）去要旧 bundle 时，
   拿到的是 HTML 当 JS ⇒ 白屏风险，而且状态码是 200，监控看不出问题
```

**处置**：把 `dist_bak_1538/assets/` 的 js/css **只补不覆盖**地并回线上 `dist/assets/`（`cp -n`，4→8 个文件），做完复测：

```text
GET /assets/index-BCF4ptyk.js -> 200  1,230,082 B  是 JS
GET /assets/index-CnfHH2K_.js -> 200  1,228,395 B  是 JS（旧包又可达了）
GET /                      -> 200  index.html 内引用 = assets/index-BCF4ptyk.js（新包）
```

**关于"要不要重开一次"的口径，现在有读数了**：线上 `/v10-sw.js`（App 注册的那支）里 precache 只列 **`assets/index-BCF4ptyk.js`**，且含 `skipWaiting`＋`clientsClaim` ⇒ 手机最多再走一次装载就会切到新包；旧包我又留了可达副本，所以**这一次装载不会白屏**。
仍未做的两格不变：`tight` 档在主页的运行时证据（ORD-0216 ①，归 D），以及**用户真机眼睛**看到新主页（我签不到那一格，只能签到"链上服务的是新包＋旧包可达＋SW 会自更新"）。
现场：working tip `56d20ec`；`:8693` 仍未重启（`53fe8e8`）；用户库 3/19/3；护栏 `demo/reset` 403 PREVIEW_GUARDED、匿名 401；0 次 provider 出网；16:17 我已把仲裁 16:10 的 F/C 顺序令转达并叫醒 F、C，B 已回到 running。
