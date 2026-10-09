## commander 转达 @2026-09-23T03:36+08 —— 仲裁 `5782717232`：**`real_phone_gate_preflight.json` 签 `ACCEPTED-EVIDENCE`**；**ORD-0239 选 (iii) 且要拆成四个正交事实**（不能把 `HYDRATABLE` 硬改成"有没有数据"）；含 9 项验收矩阵 ＋ 服务端 parity 门 ＋ 排序

### ① 那份小收据被签了

它读的是 blob **`4b07d036e2f83666ed67e69b0de812dfd748c43f`**（2,806 B），并**逐字段重核**：`/v10-sw.js` 200 text/javascript 2,096 B、precache = `index-DtQ86lsQ.js` + `index-cWMF3pBW.css`；`/` 200 text/html 1,200 B、asset_refs 同代；current JS 1,231,985 B、sha256 `cf3a08108ffba413…`；`/sw.js` 7,178 B、`prod_registered=false`、`carries_hashed_index_assets=false`；retention CURRENT `DtQ86lsQ` / PREVIOUS `BCF4ptyk` / N-2 `CnfHH2K_`；`tech_preconditions = MET`。
⇒ **`real_phone_gate_preflight.json = ACCEPTED-EVIDENCE`**。**闸门仍只差用户那一跳；清理 0 删除。**

### ② ORD-0239：裁 **(iii)**，但**不是**把 `HYDRATABLE` 硬改成"有没有数据"

它要求把"可用性"**拆成四个正交事实**：
```text
identity / catalogue-readiness / hydration-capability / user-visible support
⇒ UI 只能消费【最终 support state】
```
**按 support state 的推荐行为（照录）**：
```text
LIVE_READY / DEMO_READY
  -> 可直接选择；DEMO_READY 必须明示"演示数据"
HYDRATABLE_ON_DEMAND
  -> 可以列，但标签必须是"需要加载数据"
  -> 选择后先 hydrate；hydration 成功并【重新判 READY】后才进入后续向导
UNAVAILABLE
  -> 不出现在"支持目的地"，或以 disabled / coming-soon 单独展示
```
⇒ **这是 (i)+(ii) 都要，但有先后**：**先修名单 truth，再把 capability 后端做成能可靠驱动名单的多轴事实**。
**压轴**：**`HYDRATABLE` 不是"可用"的同义词，`GOLDEN_FIXTURE` 也不是 LIVE。**

### ③ `RECOVERY_COSTLY` 并进 ORD-0239（不另开同源单）

理由：11–13 次交互才能换城、且向导是浮层无可回退路由，与"错误的 support 承诺"是**同一个用户伤口**。关闭条件加：
```text
如果 hydration/availability 在选择后失败：
  保留用户已填字段 / 显示具名 reason /
  <= 1 个显式 in-app action 返回城市选择或打开城市输入 /
  不要求重走 11-13 步
（沿用 SECONDARY_SURFACE_RECOVERY 精神，不再发明恢复哲学）
```

### ④ 验收矩阵（它直接给实现车道）

```text
A. READY live city            -> listed/selectable
B. DEMO fixture city          -> 只以 DEMO 标签列出，绝不声称 LIVE
C. RESOLVED + 0 eligible + hydratable -> 不得宣传为"立即可用"；需先 hydrate 再继续
D. UNRESOLVED identity        -> 不进 supported list
E. 未知城返回 HTTP 200 []     -> support_state != READY
F. 突变：把不可用城硬塞回 supported list -> UI parity 门 RED
G. 突变：把 DEMO_READY 折叠成 LIVE_READY -> provenance 门 RED
H. 突变：把 200 [] 当成 READY  -> readiness 门 RED
I. 恢复：失败的 hydration 在 <=1 个显式动作内回到城市选择且草稿保留
```
**另加一条服务端 parity 门**：前端显示为可选的 city codes，必须是后端 `support_state` 可选中集合的**子集/精确投影**——**不能靠两份名单"碰巧一样"**。

### ⑤ 排序（它点名）

**不要打断 C 正在补的 `G3_XPROC_LOSER_READBACK`。** ORD-0239 先由**只读 / HARNESS 车道**把 **11 城矩阵 ＋ 后端 support contract 规格**钉出来；**等 C 的 identity closure 完成后**，再由 owning backend 车道落 `support_state`。**D 只消费契约，不自己推断 `place_count` / canonical identity。**
**ORD-0240 方向维持**：模型原文是动态内容，**不能塞进静态翻译表冒充已翻**；中文 UI 要么生成/呈现中文摘要，要么把原文放进明确标注的"模型原始输出/技术详情"。

### ⑥ 我的派单落地（本轮）

- **ORD-0239** 状态：`SPEC_PENDING`，**归只读车道（HARNESS）先钉矩阵与契约规格**；实现在 C 的 identity closure 之后开单（**我会挂 `blockedBy: C 的 G3_XPROC_LOSER_READBACK`**）。
- **ORD-0240** 已派 D，方向与它一致（不塞翻译表）。

### ⑦ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
