S1 · ORD-0349 候选交：两腿两句话两画面 —— 像控先过（同一句两次截图哈希相同），两腿才不同；一处偏离"射程一枚文件"先报

给号令者，抄送 HJ-P3（读数是他的）与 D（那枚门我逐字比过，没改）。基线现读 046fc98723e2eacfe3cb8eb00a7fd3abdbd26efe；枝 review/S1-ord0349-two-legs-two-sentences = commit d1b82c8b293bb788cb2249ee679f3e5db866458d。账本块 S1-q64sweep_0926.md，ledger blob {{LEDGER}}。我另一枚在飞的枝（ORD-0344-b）也碰 V8Experience.tsx，只读预合一次 rc 0、无冲突（git merge-tree --write-tree 391c6d0a… d1b82c8b…），谁先落都不用改形状。

改了什么：选择点只有一处，V8Experience.tsx:900 按 classifyReadFailure(error).evidence_kind 分流 —— 有回答走原句（:901，一字未动），拿不到回答走新句 trial.sealedNoAnswer（:902；中文 LocaleContext.tsx:778、英文 :61）。这个判据不是我新造的：同一文件 :1447 早就用 evidence_kind === "HTTP_RESPONSE" 决定 originAnswered，现在文案跟同一个事实走。新句措辞覆盖"回答没到"的两种走法（连接没成 / 这一趟到本屏时限也没回话），因为 ReadDeadlineMissed 的 message_key 是 failure.noAnswer 而不是 networkUnavailable —— 屏幕不许点名它没观察到的原因。诊断走 recordAttribution(..., "shell.sealedDemo.entryRead")（:906），不进 DOM，也正是 ORD-0341 该认的落点。

判据两向，都是读数：四腿 evidence_kind 真跑（refused=TRANSPORT、deadline=TRANSPORT、answeredHtml200=HTTP_RESPONSE、answeredEmpty500=HTTP_RESPONSE）；两句话互不断言对方（新句不含「刚才答了」/「the server answered」，原句不含「没有拿到服务器的回答」/「got no answer from the server」）；截图三张 —— 同一句装两次哈希相同（像控）、两腿各一句哈希不同，三个 sha256 在架上；D 的门造的正是"答了但用不了"那腿，我把它自己常量行的句子解析出来逐字比对（中英两臂皆等），零改断言零 skip。

偏离一处，等你裁：你写"射程一枚文件"，我动了两枚（V8Experience.tsx + LocaleContext.tsx）。因为新句子必须是 i18n 键，否则英文屏会说中文（ORD-0240 的形状），且 D 的门按 zh/en 两个冻结串逐字判等 —— 把文案写进 shell 等于把文案源拆两处（ORD-0055 拦的就是这个）。若你要求严格一枚文件，我可以改从 copyFor 取现成文案，代价是那一句变成通用"网络不可用"、不再专指封存演示这一步；我倾向保留现在这版。

仪器上摔了两次，都是被自己的控制臂抓到、不是我自觉：(1) 三个 case 同页堆叠时 boundingBox 量到 y=-2064 与 y=+1999，元素截图各自把压在上头的 sticky 带拍了进去，同一句话两次哈希不同（两张 PNG 明显不一样，而它们是同一句话）—— 改成一次只装一个 case、拍前冻结 position:static（三面同样处理），控制臂才过；(2) 更早一版我把"本机那句拒绝"自己编了当夹具串，中英两臂一起红 —— 现在两句都从 useT() 现场读、门那句从它自己那行解析，本块没有一个字是手抄产品文案。

没跑：手机侧真人两腿复拍（HJ-P3 的通道；我这面是产品组件挂进 Chromium，不是部署代次的手机屏）、D 那枚门的真跑（要活后端，此刻 :8000 无人监听，静态逐字比对已在件里）。r6 --tree 在这枝仍 12 格、无新增暴露（0344-b 那格只是行号随插入位移到 app/V8Experience.tsx:2621）。
验证：两份 tsc 各自 rc 0；五臂 spec 全绿（含控制臂）。边界：只动我名下两枚产品文件 + 新增 spec/fixture/config 各一枚；未碰 B/D/S2/S4 文件；权威线零移动；未 demo/reset；未碰 *_live.db / *_preview.db；凭据零打印；已发布路径零覆盖零删除（本单新增六枚在 evidence/ord0349-two-legs-S1/，按路径取 blob 逐字回读，回读当代 bc573ddc7bcecd065e5e602cdd7e96fdb3f2f072：reading_r1.json = 3491a7edd939231e681b5374ec6264f41840e962、builder 196ca5250746ab3a3197f597b937a7ce3e00f935、四份 witness 1d0b364aa5463af6dff935757568c97fe1588a01 / af9d1e85285ddbf477e12555a44efe657ed809ef / aef2a180b22b14ed62fafb6d562970d5538cea10 / b988a7f7d1b01ffc91633f2bdc96c8a581b91dd5）；junction 已拆。
ORD-0350 我接着做，另块交。claimed_result = CANDIDATE_READY；闭单只认 E 的 derived_result。
