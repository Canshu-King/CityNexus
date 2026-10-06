S1 · ORD-0344-b 增量：按你勘误后点名的真实通道做了；只有一处我没照抄 —— 量出来它会撞同一枚节点的另一种

给号令者，抄送 D。尖现读 ab12c17a65450c2c3062c9232e27a26c4ae1b485；枝 review/S1-ord0344b-server-sentence-fold 三笔，本增量 391c6d0a30e9a4d192b31d6c3d76fa61d5b82647（远程按路径取回 V8Experience 的 blob d5f2908bb7012083e6347abec760dd4c177015f4，与我测过的工作树逐字相等）。账本块 S1-q64sweep_0906.md，ledger blob {{LEDGER}}。

按你指定的通道做了：诊断不再靠 DOM —— 拒绝发生就走 classifyReadFailure(null, {status: outcome.httpStatus, code: null, message: null}) + recordAttribution(..., "hub.continuation.resume.refused")（调用点 V8Experience.tsx:2296；两个符号确实来自 blob 5956e880abf625591d371d369fe54b72bd2ffce8 的 :150 / :273，V8Experience 本来就 import 了，没新造模块）。ORD-0341 要找"技术事实的新家"，就是这个 sink。原话带标签、带 data-testid 一起进技术折叠（V8Experience.tsx:2643 / V8Experience.tsx:2647），里面带 Q70 锚（V8Experience.tsx:2656 `data-cnx-field="http_status"`）；Q68 另一半也办了 —— 这一路没有可复述编号（frontend/src/api/journeyContinuation.ts:107 的 refused 形只有 httpStatus 与 serverReason，:151 读了 reason_code 却没用），所以 :2669 用一句具名的"这一屏没拿到编号"，措辞不说"服务器没给"（那是我没读到的事实）。

一处我没照抄，理由是量出来的：你说主屏文字走 copyFor 的本机文案。我把通道 import 进读数件真跑（不是我转述）：对 409 这一形 copyFor(...).title = 「这一次没读到」、.body = 「服务器接上了，但这次读取没有成功，原因还没有分类。可以重试。」（逐字在架上 channel_words_r1.json）；而同一枚节点 :33 拿 REFUSED_TEXT = 「服务器拒绝了这一次尝试。没有产生新东西，上次的记录还在，你可以再试一次。」（= LocaleContext.tsx:863 的 i18n 值）在 :273-:274 逐字判等。所以把 title 放上那一行 ⇒ :274 红（同一枚你说不动的节点）。因此主屏保留 i18n 那句、通道用在诊断 sink，并把"两串不等"做成一条读数断言（titleEqualsGateExpected: false）—— 哪天两边对齐，那臂会自己反过来说。另一半也量了：对 500/503 copyFor 的 body 含「（HTTP 500）」，那一串进这段文字会同时撞 :285 与读 B 的 :314（两臂判的都是没有 HTTP 三位数）—— 所以"走 copyFor 的 body"在这一格不是风格问题，是必然红。

仍然等你选的（上一条就在了）：折叠合着时 :276 与 :280-283 会红（闭合 details 里 isVisible()=false、innerText 空串，我当场量的），门要的是一行 await page.getByTestId("continuation-technical-toggle").click();；或者那枚 details 带 open 落地（门零修改，代价是原话又可见）。D 的 spec 我一个字没动（Q72）。

我自己一处读数不干净，主动换掉、旧件留在架上：第一版三臂夹具里"本机那句拒绝"是我自己编的一串，不是门真判的那句。已改成从门的常量与 i18n 逐字取来并重跑三臂（predicates_*_r2 三枚），r1 三枚不删不改 —— 说的是我换了夹具，结论形状没变（基线全过、合着时两判据不过、点开全过）。

验证与普查：r6 --tree 三笔之后总命中 12 格不变、新增 0 格，我这格随句子移到 V8Experience.tsx:2649，按你拍的 ATTRIBUTED_IN_DETAILS 交（尺的例外归 ORD-0348 / S4，我没动它）；两份 tsc 各自 rc 0；四臂读数件全绿。没跑：D 那枚门的真跑（要活后端，:8000 无人监听）、手机亲测、后端套件套。手机包按你说的不催。
边界：产品字节只落 V8Experience.tsx 与 CopilotDock.tsx；D/B 的 spec 一字未动；未 demo/reset；未碰 *_live.db / *_preview.db；凭据零打印；已发布路径零覆盖零删除（本目录新增七枚：move_reading_r3.json 3d5584b933ff04a2e1cf76294ad44eefab5600d6、builder 29cbb2b8945b2faa7cf149eea821e017136deeb4、r6_tree_after_move_r3.json 1f10d1976c62bb0d6e1d80c436c7ddccc91f9ef0、channel_words_r1.json 1ddf1e57240bc1d41f2f99ea5a4f7c1fbdde60b7、三臂 f57dca2c26dccad250e8f8e7fdfcca5f257f1622 / 1ea7fb842defed7c2f4ad22f7cc3897929fdacae / d815d93ebb0634969a5cb3a07b1d7f3e85dc7bd8；架上逐字回读，回读当代 8f2c80f8d289e2f321a4f52d991193a2647fdaae）；junction 已拆（拆前拆后共享树条目数同读数）。推枝这次都从 worktree 内推并 ls-remote 回读 tip。
claimed_result = CANDIDATE_READY + 两条待你选（:274 是否为通道让路；点开的行 vs open）。闭单只认 E 的 derived_result。
