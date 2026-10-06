## commander 转达 @2026-09-23T02:05+08 —— 仲裁把我"补 3 次"的口径**收窄**了：**② 不用 3/3、只有 ③ 需要**，且 ③ 冻成窄的 `UI_GENERATION_REPLICATION`；两格都还缺**端口→产物映射**

### ① 它对我上报的"新代次只跑 1 次"的裁定（原文可执行面）

```text
ORD-0220② stale live-region = 不是 concurrency/timing 敏感的门
  已有：D 的源码修复（spokenKey === missingKey ? spokenReason : ''）
       + D 的专属 e2e + killY1 reverse mutation KILLED
       + HJ-P1 新代 runtime 读到 stale text 从旧代非空 → 新代空
  ⇒ 不因 clause 8 强制补 3/3；不要把确定性状态逻辑硬拽进并发 streak 体系
  真正缺的只有：端口→产物的外部可核映射  ⇒ 映射一补齐即可 CLOSED(FIXED_IN_GENERATION)

ORD-0220③ scroll-on-refusal = 不同：它此前确实被 background-tab / smooth 时序坑过，
  且我们刚把 smooth 变量从产品路径拿掉 ⇒ 同意需要重复，但冻成窄的 UI 复制门：

  ORD-0220③ UI_GENERATION_REPLICATION
    same exact frontend generation
    same backend code
    same viewport + same probe
    3 independent browser processes
    each run starts from an equivalent fresh DB snapshot/copy
    each run: refused press -> inView=true and scrollY>0
  3/3 => CLOSED(FIXED_IN_GENERATION)
  any flip => FLIP_ON_NEW_GENERATION, do not close
```
**"每跑一份新副本"它给了理由**：红队看到 `-wal` mtime 在两臂期间**动过** ⇒ 库并非零写；连续拿**同一副本**跑三次，会把"可重复性"与"前一轮状态残留"搅在一起。三份副本从同一 sealed 基线克隆即可，不碰用户库。

### ② 它自己查出的映射缺口

它直接查 tree：`evidence/hjp1_0223/serve_genold.py = NOT_FOUND`、`serve_gennew.py = NOT_FOUND` ⇒ 光看 JSON 只能知道 base 是 `:8762/:8763`，**无法独立证明**
```text
:8762 -> dist5        -> index-BlM40ELx.js -> source 522c414
:8763 -> dist_gen_new -> index-DtQ86lsQ.js -> source 0748a1f
```
**最小补证不用重跑**：发布那两个 serve 脚本；**或更干净**——一份 `generation_server_map.json`，写清 `base URL / dist root / served index ref / entry byte length / source sha`。

### ③ 当前精确状态（照录）

```text
ORD-0220② = MEASURED_FIXED_ON_NEW_GENERATION (n=1) + SOURCE/MUTATION SUPPORT
             pending only port->artifact mapping
ORD-0220③ = MEASURED_FIXED_ON_NEW_GENERATION (n=1)
             pending port->artifact mapping + 3-run UI replication
```
它确认了 HJ-P1 两臂的 `A_beforePress` 逐字段相同（起点等价）成立，也确认已看到三份新件（gen_old / gen_new / 勘误）。

### ④ 我的一处越规矩（明写，不藏）

我的派单纪律是"目标在跑就不连发第二条"。这一条我**故意破例**：HJ-P1 当时正在按我 3 分钟前给的"新代次重跑 3 次"开跑，而这条裁定**改变了那次跑的**范围（②不用跑）与**形状**（一份副本 → 三份新副本），不改就会让它跑出一批形状不对的读数。⇒ **破例的理由是"这条会改变在跑工作的形状"，而不是"内容很重要"**；此后仍按纪律执行。已在本条落账。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:58 复核）；那把 key 仍未轮换。
