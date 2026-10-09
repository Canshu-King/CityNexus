### SESSION=494abfd7 · 向导"缺项态"实测（给 ORD-0135③ 的证据，含一条我认为不致一致的地方）@00:1x

`STATUS: COMMANDER-OBSERVATION-NOT-A-DEFECT-VERDICT | 目标：部署后的生产包 `index-BkEHAbFb.js`，390×844，`:4782`（只读浏览）| 我**只改自己那个浏览器档案的 `localStorage` 草稿**，未点「确认创建」、未向 `:8693`/`_live.db` 写任何东西 | 结论只到我量到的范围 |`

#### ① 我先量了"什么都不缺"的样子（免得把正常态当缺陷报）
草稿完整（厦门 / 2 人 / 总预算 CNY 1500 / 住宿 450 / 抵达 高崎机场 / 离开 厦门北站 / step 3）⇒
`trial-step-1..2 = done`、`step-3 = active`、**CTA 可点**（`disabled=false`、cursor pointer、opacity 1）、
`trial-next-reason` **存在且为空** ⇒ 这一态**完全正常**，我不报问题。

#### ② 再把必填项抹掉（`arrivalLocation=''`、`budgetMajor=null`）后重载，量到的是：
| 读数 | 现场 |
|---|---|
| 缺项有没有被**点名** | **有**：屏上写「抵达 **未填写 · 必填** · 2026-09-25 11:00」⇒ 比"哑按钮"好，这一半已做到 |
| 主行动按钮 | `确认创建` 仍然 **enabled**（`disabled=false`、无 `aria-disabled`、`cursor:pointer`、`opacity:1`） |
| "为什么不能提交"的槽位 | `[data-testid="trial-next-reason"]` **存在但内容为空字符串** |
| 无障碍 | 无 `role="alert"`；没有任何 `trial-jump*` / `*missing*` 控件可跳到缺项 |
| 后端 | 我**没点**创建 ⇒ 服务器会答 422 还是客户端会拦，**我不知道，也不去试**（那会写你的库） |

#### ③ 因此我只提一条**一致性**问题（不是"缺功能"指控）
屏幕已经说得出"这一项必填未填写"，**但主按钮的外观与可点状态完全不反映这件事**，而产品自己预留的 `trial-next-reason` 槽位是空的。
⇒ 这就是 ORD-0135③ 的正身：**把已经知道的"缺项"接到按钮与播报上**，而不是新做一套判断：
- 有缺项 ⇒ CTA `aria-disabled="true"` + `aria-describedby` 指向 `trial-next-reason`，并把那句"抵达未填写·必填"原样填进槽位；
- 每个缺项一个可聚焦跳转（"去补这一项" → 回到对应步骤并聚焦字段）；
- **不许**用 `disabled` 把按钮打死（我们仓里 `aria-disabled` 才不会被 `click()` 挡住，也才可聚焦可读——见 ORD-0066 的旧结论）；
- 若产品策略允许"点了再报"，那也必须**点了之后把原因播报出来**，不许静默。

#### ④ 门（给 D 直接抄，两条都要求"先红后绿"）
1. `arrivalLocation` 为空时：断言 CTA `aria-disabled="true"` **且** `trial-next-reason` 非空、文本含"抵达"与"必填"；
2. 断言存在可聚焦的"去补这一项"控件，点击后对应字段 `document.activeElement` 就是它；
3. 突变：只留"未填写"文案、不给按钮上 `aria-disabled` ⇒ 必须红（防"文字改绿、状态还是能点"这种半修）；
4. 反向不变：草稿完整时 CTA 必须保持 enabled（别为了门把正常态也钝掉）。

status: 向导缺项态实测完成（缺项已点名 / 按钮状态与 reason 槽位不反映 / 无播报无跳转）；给 ORD-0135③ 四条可直接抄的门；未点创建因而不判定后端行为
evidence: 本轮两次 evaluate 原样读数（完整态 vs 缺项态对照）
