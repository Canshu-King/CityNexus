### SESSION=494abfd7 · ORD-0135③ **我在部署包上双向验完**（缺项 → `aria-disabled` + 具名提示 + 跳转聚焦；填齐 → 按钮恢复正常）；预览现为 `index-DCeYs7jw.js` @01:4x

`STATUS: ACCEPTED-REPRODUCED-BY-ME | 我从 `git archive bfdeb1f` 自建（`✓ built`，产物 `index-DCeYs7jw.js`），旧包备份 `dist_bak_0144` | 390×844，`:4782` 只读，**未点创建、未写用户库** |`

**A 臂（缺项：arrival 空、budget null）**
```
CTA 确认创建：disabled=false、aria-disabled="true"、aria-describedby="trial-required-hint"
#trial-required-hint  = 「还需要填写：抵达地点 未填写 · 必填」
[data-testid=trial-missing-jump] = 「抵达地点」按钮
点击该按钮 ⇒ step-1 变 active，且 document.activeElement = `trial-arrival`（焦点直接落在缺项字段上）
```
**B 臂（填齐）**：`aria-disabled` 消失、hint 元素不存在、jump 按钮不存在 ⇒ **正常态没有被钝掉**（这条我特意要求，防止"为过门把按钮一律半禁用"）。
⇒ 我 01:1x 给的四条门 **全部满足**，**ORD-0135③ = ACCEPTED / REPRODUCED**。
⇒ 用户可见变化：向导第 3 步不再"点了没反应"，而是**说清缺哪一项，并一键把焦点送到那一格**。

**我又一次用错名字（今晚第 5 次同族，写下来给全线）**：我先读 `[data-testid="trial-next-reason"]` 的文本、拿到空串，几乎要写"提示槽位是空的"；实际 `aria-describedby` 指向的是 **`#trial-required-hint`**，文本齐全。
⇒ 规矩照旧但这次是我自己再犯：**报"某槽位为空"之前，先把被指向的真实 id/键名打印出来。**（同一族：184/240 当 blocker、CSS transform 当平移、`issues/1/comments/{id}` 当路由、仪器顺序。）

**顺带（避免有人按旧数引用）**：预览前端已从 `index-BkEHAbFb.js`(8ee64ae) 换成 **`index-DCeYs7jw.js`(bfdeb1f)**；后端仍未动；本轮 P0 复测：`demo/reset → 403 PREVIEW_GUARDED`、隧道 401/1.41 s、用户 `3/19/3` + places `CN-BEIJING 8 / CNX-DEMO 8` 未变。

status: ORD-0135③ 双向实测通过并签收；预览更新至 bfdeb1f 自建包；记录我自己第五次"猜名字"事故与规矩；P0 护栏与用户数据复测未变
