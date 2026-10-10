仲裁: SESSION=494abfd7（Commander）— 一条**部署缺陷类**要你定规则（我自己造出来又自己关掉的），加两条读数。镜像 sha1 `ce370336dcede8b8`。

## ① 换包会打断旧缓存客户端：`DEPLOY_BUNDLE_RETENTION`（请裁成常驻规则，不开单）

我把 `dist` 整目录换掉之后，第一件事不是"用户看到新界面"，而是**旧 bundle 的 URL 还在被旧 index.html/旧 SW 引用**。实测：

```text
GET /assets/index-CnfHH2K_.js（旧包，换包后第一把）-> 200 但 1200 B —— 内容是 SPA 回退的 index.html，不是 JS
⇒ 状态码 200，监控与 e2e 都看不出问题；旧缓存客户端拿到 HTML 当模块 ⇒ 白屏
```

处置（已做，复测过）：把 `dist_bak_1538/assets/` 用 `cp -n` **只补不覆盖**地并回线上 `dist/assets/` ⇒ 旧包 `1,228,395 B` 且是真 JS，新包 `1,230,082 B` 正常，`/` 仍引用新包。`/v10-sw.js` 的 precache 只列新包、带 `skipWaiting`＋`clientsClaim` ⇒ 最多再装载一次。

建议冻结成一条部署前置检查（措辞我按你的口径写，你可以改）：

```text
DEPLOY_BUNDLE_RETENTION
a dist swap must keep the previously-served bundle assets reachable (union, never overwrite)
post-swap receipt must assert: old bundle URL -> 200 AND body is JS (size > 100 KB, not HTML)
                                        new index.html references the new bundle
                                        registered SW's precache list names the new bundle
```

理由：这三条缺任何一条，"已部署"就只是文件换了，用户那侧可能是白屏——而这是我们最不该第二次踩的坑（09-21 的 SW 服务 HTML 已经是一次同类）。

## ② 两条读数

- **B 的四条红在 `56d20ec` 上 0 条恢复**（我自己跑：`-k "g14a or g14c or g10 or city_failure"` ⇒ `4 failed, 6 passed, 1168 deselected`，分母 1178 与 HARNESS 那把同）。B 已回到 running，按 ORD-0215 交。
- **线上新包我用眼睛看过了**：把线上 `dist` 挂到隔离口＋副本库 canary，390×844 走完入口，截图读屏——整屏没有 `每人每天约` 那行（从渲染文字算，不是从 class 猜）。**顺手抓到一条新线索**：演示入口落地那趟封存行程，地图那格写"尚未获取地图位置/这个行程还没有可信的坐标"⇒ 官方演示入口的落地页地图是空的。这条我不自己定级，已交给 HJ-P1 判（改前/改后基线在它手上）；若判要修，靶子在 demo 行程的坐标链，不在前端。

## ③ 现场与点名（16:29）

`running`＝B、D、HARNESS、红队区｜`ready`（16:05–16:17 被我叫醒后已各走一轮，账本尚无新交付块）＝C（ORD-0213 仍未 CLAIMED）、F（按你 16:10 的顺序：0210 机制先）、HJ-P1、HJ-P3、HJ-P4、LAB
`仍 cold`＝**HERMES `9baacb24`（两次点名后）· HJ-P2 `d4b04a0f`** ⇒ 我再各敲一次；若仍不动，我把"车道不响应"当事实报给你和用户，不替它们编 blocker。
working tip 仍 `56d20ec`（16:15 两棵树同 SHA）；reference tip `c0d7e3d`；`P7=false`；`:8693` 未重启（`53fe8e8`）；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次 provider 出网；canary 进程验完已停；那把 key 仍未轮换。

竭尽所能的替qoder铺路
