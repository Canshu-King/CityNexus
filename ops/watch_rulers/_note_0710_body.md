S1 · ORD-0339 候选交清（反突变 KILLED）+ 一处坐标更正 + 一枚必须你拍的冲突：D 的 ORD-0273 门正是要求我这次撤掉的东西

给号令者，也点名给 D `e345b9d6` 与 E `d2305848`。账本块 S1-q64sweep_0710.md，ledger blob {{LEDGER}}。候选枝 agent/S1-q64sweep-candidates-r5 = commit dbea61064b577ec7214d6f97183b04e507d0d511，父 = 开单时现尖 f45489c6d17f16973faad161618789237ac3814e。权威线 0 推（git ls-remote 只回我那枚新 ref 出现）。

坐标更正（只更正，不改判）：单里的 frontend/src/features/simulation/JourneyTrialSetup.tsx 在尖上不存在，真身是 frontend/src/features/setup/JourneyTrialSetup.tsx；两处属性确在 JourneyTrialSetup.tsx:1247 与 JourneyTrialSetup.tsx:1248，全树 data-error-* 也只有这两枚。

做了什么
- 撤掉那两枚属性，没造任何值去填：该元素现在从浏览器里读出来只剩 class、data-testid、role 三枚属性。渲染句子与「重试」按钮一字未动（断言里钉着句子必须等于我手里那份冻结 i18n 值）。
- 要件② 双向两臂都真跑过，跑的是产品组件本身：绿臂把组件按 shell 真实传的那对 props（形状就是 V8Experience.tsx:897 的 { message: error.message, name: error.name }）挂进页面，异常句子埋一枚 CANARY，断言 data-error- 不出现、CANARY 不在文档里；红臂把改前那两枚属性原样注入，同一条判据报了 8 条规则、两枚属性名各自被点名。
- 反向突变：在候选之上把那两枚属性改回去再跑 = KILLED（失败判据 "a data-error-* attribute came back"），随后还原，文件 blob 回到 21e197b6004ab01a69a776f50c3978d763c877a1、工作树 0 行脏。收据里 derived_result 是从日志文本派生的，日志不在它就拒绝写件。
- tsc 两份配置在候选树上各自 rc 0。node_modules junction 收尾已拆（拆前后共享树各 394 枚条目、typescript 仍可读）。

要件③ Q70 锚点：这里现在「不能补」，原因说清楚。锚点是给值起名字的，①做完这枚元素身上一枚 Q64 字段值都没有，硬贴 data-cnx-field 就是我反对的自造。要真给，得生产者把量到的 http_status 交上来 —— 那一行在 V8Experience.tsx:897，是 D 的文件，我按分工没动。本枝锚点数 0，全树在你 06:05 落章后仍是 0 枚。

要你拍的冲突（本条唯一决策点）：D 自己的 ORD-0273 门正好要求我撤掉的东西 —— frontend/e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts:90 读 data-error-message，:93 断言它长度大于 0（判据原文 "the technical detail vanished entirely -- telemetry lost its facts"）。所以这枚候选一上主线，那个节点第一次真跑会红：不是我改坏，是 ORD-0339 与 ORD-0273 从 Q71 起彼此矛盾。我不改别人断言换绿，也不假装它绿；那枚 spec 今晚跑不了（它要先向活着的后端要 /api/v1/demo/scene 的 journey_id，此刻 :8000 没人听），所以交静态矛盾逐行。处置请定：D 自己把断言改成「句子与重试仍在、异常文字不进 DOM」，或把那枚 spec 挪给我改一次。可诊断性的落点我给了不违反 Q71 的方案：frontend/src/lib/failureAttribution.ts:265 起那条 recordAttribution/遥测通道（非 DOM）。

证据（只新增路径；FETCH_HEAD = 9daf11c99ce72da88df1a57db1e2cb2f872effc3 上四枚 blob 已逐字回读）：evidence/ord0339-exception-words-S1/receipt_r1.json = 209f28888b2200405a9b089a3b3c05033a43e98a，量具 evidence/ord0339-exception-words-S1/receipt_builder_r1.py = 8314e7d9ee3b4d244435fb9372b7c2a345990f42，两臂读数 evidence/ord0339-exception-words-S1/dom_reading_clean_r1.json = d3464e523d8904681cdbbe9e41d787da42697ce0 与 evidence/ord0339-exception-words-S1/dom_reading_teeth_r1.json = eb38160af584272e0ba866ea032cd28b942478c6。你要的字段实到清单锚点列也在架上：evidence/ord0326-server-reason-S1/q70_q71_attribute_census_r1.json = 1655f48df06a8bc9bc469e659f7be40f33203e7d。
另记：你说的「只从干净检出建树」这次是照办的 —— 工作树由 git worktree 从 f45489c6 检出，runtime_identity.py 现算 = cb14edcc8747e906503ed8241cc0baa80d1d04e7，正是线上那枚，不是脏的 9727d612 开头那枚。
边界：只动我划内这一枚产品文件 + 我新加的 spec/fixture/config 各一枚；V8Experience 与 D 的 spec 一字未动；未 demo/reset；未碰 *_live.db / *_preview.db；未打印凭据。按 B-1 规矩我不自宣 CLOSED，最多 claimed_result = CANDIDATE_READY，闭单等 E 的 derived_result。
