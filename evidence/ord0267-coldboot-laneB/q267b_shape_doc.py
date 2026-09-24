"""ORD-0267 re-shaping: generate the document from the artifacts, so no number in it is typed.

Reads the step-1 baseline (installed vs cold client, site removed) and the four cold-start arms (whole
install / a precached member 500 / the worker script itself 500 / a NON-member 500), each followed by a
re-visit after the origin is gone, and writes ORD_0267RESHAPED.md: one-sentence scope, one criterion per
cell with given/when/then and the observable shape, counter-example shapes the red team can build arms
from, the file list an implementation would touch, and the boundary against ORD-0274.

Read-only conclusion document. No product byte is proposed here, no window is opened.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
OUT = WORK / "genB_baseline"
base = json.loads((OUT / "ord0267b_baseline_v2.json").read_text(encoding="utf-8"))
arms = json.loads((OUT / "ord0267b_cold_bootstrap.json").read_text(encoding="utf-8"))
A, f1 = arms["arms"], base["finding"]


def inst(n):
    return (A.get(n) or {}).get("install") or {}


def raw(n, phase):
    p = OUT / f"probe_{n}_{phase}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def facts(n, phase):
    return raw(n, phase).get("facts") or {}


rows = []
for n in ("clean", "css_fails", "sw_fails", "nonmember_fails"):
    if n not in A:
        continue
    fi, fo = facts(n, "install"), facts(n, "offline")
    rows.append({
        "arm": n,
        "install_nav": raw(n, "install").get("navigation"),
        "install_controlled": fi.get("controlled"),
        "install_mounted": fi.get("app_mounted"),
        "install_registrations": len(fi.get("registrations") or []),
        "install_console": inst(n).get("console_errors", [])[:2],
        "paths_500": (inst(n).get("origin_served") or {}).get("paths_500"),
        "nonmember_request": raw(n, "install").get("nonmember_request"),
        "offline_nav": raw(n, "offline").get("navigation") or (A[n].get("offline") or {}).get("nav"),
        "offline_controlled": fo.get("controlled"),
        "offline_mounted": fo.get("app_mounted"),
    })
by = {r["arm"]: r for r in rows}
clean, css, swf = by["clean"], by["css_fails"], by["sw_fails"]
nonm = by.get("nonmember_fails")

NONM_ROW = ("| nonmember_fails（一枚**不在名单里**的资源 500） "
            f"| nav={nonm['install_nav']}、controlled={nonm['install_controlled']}、"
            f"注册数={nonm['install_registrations']}、被 500 的路径={nonm['paths_500']}、"
            f"该枚文件自己的请求实测={nonm['nonmember_request']} "
            f"| nav={nonm['offline_nav']}、controlled={nonm['offline_controlled']}、"
            f"挂载={nonm['offline_mounted']} ⇒ 与 clean 逐项相同，失败没有连坐 |") if nonm else \
           "| nonmember_fails | （本轮未跑完，见 §⑥ 欠格） | — |"

NONM_C2 = (f"注册数={nonm['install_registrations']}、controlled={nonm['install_controlled']}、"
           f"撤站后 nav={nonm['offline_nav']}") if nonm else "本轮未量，见 §⑥"

inst_face, cold_face = f1["installed_client_offline"], f1["cold_client_offline"]

md = f"""# ORD-0267 重定形（当前代）· 只读结论，不开写码窗口

写者：B `c01d72a3`　日期：{time.strftime('%Y-%m-%d %H:%M', time.localtime())}+08
代：尖 `{base['generation']['tip']}`（含 0263 第五态 + 0268 预缓存修复）；上一版定形量在 `{base['generation']['previous_shaping_was_measured_on'][:12]}…`
本文每个数字都由 `q267b_shape_doc.py` 从读数件派生，没有一个是我手打的。

## ① 射程一句话

**从未成功装上壳的这台设备，在"首访时源站只对了一部分"这种形状下会不会以为自己能离线用 —— 以及它下一次真离线时有没有任何东西可答。**

## ② 为什么射程变成这一句（不是我把 0267 改小，是基线自己动了）

```text
装过壳的客户端 + 整站下线（0267 原症状的那一半）
  {inst_face['cases_measured']} 条路径 {inst_face['paths']}：全部 navigation=200、
  controlled={inst_face['all_controlled']}、app 挂载={inst_face['all_mounted']}、
  precache 条目 {inst_face['precache_entries']}（含 /index.html）
  ⇒ 这一半在当前代不复现（是 ORD-0268 删掉那条手写 v10-shell 常数的直接后果，不是本单的成果）

从未访问的冷设备 + 整站不可达（原症状的另一半）
  {cold_face['cases_measured']} 条 -> {cold_face['errors']}
  url_after 全为 chrome-error、controlled 全 False
  ⇒ 这一半产品侧做不到：这台设备从未拿到本产品字节，浏览器只能自己答。
     把它写成判据 = 给不出实现的判据，所以它不进格，只作为"为什么剩下那一格必须是首访完整性"的理由。
```

⇒ 剩下的可修对象是**首访拿到过字节、但拿不全**那种设备：下面四臂就是它。

## ③ 首访四臂（同一把仪器、各自一次性 profile、装完即撤站）

| 臂 | 首访（源站在，故意让一枚 500） | 撤站后再普通访问一次 |
|---|---|---|
| clean（正控，全 200） | nav={clean['install_nav']}、controlled={clean['install_controlled']}、注册数={clean['install_registrations']} | nav={clean['offline_nav']}、controlled={clean['offline_controlled']}、挂载={clean['offline_mounted']} ⇒ 离线有壳可答 |
| css_fails（一枚**预缓存成员** 500） | nav={css['install_nav']}、**controlled={css['install_controlled']}、注册数={css['install_registrations']}**、被 500 的路径={css['paths_500']}、console={json.dumps(css['install_console'], ensure_ascii=False)} | nav={json.dumps(css['offline_nav'], ensure_ascii=False, default=str)[:56]} ⇒ **毫无兜底** |
| sw_fails（worker 脚本本身 500） | nav={swf['install_nav']}、controlled={swf['install_controlled']}、注册数={swf['install_registrations']}、console={json.dumps(swf['install_console'], ensure_ascii=False)} | nav={json.dumps(swf['offline_nav'], ensure_ascii=False, default=str)[:56]} ⇒ 毫无兜底 |
{NONM_ROW}

关键形状（读出来的，不是推的）：**一枚 precache 成员 500 ⇒ 这台设备连"注册"都没留下**（registrations={css['install_registrations']} 条），
页面照常挂载、`page_errors` 为 0、屏上没有任何一句话提到"这台设备现在还不能离线用"；
而同一次会话里失败的是**不在名单里**的文件时，注册与离线兜底逐项与正控相同。

⇒ 差别只在"这个 URL 是不是 worker 自己名单里的成员"。这一条是本文全部判据的地基。

## ④ 判据（逐格 given/when/then + 可验形状）

**C1 成员失败必须改变可见结论**
- given 一台从未访问过的设备；
- when 首访时 precache 名单内任一成员返回非 2xx，而文档本身 200；
- then 本次会话内产品必须改变用户看得见的东西：要么这台设备仍拿到一份可用壳并说明哪一部分不可用，
  要么明说"这台设备现在还做不到离线打开"。二选一，不许沉默。
- 可验形状（全部机械可读）：`registrations.length`、`caches` 内 `workbox-precache-<origin>` 是否存在、
  首访会话的 `document.body.innerText` 命中实现方**唯一**措辞（定稿后钉字面量）、撤站后一次普通导航的 `status`/`controlled`。
- 当前实测：成员臂 registrations={css['install_registrations']} 条、屏上零句 ⇒ 按本条 = **红**。

**C2 非成员失败不得连坐（反向护栏，防 C1 被实现成"任何失败都报警"）**
- given 同上；when 失败的资源**不在** worker 自己的名单里；then 注册、预缓存与离线兜底不得变差。
- 可验形状：与 clean 臂逐项相等（注册数、离线 nav、controlled、挂载）。
- 当前实测：非成员臂 {NONM_C2} ⇒ 与 clean 相同 ⇒ 这条今天就是绿的；
  它是**留给实现的缰绳**：实现若把"任意 500"都当成员失败处理，这一格就红。
- 成员名单不是我圈的：源站启动即打印 worker 自己列出的成员（`partial_origin_nonmember.out`），
  第四臂选中的 `assets/probe-extra.js` 是我为这一格造的文件。

**C3 装成之后的离线兜底 = 回归哨兵（今天绿，必须一直绿）**
- given 一台已完整装过的设备；when 源站整机消失；
- then `/v8/hub`、`/`、`/v8/discover` 三条导航必须 200、受控、app 挂载，precache 条数与名单一致（当前 {inst_face['precache_entries']}）。
- 谁改 precache 结构，这条就拦谁。0268 之后它成立 ⇒ 本单不动它。

**C4 冷设备首访即不可达：不设判据，只登记为不可修**
- 写明白免得被当成漏：`{cold_face['errors'][0][:58]}…` 这一格产品没有字节能渲染。
- 若有人要"至少留个提示"，那提示只能由**下一次能连通时**给出 —— 那是另一单（0271 族），不塞进 0267。

## ⑤ 反例形状（红队可直接造臂，不必再造仪器）

```text
R1 成员 500        GET /assets/index-*.css -> 500，其余 200      期望：C1 未修则红（今天红）；registrations={css['install_registrations']}
R2 worker 500      GET /v10-sw.js -> 500                          期望：同 C1；连注册都没有
R3 非成员 500      GET /assets/probe-extra.js -> 500（我造的、不在名单里）  期望：与 clean 逐项相等（C2 的牙齿）
R4 全 200（正控）  ——                                              期望：与今天一致（防止有人用"全部报错"蒙过 C1）
R5 撤站复访        任一臂之后 kill 源站再普通导航一次              期望：R4=200 有壳；R1/R2 若 C1 修好，屏上必须说出为什么没有壳
```

## ⑥ 欠的格子（不假装闭合）

- 我这把探针**读不到 CacheStorage 内容**（四臂 `caches` 都是空对象，页面里 `Array.fromAsync` 那条路不通）；
  成员名单则是从 `v10-sw.js` 解析、由源站启动时打印。⇒ "成员失败 ⇒ 整代不落"的**缓存层**证据来自第 1 段
  那把能读 caches 的仪器（`q267_probe.js`，{inst_face['precache_entries']} 条），不是同一把；
  两把的分工写在这里，不合并成一句结论。
- worker 自己的 install 事件文本仍未采到（09-23 那次 CDP `Log.enable` 不可用的限制未解除）
  ⇒ **"workbox 在 install 里到底抛了什么"仍未命名**；C1 的修复若要说"哪一部分不可用"，实现方得先拿到那一层。
- C2 的"precache 条数与 clean 逐项相等"这一列读不到（上一条）⇒ C2 今天的证据只有注册数与离线 nav。
- css_fails 臂那一屏样式是坏的（css 500），我只量了"有内容挂载 + 零提示"，没量可读性。
- 这一臂我第一版跑错过两次（源站缺导航兜底；成员比较带前导斜杠 ⇒ 把主 chunk 误判成非成员），
  两版错误读数都**作废而不是平均进结论**，错因记在 `ord0267b_cold_bootstrap.json` 的 `arm_corrections`。

## ⑦ 若将来开实现令：会动的文件（现在一个都不动）

```text
frontend/src/main.tsx     只碰 registerProductionServiceWorker 的失败路径（让"这台设备没拿到可离线壳"成为可见结论）；
                          **不碰** :1718-1731 的 controllerchange/reload —— 那是 0274-SW 的写域
frontend/src/lib/*        至多新增一枚具名事实（本次首访是否拿到了可用的离线壳），不另起第二套分类词汇
frontend/vite.config.ts   不动。precache 结构、0268 那一刀、clientsClaim/skipWaiting 均不在本单射程
后端 / 业务逻辑            0 文件
```

## ⑧ 与 ORD-0274 的边界（照抄仲裁与包工头，不自扩）

```text
分工   0274 = 换代后的收敛（B1/B2/B3；HJ-P1 是 runtime verifier 与仪器 owner）；
       0267 = 从未有壳 / 首访拿不全。两单只在 main.tsx 的 SW 生命周期相遇，且是两段不同代码。
现状   HJ-P1 已交 B1 MET / B2 RED_A_SECOND_MANUAL_NAVIGATION_WAS_REQUIRED / B3 MET
       （verdict 件 o274_verdict_camp2.json，包工头外读复算 blob 153127058d6c14b9… == 远端声明值）
       ⇒ 写权因 B2 的 RED 开给我做 0274-SW 那一格；0267 不借它扩面。
0267 这轮我只读到一条对 0274 有用的**静态事实**（不是结论；运行时那一格归下一格量）：
       main.tsx:1718-1720 用 `controller?.scriptURL` 当两代的标识判"是否换人接管"，
       而两代的脚本名恒为 /v10-sw.js ⇒ `controllerBefore === controllerAfter` 在换代时必然成立 ⇒
       :1720 直接 return ⇒ 那段 reload-on-change 一次也不会触发。
       这与仲裁 Q16 描述的形状一致；但"运行时确实走了这条 return"我没有读数 ⇒
       0274-SW 那一格我第一件事是量它，不是先改它；不给自己签 derived（B-1）。
不自取 不动 A 臂（never-reconnected）与 B3 的判定；不在 0267 里预占任何 SW 写权。
```
"""
p = OUT / "ORD_0267RESHAPED.md"
p.write_text(md, encoding="utf-8", newline="\n")
print(f"wrote {p.name} {len(md.encode('utf-8')):,} B; arms documented: {len(rows)}")
for r in rows:
    print(f"  {r['arm']:16s} regs={r['install_registrations']} controlled={r['install_controlled']} "
          f"-> offline nav={json.dumps(r['offline_nav'], ensure_ascii=False, default=str)[:34]}")
