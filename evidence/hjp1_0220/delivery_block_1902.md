# HJ-P1 交付块（ORD-0220 ②③ 各 2/2 复跑）— 由 Commander 代发（原车道只读，不 push）

来源：账本 `CITYNEXUS_AGENT_DELIVERY` 块 `### 1a986a24 HJ-P1 ORD-0220 ②③ 各 2/2 复跑 + 按新规则声明证据坐标 @2026-09-22T19:02+08`
发布者：Commander `494abfd7`（该车道约束为只读，`publish_evidence.py` 只能由我运行）
原始坐标声明（车道自报）：
  522c414102fa956a0af7c4e5567da2b6badfccfd  ← 包所出自的树
  25165d9e193b61ba9751f946272d555543cf0444  ← 当前工作尖
  git branch -r --contains 522c414 => 0 条 ; 25165d9 => 0 条
  git remote -v => origin = D:/moodle/CityNexus (本地路径), iso = D:/moodle/_qoder_th_20260918 (本地路径)
  ⇒ LOCAL-ONLY, no resolvable coordinate（比"没 push"更糟一层：这条线的 origin 本身是本地目录）

## 两格各 2/2（同一序列、两个独立页面会话；pass2 前先 removeItem 草稿再 reload）

| 读数点 | pass 1 | pass 2 |
|---|---|---|
| 被拦瞬间 .trial-required-hint 的 y / 高 | y=1221 / h=85 | y=1221 |
| 是否在视口内（视口 844） | inView=false | inView=false |
| 此刻 scrollY | 0 | 0 |
| 同屏 sticky 主按钮「下一步」y | 652 | 652 |
| 改成有效值后 .v8-sr-only 里 | 「还需要填写：总预算」 | 「还需要填写：总预算」 |
| 进第 3 步后：可见 .trial-required-hint 实例数 | 0 | 0 |
| 进第 3 步后：.v8-sr-only 含该句 | 1（仍在） | 1（仍在） |

ORD-0220 ③（提示渲染在折叠外）＝仍在，2/2（累计 4/4，与 50b35e0 同型）：解释条 y=1221、视口 844、sticky 按钮 y=652，产品既不滚动也不聚焦。
ORD-0220 ②（sr-only live region 不重算）＝仍在，2/2：字段当场改好后读屏节点仍写「还需要填写：总预算」。

## 给 D 的两条断言（车道原样给出）

```ts
const hint = page.locator('.trial-required-hint');
await expect(hint).toBeVisible();
const box = await hint.boundingBox();
expect(box!.y + box!.height).toBeLessThanOrEqual(844);

await budgetInput.fill('420');
const stale = await page.evaluate(() =>
  [...document.querySelectorAll('.v8-sr-only')].filter(e => (e.textContent || '').includes('还需要填写：总预算')).length);
expect(stale).toBe(0);
```
车道注：特意没写 `expect(locator).toHaveCount(0)`（本车道记过该写法会挂）。

## 栈与合规

包 dist5/assets/index-BlM40ELx.js（从 522c414 出；构建前后从仓库根读 `git status --porcelain frontend/src` 均 0 行）
当前尖 25165d9 与 522c414 之间 `git diff --name-only -- frontend/src` = 0 文件（那是一笔 docs(review)）
后端 127.0.0.1:8751 + 代理 8752；库 _hjp1_o220.db；AI=disabled、DEMO_MODE=false、key 清空、无隧道、无 provider 出网
本轮 0 次创建：库前后都是 journeys 44 / travelers 59
