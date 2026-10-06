## commander 订正 @2026-09-22T15:5x+08 —— 上一条部署块里"我只做了 1 轮、所以不签三次连点"这句话已经过期：**三轮独立循环我做了，这一格我改签 `REPRODUCED(canary)`**

上一条（15:4x 块 ③）写的是"我这遍只做了 1 轮 ⇒ 不签『三次连点 0 新建』"。**15:49–15:50 我把那三遍补齐了**，形状就是 HJ-P1 提醒的那个（不是同页点三次）：

```text
每轮 = 点「试用其他城市」重进向导 → 找到「使用封存的天津演示」→ scrollIntoView → elementFromPoint 命中自身 → click → 等 3s
round1: 14 requests / POST=0 / GET /api/v1/journeys/22222222-…-222222222222/experience / 落点 /v8/hub / rect [20,706,335×44]
round2: 14 requests / POST=0 / 同一条 experience 寻址 / /v8/hub / rect [20,706,335×44]
round3: 14 requests / POST=0 / 同一条 experience 寻址 / /v8/hub / rect [20,696,335×44]
三轮合计 POST = 0；canary 副本库 journeys/travelers/plan_versions 跑前跑后 = 3 / 3 / 19
```

⇒ ① **ORD-0209 的"入口不再偷偷新建行程"这一格从 `PENDING` 升为 `REPRODUCED(canary 运行时)`**——不是我 15:4x 说的"1 轮不算"；② 我 15:4x 块里"我不签三次连点"那句**作废**，以本块为准；③ 仍未做的两格不变：`tight` 档在主页的运行时证据（只有 D 的 e2e 与我的代码级阅读），以及**手机真机**那一格（旧 service worker 可能仍给一次旧界面，重开即新）——这两格我不打包成"已完成"。
④ 现场：`56d20ec` 仍是 working tip；线上 bundle `index-BCF4ptyk.js`；`:8693` 未重启（仍 `53fe8e8`）；用户 `_live.db` 只读复查 3/3/19；canary 两进程已停，副本库与 `canary_dist/` 留下作证据。
⑤ 另记我自己一条仪器坑（写给所有车道）：**在 bash 里用 `python -c "…"` 拼中文正文时，正文里的反引号会被当成命令替换吃掉**——我 15:5x 就是这么把一份总线正文里的所有 `代码段` 静默删掉的（长度对不上才发现）。凡是带反引号/引号的文件内容，用 Write 工具落盘，别在 `-c` 字符串里拼。
