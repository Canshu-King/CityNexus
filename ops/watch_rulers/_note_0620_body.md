S1-q64sweep · 按 Q70/Q71 落章后的第一次量：锚点全树 0 枚、清单补上锚点列、另有一枚你新 binds 的异常文字面要派活（不在我文件里）

给号令者（③④）也顺手给 F 与 S4。代 = {{TIP}}。

量到的三件事
- Q70 那一列：frontend/src 里带表达式的 data-* 汇共 145 枚（19 枚文件、78 个属性名），`data-cnx-field` 这名字全树 0 处 ⇒ 按「谁少了锚点算」，现在每一枚承载者都缺锚点。字段承载者（值被读实之后确认的）：http_status 2 枚（frontend/src/components/RawFactsPanel.tsx:29、frontend/src/features/planning/PlanWithAiSheet.tsx:1060）、content_type 2 枚（:30、:1061）、body_bytes 2 枚（:31、:1062，键面拼的是 bytes 不是契约名，字节数真是字节数：frontend/src/lib/rawFacts.ts:24）；response_received、elapsed_ms、request_id 三枚全树没有承载者。
- ③ 预言的坑我拿到了样本：只按属性名认，会有 5 枚候选读错。data-elapsed-seconds 两枚（PlanWithAiSheet.tsx:959、frontend/src/features/setup/JourneyTrialSetup.tsx:1142）其实是本机秒表（:384 的 useState、:589 的 useElapsedSeconds），主体与单位都不是服务器的 elapsed_ms；data-status（frontend/src/features/discovery/DestinationPreparationPanel.tsx:456）与 data-result-status（PlanWithAiSheet.tsx:1007）是作业状态词，不是 HTTP 状态；PlanWithAiSheet.tsx:909 的 data-request-length 是旅客自己输入的字数（方向相反，且是字符不是字节）。
- Q71 新 binds 的那一面有一枚要派活：frontend/src/features/setup/JourneyTrialSetup.tsx:1248 的 data-error-message 装的就是被 catch 异常的 message，链路我逐行读了（frontend/src/app/V8Experience.tsx:897、:898 写进去，形状在 JourneyTrialSetup.tsx:339），V8Experience.tsx:891 那段注释本身就写着「raw error.message 留在 data-* 里」—— 这是 Q71 之前被当合规设计、06:05 ④ 之后正好被点名的那一类。同元素 :1247 的 data-error-name 是异常名，同一个类。两枚都在 D 那一片，按现行分工我不动，只点名。

给 S4 的一句话（只报不修）：r6 表头第 65 行（blob 6a251d3a6bea70329e06581384a81d5ef54c96a6）自己写明属性插值不算汇，第 64 行的汇只有 JSX 文字子节点、dangerouslySetInnerHTML、textContent/innerText/innerHTML ⇒ Q71 刚 binds 的这一类今天没有任何一把尺看得见，这不是漏，是当时设计成不管。要不要开一单把汇集合扩到 data-*，你和号令者定，我不动你的尺。

需要你拍一个形（不拍我只能继续只量）：一枚元素同时带好几枚字段时锚点长什么样没定 —— 我的 data-attribution 一行里同时有 attribution_reason、evidence_kind、http_status、source_layer、retryable、recovery_action，有 server_code 与 content_type 时再多两枚。我倾向「允许 data-* 放六个字段的 key=value 行，但每枚字段各挂一枚锚点」，这样不动渲染文本、我那两枚文件加几行就合规、也不逼 B 改中文标签。你拍完我立刻补我自己的两枚并交双向件；B/D 那两片归他们。

件：evidence/ord0326-server-reason-S1/q70_q71_attribute_census_r1.json（blob 1655f48df06a8bc9bc469e659f7be40f33203e7d）／量具 evidence/ord0326-server-reason-S1/q70_q71_attribute_census_builder_r1.py（blob 07d29f7844d89e60ddb6e5c4f1a5a31fe0051f3e）／账本块 S1-q64sweep_0620.md，ledger blob {{LEDGER}}。
自测双向跑过：正臂 145 枚汇 + 13 枚裁决全过；反臂把 rawFacts.ts:22 的 trace 引用错读成 :25 当场 ABORT，反臂清空短名单读数从 8 掉到 0。
边界：0 改产品字节；0 推权威分支；只新增证据路径；未 demo/reset；未碰 *_live.db / *_preview.db；未打印凭据；S4 的尺与别人文件一枚字没动。另纠正我自己那张表的一处口径：body_bytes 在「我那两条腿」上确实 NOT-EMITTED，但全树已有实现，F 别以为前端没有字节数。
