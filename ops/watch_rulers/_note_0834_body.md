S1 · ORD-0344 交：三格收敛（r6 全树 15→12、新增 0、每格带 Q70 锚），第四格我不收敛，交回一枚三面互斥的裁定

给号令者，也点名 S4（量具）与 D。基线现读 git ls-remote = c740f45d68f337c460a1a43b995162689d0110af（枝从它开）；交块时尖已前进到 e9a392db4f596362ffe3365174e1fef1366f3247，按你的话不重切：候选枝 review/S1-ord0344-q64-fanout，两笔 110c4323d99509c9a957ed42f4d01022b8fef0c3 与 ceafbe7c0e20fe6fc6fc19d66785d5c696833034。只读预合 `git merge-tree --write-tree e9a392db… ceafbe7c…` rc 0、无冲突文件；我碰的文件在两代之间逐枚 blob 全等。账本块 S1-q64sweep_0834.md，ledger blob {{LEDGER}}。

收敛三格（每格都证了"改前那代真报过、改后不报"，两份读数都是尺本体 --tree 跑的）
- frontend/src/main.tsx:968 与 frontend/src/main.tsx:992：那两处本来渲染 `error`，而 `error` 装的是旧 errorMessage() 的返回值 —— 服务器原话 `body?.error?.message` 或异常句子 `error.message`。现在这屏只说自己写的话加自己量到的允许字段：main.tsx:985 与 main.tsx:1018 挂 `"data-cnx-field": "http_status"`（值是量到的那个状态码），文字在 main.tsx:987 / main.tsx:1022。
- frontend/src/features/agent/AgentRunRail.tsx:18：那枚槽本来叫 `detail`，正是上游放句子的字段名；现在改成本屏的话（AgentRunRail.tsx:10 `runMeta?: ReactNode`、AgentRunRail.tsx:21），唯一调用方不再把服务器自撰的 result_summary 放进 DOM（CopilotDock.tsx:323），并且这屏真显示的步长数字带上契约名锚（CopilotDock.tsx:310 `"data-cnx-field": "elapsed_ms"`，值是原始毫秒）。
Q68 一并守住：没量到就没有那对锚，也不写任何编号。全树：r6 15 格 → 12 格，消失的正是我这三格，新增 0 格，别的车道名下 11 格一格未动（集合差在件里）。

要你拍的一处（第四格我不收敛）：frontend/src/app/V8Experience.tsx:2609。那行在 `V8Experience.tsx:2607` 的 span 里先写「服务器给出的原因：」再拼 `resumeOutcome.serverReason`（来源 frontend/src/api/journeyContinuation.ts:152 的 `detail.error.message` / `detail.detail`）。三条章在这一格互拉：Q64/Q70/Q71 要我收敛；Q67=① 说带归属标签的服务器原话是合规归属；已上线的门还把 Q67 两面钉住 —— frontend/e2e/qoder-continuation-resume-carries-identity.spec.ts:281 要求那枚 span 真带原话，:285 又要求这段文字里不许出现本机自写的 HTTP 三位数。所以删正文 ⇒ :281 红；把 http_status 写成文字 ⇒ :285 红；只挂 data-cnx-* 不动文字 ⇒ 尺仍按 jsx-text 报这格（Q71 也不许把正文挪进属性）。我没替你挑一条，也没动那枚 spec（Q72 你已定：门的断言只有门的主人改，且你明写拒绝由我顺手改 D 的字）。要收敛请二选一开单：① 以 Q64 为准、supersede Q67=① 在这一格的适用；② 以 Q67=① 为准、让尺学会"带归属标签 + 技术详情面"这条例外（量具归 S4，我一个字不动）。

实际意义我自己在前头说：件里 reachability 按行读出 —— main.tsx 那两格只在 /legacy 路由挂载（main.tsx:1698），旅客屏未变；AgentRunRail 那格在旅客路径上（CopilotDock.tsx:402 挂它），那才是今晚旅客真能少看到一句上游话的地方；第四格也在旅客路径上而我没动。

验证与未验证：两份 tsc（tsconfig.check.json 与 tsconfig.typecheck.json）在候选树上各自 rc 0，补锚之后重跑仍 rc 0 且 r6 命中集合与补锚前逐格相同。我改的三处表面在 e2e 里 0 处被断言（grep cn-agent-event-detail|cn-agent-rail|CityNexus request failed|CityNexus API 无输出），所以这一单不需要再来一张 ORD-0341。没跑：任何要活后端的套件套（此刻 :8000 无人监听）与手机侧亲测 —— 尺是静态判据，绿不等于屏上验过。
反控：读数件量具把改前基线置空再跑必须 ABORT（"cell 1 … is not a hit in the BEFORE run"），它真 ABORT —— "改后绿"签不出从没红过的基线。
一处我的读法错误，记不删：第一次回读架上文件时 FETCH_HEAD 比发布器落 branch 的时刻旧（拿到 e9a392db），按路径取 blob 报"不存在"；改用 origin/commander/control 重取后全部逐字相等（回读当代 eaca1cbd87a190ea5febbe92f6defa39de5511cd）。
证据（架上逐字回读，只新增 evidence/ord0344-q64-four-cells-S1/ 六枚）：cell_reading_r3.json = 64c5050b941d497ed3a21cfb7caf2b223d44e7a9、builder b36ec13e08a77f186111977cd8dd041ecbc3b457、改前 r6_tree_before_r1.json = 57127e69723ca8a9905b0b9b5ea1142c5bc0e905、改后 r6_tree_after_r2.json = cfa1ca9bbc536875556f302e2f517046ab81a411；早期两版 cell_reading_r1/r2 = 3e86719e5c6e414cb7b20eafd109fb1f6bd03c82 与 ea31650d5c88eaa6cd028198e7b3c256a75fe101 保留不覆盖。尺与普查原件按引用 blob 取回后未改一字：6a251d3a6bea70329e06581384a81d5ef54c96a6 与 95c6c24639ed0fca8f8bad4a2fc1fd6f863b3e0d。
边界：产品字节只落我名下三枚文件；权威线零移动零 push；V8Experience 与 D 的 spec 一字未动；未 demo/reset；未碰 *_live.db / *_preview.db；凭据零打印；已发布路径零覆盖零删除；junction 已拆（拆前拆后共享树各 394 枚条目）。不宣布 CLOSED：最多 claimed_result = 三格 CANDIDATE_READY + 一格 NEEDS_RULING，闭单等 E 的 derived_result。
