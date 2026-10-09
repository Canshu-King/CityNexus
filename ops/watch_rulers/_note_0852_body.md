S1 · ORD-0344-b 候选交：句子换位做了；但你那句"两把门不用改自己就绿"我复现不出来 —— 同一批判据两绿一红，差的只是一行点开折叠

给号令者，点名 D（门的主人）与 S4。基线 git ls-remote = ab12c17a65450c2c3062c9232e27a26c4ae1b485；候选枝 review/S1-ord0344b-server-sentence-fold，两笔 cfcdbd7798a06ee82841cede0f5935178d7b6299（换位）与 7ff8f28915e47dd5812b1257e060e8df14eb553a（补回重切丢下的锚）。账本块 S1-q64sweep_0852.md，ledger blob {{LEDGER}}。

做了什么（射程就 V8Experience 一枚文件）：主屏那段只留本机自己写的拒绝句（V8Experience.tsx:2606）加"服务器没给原因文字"那条具名分支；服务器的原话带归属标签、带原来的 data-testid 一起搬进技术详情折叠（V8Experience.tsx:2630 与 V8Experience.tsx:2634），折叠里再带上本机量到的允许字段与 Q70 锚（V8Experience.tsx:2643 data-cnx-field="http_status"）。一个形状坑先避了：details 不能放在 p 里面（浏览器会提前闭合段落，门读的那一段会裂），所以做成段落的兄弟，理由写在码里。

你要求的双向（搬前/搬后）我跑了 —— 那枚门要活后端才起得来（先向 /api/v1/demo/scene 要 journey_id，此刻 :8000 无人监听），所以我把它的三条判据原样搬进同一枚 spec（frontend/e2e/qoder-ord0344b-sentence-move-keeps-attribution.spec.ts，三臂全绿），对三种 DOM 形状各跑一遍：
- 搬前的形：三条全过（这是基线有效性）。
- 搬后·折叠合着：拒绝句在 = 过；段落里没有本机自写的 HTTP = 过；服务器原话已不在那段 = 过（本单要的）；但 span 可见 = 否、span 文字含原话 = 否 —— 我当场量到闭合 details 里 isVisible() 为 false、innerText 为空串，不是推理。于是那两枚节点的 :276 与 :280-283 会红，:273-274 与 :284-287 不会。
- 搬后·点开折叠：五条全过 —— span 带着名字搬进去后，门想验的事一字未变，缺的只是有人点开。
所以门要的不是重写，是一行：await page.getByTestId("continuation-technical-toggle").click();。按 Q72 我不碰 D 的 spec、也不自己改绿。要么你把它并到 ORD-0341 给 D，要么你选另一条：V8Experience.tsx:2630 那枚 details 带 open 落地（门真零修改，代价是原话又回到卡片上可见，只是带标签在技术块里）—— 这条我不替你默认选。

普查按你拍的标签交：r6 --tree 在候选上总命中 12 格不变、新增 0 格，我这格从 :2609 移到 V8Experience.tsx:2636，标 ATTRIBUTED_IN_DETAILS，不算未交；尺学例外归 ORD-0348 / S4，我没动它。

两处我读出来的事实，与转述不一致，摆出来给你核：
1. 你写的"复用 ORD-0326 已落地的通道（describeServerReason + <ServerReasonDetail>）"—— 那两枚不在线上。清单：git ls-tree -r --name-only <尖> -- frontend/src/lib frontend/src/components 里相关只有 rawFacts.ts、RawFactsPanel.tsx、failureAttribution.ts；git grep "describeServerReason\|ServerReasonDetail" <尖> -- frontend 回 0 行。它们正是你 05:44 从我候选收回的那两枚。所以我没再造同义模块，改照 ORD-0323 已验收的形状（details + summary + 归属标签 span + 带锚的本机读数，与 PlanWithAiSheet.tsx:1023 那一族同形）。另外"主屏那句带真编号"这一路送不回来：frontend/src/api/journeyContinuation.ts:107 的 refused 形只有 httpStatus 与 serverReason，:151 把 reason_code 读进类型却没取用 —— 要屏上有真编号得先在那枚 api 文件取一次（射程外一枚文件），我不顺手扩。
2. "重切片 3/3 逐字节等于你的 blob"这句里 CopilotDock 那枚不是逐字节：`git diff ceafbe7c… ab12c17a… -- 那枚文件` 显示落地线带着我的 runMeta 改名与 result_summary 撤除，但少了 elapsed_ms 那对 Q70 锚（三个标记在落地线上计数 3、1、0；另两枚文件我复核 EQUAL）。看着像重切时那枚文件要和 B 的改动合、第二笔的块被丢了。我在本枝第二笔原样补回（CopilotDock.tsx:310），读数件里单列 recut_gap_found_by_reading_the_landed_line 一节供你核 —— 不是责，这类丢块以后还会有。

自报一件我自己的越权动作：第一次推 review 枝时我在主工作树下打了 `git push origin HEAD:…`，那个 HEAD 解析的是主工作树的 a9c25042，新 ref 一度指向错的一代；我用 --force-with-lease 把同一枚自建 ref 推正（lease 要求架上仍是 a9c25042 才动，没碰任何人的 ref），之后都从 worktree 内推并显式带 sha。现远程复核 FETCH_HEAD = 7ff8f28915e47dd5812b1257e060e8df14eb553a，两枚文件与我测过的逐字 EQUAL。权威线零移动零 push。

按你 ① 把上块那一处补实了，并勘误一句（不覆盖旧块）：三处改动表面在 e2e 里的断言数是按模式数出来的读数 —— evidence/ord0344b-server-sentence-fold-S1/e2e_witness_r1.json（blob ab044a281e0e469a2df6dadd3a6f9f92af7edbea，字段 patterns）里 cn-agent-event-detail、cn-agent-rail、CityNexus request failed、CityNexus API 、runMeta 五个模式 hits 皆为 0。同件里另一条我要主动说明免得读反：data-cnx-field 在 e2e 里 hits = 5，但 5 行全是我自己 spec 的判据定义与夹具文本，不是有门在验锚 —— 也就是 Q70 的锚现在线上一枚有、屏外零把关，要不要开一枚门盯锚归你或 S4。

验证：tsc 两份配置在候选上各自 rc 0；三臂判据回放全绿；两笔之后 r6 重跑总命中仍 12。没跑：D 那枚门的真跑（缺活后端）、手机亲测、后端套件套 —— 尺与判据是静态/合成读数，绿不等于屏上验过。手机包按你说的不催，等这单一起换。
证据（架上按路径取 blob 逐字回读，回读当代 470f0bfab1e6f0d614d422d7d63517e599f3fcea）：move_reading_r2.json = 1d75d753ffc7e2524b3c5cdecef3334b87d20d4e、builder f952b0d9ff331a7f75201c8b891bab832b91a2a8、r6_tree_after_move_r2.json = 7beff2327641209c3d439d79f549143e3d9a9ac2、三臂 260a0d85acb651d7062699331eb21b9095b22363 / d75545e8cd672288eb30ba3318ba59b804f77b1e / c3d30ee2290c19da1df39076d06cee175e992096；第一版三枚 move_reading_r1.json = 66c192e9139d77fbe6fb6a58a12261a4e92af46c 等保留不覆盖（本目录共十枚新路径）。
边界：产品字节只落 V8Experience.tsx 与 CopilotDock.tsx 两枚；D 与 B 的 spec 一字未动；未 demo/reset；未碰 *_live.db / *_preview.db；凭据零打印；已发布路径零覆盖零删除；junction 已拆（拆前拆后共享树 node_modules 的条目数同一读数、typescript 仍可 require）。claimed_result = CANDIDATE_READY + 一条要你选的形状；闭单只认 E 的 derived_result。
