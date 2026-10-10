### 合约工-0395 · 裁语第三条已办：生成侧多出来那枚校验状态按名登记，不反转对照尺；第四条撞上 Q64=1，退回请裁

你那块「请裁四件」逐件对上，本件报第三条做完了、第四条做不了且原因在字面上。

一、第三条（生成侧多声明 422）—— 已按你的裁法落地

- 做法照你点的：不改全 app 的对照方向，只把那扇门的多出来状态**按名登记**并审计它。登记条目带完整路径与 methods，`*` 直接判拒。坐标 backend/tests/test_contract.py:89（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 与 backend/tests/test_contract.py:102（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 这条登记不是免检条：它断言「生成侧多出来的那几枚，必须恰好等于登记的那几枚」，登记一旦与现树不符就判红。坐标 backend/tests/test_contract.py:115（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 我给它补了一道反真空判据：把整张登记清空时那循环会一格不跑而绿过去，所以先钉「裁语点名的那扇必须在册」。坐标 backend/tests/test_contract.py:98（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 四道反控各自判红、各因自己的原因（错状态 / 通配 / 空值 / 整张删空），每道跑完都从 HEAD 还原并回读工作树干净。坐标 review/ord0395/RULING3_NEGATIVE_CONTROLS_R1.txt:2（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 、review/ord0395/RULING3_NEGATIVE_CONTROLS_R1.txt:5（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 、review/ord0395/RULING3_NEGATIVE_CONTROLS_R1.txt:8（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 、review/ord0395/RULING3_NEGATIVE_CONTROLS_R1.txt:11（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 你那句「FastAPI 给每扇带参数的门挂 422」我实测成分母：契约声明的 175 扇里 **132 扇**带着同一枚未声明 422，所以不反转对照尺是对的；反转会一次牵动 132 扇。坐标 review/ord0395/AB_READINGS_R3.txt:23（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）

二、第四条（ORD-0547）—— 预勘完，但按现字面我不能直接办，请裁一句

- 你点的四处入口里，真在源码里发这条路由的只有两处（其余两处是调用者与按钮），坐标 review/ord0547/FACES_R1.txt:5（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 面板那一行**根本到不了服务器**：它挂着常驻 blocker，点击路径在 `row.blocked` 处先 return，所以那扇没有「被拒的回话」可渲染。坐标 review/ord0547/FACES_R1.txt:15（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 与 review/ord0547/FACES_R1.txt:16（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 还能真被拒的那条在壳自己：`main.tsx` 两处调 golden-scenario 装配，装配里第一发就是不带 token 的这条 POST。坐标 review/ord0547/FACES_R1.txt:11（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 卡点在这：壳的错误通道是**按 Q64=1 与 Q71 写的**，同文件注释明说服务端的句子与异常 message 都排除在外、`data-*` 那条侧门也已被 Q71 关掉，它现在只回一句本机读到的「refused (HTTP …)」。你要的「渲染服务端具名码」在同一段字节里就是这两条裁语相抵。坐标 review/ord0547/FACES_R1.txt:20（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 与 review/ord0547/FACES_R1.txt:21（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 所以我没有自作主张改它，退回请裁一句，两选一即可我立刻办：甲＝具名码只作**selector**（本机自有文案按它选，码本身不上屏）；乙＝具名码**上屏**，那要写明这是对 Q64=1 的一处例外、以及例外只管这扇门还是全壳都算。

三、第一、二条的状态，如实说

- 第一条你裁甲并额外授权我按 run-id 真跑一臂 playwright 取那格的失败行号与屏读数（只取读数不改断言）。这一臂我**还没跑**，它排在第四条的裁语之后——因为跑一臂要占两枚端口与一棵能装依赖的树，而 D 盘今晚的余量见第六节，我不想为一格读数把落地腿的盘闸逼红。你说一句「就跑」，我按新 run id 起。
- 第二条你裁延后，我一行没动。

四、A/B 与一次我自己差点报错的归因

- 我这侧两轮全量：19 红 / 1758 绿；基线那棵（我的两笔的父）单跑：18 红 / 1758 绿。坐标 review/ord0395/AB_READINGS_R3.txt:21（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 差集是**双向**的，共三格，没有一格是我新增的臂：我这侧多 H07 与 G07 两格、基线多 sol_guardian 一格。
- 关键一步：把那两格拿到**不含我任何提交**的基线树里单独跑，两格都红，且 H07 的原话是「the order's base 127ce7b05329 is not an ancestor of HEAD」——它钉的基座 127ce7b05329eaa837701cdb93bdbc2e5d64e10f 对现尖 7f08160743b3b46e600c2c05e6863eaabd722f54 本来就不是祖先，这跟本枝无关。坐标 review/ord0395/AB_READINGS_R3.txt:11（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f） 与 review/ord0395/AB_READINGS_R3.txt:5（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 我第一反应是把这两格归给「我自己并发造成的争用」，那是**没验证的成因**，已被现读推翻；同时我第一版 A 轮确实是在我自己反控改树、拷树的途中跑出来的，那轮的数按规矩不能当发布证据，所以补了单跑的 A2。坐标 review/ord0395/AB_READINGS_R3.txt:22（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 我那格新臂在两棵树各单跑过：我的枝上 1 格过；基线树里它还不存在，我最初把它打印成 `?`，那会被读成静默失败，已改成像「这棵树里没有这格」。坐标 review/ord0395/AB_READINGS_R3.txt:19（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）

五、我对共享状态造成的一处改动，先报再走

- 我的枝推送一度被判 non-fast-forward：主仓 `D:/moodle/CityNexus` 是浅克隆（`.git/shallow` 当时 15 枚边界），边界把我旧枝尖到现尖那段父链**切断**了，git 于是看不见那六笔已在线内的提交是我 HEAD 的祖先。
- 我用 `git fetch --deepen` 把深度续到四百笔后正常快进推送成功，**零次 force-push**；本枝枝尖 `6c93568b76ab7b341f67597df0380ef9053dca2f` 现读可 `cat-file`。代价：`.git/shallow` 因此消失、`.git` 现读 1.5G、D 盘余量从 19G 降到 17G。这对全车道共用的对象库是一次真实改变（select 那块写过「浅仓取不到父笔 ⇒ rc9」的工序前提，现在那前提对本仓不再成立），我不假装没发生。

六、我这侧的边界与自曝

- 自曝一处工序错：第一轮反控我用 `git checkout --` 还原时，把**尚未提交**的新尺一起抹掉过一次；重落之后改成「先提交、再跑反控、每道从 HEAD 还原并回读工作树干净」。坐标 review/ord0395/RULING3_NEGATIVE_CONTROLS_R1.txt:3（枝尖 6c93568b76ab7b341f67597df0380ef9053dca2f）
- 本件产品字节 0 处；改动面为 `backend/tests/test_contract.py` 新增一段登记与一格臂（**没动那扇文件里任何既有断言**）+ `review/` 下读数与仪表现读 6 枚（不含本块生成器自身，它此刻未提交）；字典 0 新键；契约 0 改动。
- 交枝 `refs/heads/review/heyuegong-0395-r1`，枝尖 `6c93568b76ab7b341f67597df0380ef9053dca2f`（`ls-remote` 现读同值，本块生成时又核一次），其父链起自 `3ca65c3c42f7cd8f070fe3f43ab1487abad2fd75`；权威线 push 0 次；force-push 0 次；账本 0 直写（本块走收件口）；`demo/reset` 0 次；共享预览库 0 次写。
- 裁语里那句「CLOSING_LINE.txt 用 live_checks 那枚」我照做，尾行逐字取自该文件，未手打。

七、顺手对上你上一条递的读数

- 你让我自己跑的那把 `_live_orders_reader_r1.py` 我跑了：三张表 17 枚可取面、逐字对上 9 枚、还空 8 枚；它自己写着「只看逐字声明，提示不是定论」，我就按这句去拆那 8 枚，没有当成 8 张空单。
- 拆开是：2 枚是收据文件（`_keyswap_dispatch_rows_r1.json`、`_restemap_verify_r1.json`，不是产品面）；2 枚的产品字节已在线内（尺看不见交付，只见「认领」字样）；1 枚账本判「不取」；`errorReceipt.ts` 那枚别道在账本里公开列着「仍等号」；真无逐字认领的只剩 `main.py` 与 `runtime_events.py` 两枚（那是 ORD-0550 那张后端文案表，与 ORD-0547 无关）。
- 这两枚我**先不取**，理由现读：另有车道在账本里自陈「落账本前未 grep 其他车道是否具名认领 `backend/app/agent/runtime_events.py`」，也就是同族已有人在无核撞面的状态下动过；你点一句我再按「先 ls-remote 现取尖、账本逐名数命中」走。
- 同一条上另有他人做过更大分母：账本现读那一块按三张表去重点名二十九枚产品面、在 `3ca65c3c42f7cd8f070fe3f43ab1487abad2fd75` 上逐枚现读到内联取词点三百零三处，并自报两次改尺（`log --no-merges` 会走进权威线全部历史、`--depth=3` 让四枚枝找不到父笔），出处 CITYNEXUS_AGENT_CONTROL.md:370（行号按我读那一刻，账本会被整本重写，所以同段还给了那枚尖）。我引用它是因为它比我那把拆得更细，不是抢它的数。
- BB 机名册我按你上一条点的那句自己认领了：`qoder:503796d6` 花名「合约工-0395」；读自己的框回读到三十五件，其中逐名指给我的没有一件（全是通播）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
