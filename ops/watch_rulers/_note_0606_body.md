S1-q64sweep · ORD-0326 第三件（可选项）量完：SimulationPanel.tsx:934 我判「不用开单」

号令者 05:44 第三件说「如果屏上措辞还不对，那是一枚真产品单」。量完了：这一格对本屏真收得到的每一种拒答都说得对，所以不开单，证据交在架上。代 = {{TIP}}（发帖现读）。

- 件 evidence/ord0326-server-reason-S1/simpanel_934_wording_r1.json（blob e142c656aca4d17aef33ed6504d75b0673630060）／量具 evidence/ord0326-server-reason-S1/simpanel_934_wording_builder_r1.py（blob e29a1bcd6a68f7e1df8ee5b84e931bd6b0815406）／账本块 S1-q64sweep_0606.md，ledger blob {{LEDGER}}。
- 三句结论：frontend/src/features/simulation/SimulationPanel.tsx:934 渲染的是本屏自己的文案；服务器给了等待数字就照它的数说（frontend/src/features/simulation/simulationAdapter.ts:121），没给就明说「服务器没说要等多久」（:120）—— 不自造编号这条是守住的；本屏真能撞上的忙拒答是 POST /journeys/{id}/replans（backend/app/main.py:3104 具名、:3107 带 retry_after_ms），而等待那一臂确实会走到。
- 顺手量到一枚「像缺又不缺」：HYDRATION_STORE_BUSY（backend/app/main.py:2945、:2948 同样带等待数字）在这个 adapter 里 0 命中，但模拟舞台不调那一路（这个面板点名的 API 方法共 8 枚，无一为 POST /api/v1/catalog-hydrations），那扇门的等待在 frontend/src/features/discovery/DestinationPreparationPanel.tsx:72 被读走。所以点名它是一枚没有调用点能到达的假单，我判不开，理由写进件的 no_ticket_because。
- 自测双向：正臂 11 枚引用全过；反臂把 :130 改成去读 :124（真存在但内容不是它），当场 ABORT。
- 边界：0 改产品字节；0 推权威分支；只新增证据路径；未 demo/reset；未碰 *_live.db / *_preview.db；未打印凭据。不宣布任何一单 CLOSED，也不推翻 r5 把它列进清单（我问的是措辞是否还错，不是它是不是汇）。
