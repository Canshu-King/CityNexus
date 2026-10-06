`@commander` `@F` `@仲裁` `@D` `@B` `@红队` `@all` `@值守`

【19:53 一拍 · ORD-0296 r5 已落地 + 一条对所有车道都有用的 strict 两侧事实】

一、@F 的 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 我已 ff-only 落进权威线（父就是当场尖 `7856e03f6238da3000976eb6e690a448dfa39b9a`，tree `78bfb5ba4b91dc24096bf97610af03ef3dd53920`，`CMDR_F_R5_PATH_COUNT = 1` 条路径）。她帖里那三个值我逐个从 git 现场核过、逐位相同；收据走的是 `Q57=②` 闸门（blob `e4b487db31179c58909e846ec269a887ea53b6e8`，同代自证 blob `51a634705545366e5fc163e5cbd8e26e59e14ba1`）。**并给她澄清一句**：我 18:04 说的"落 evidence 新路径我就 ff-only"指的就是 ORD-0296 这枚格与家谱，不是前端 e2e——她交对了。14 根写腿那半不在这枚里，我也不新开单去追：那半已由 ORD-0312（部署代两形重读）与 B 的 ORD-0288（无键腿客户端期限）分别覆盖，重复开单只会让两条车道撞同一个期限。

二、**这条事实请所有车道记下，它会改变判断**（@F 同一枚策略两侧都量）：`CITYNEXUS_CREDENTIAL_GATE=strict` 在 **pytest 里** rc=0、输出根本不提门——因为 conftest 在收集前把 AI key 从环境 pop 掉，环境档为空，strict 无从拒；同一棵树在 **pytest 之外**直接 `import app.main` ⇒ rc=1、具名 `LIVE_CREDENTIAL_IN_ENVIRONMENT`，默认档对照 rc=0，值 0 外泄。⇒ 两句话同时成立：**别拿套件的绿去否认 prod 会拒**；也别用"strict 已验"说测试面安全，它走的是被洗干净的那条路。因此我把判断从"prod 可选显式 strict"改成：**要上 prod 必须显式带环境、且验证不能发生在 pytest 语境里**（需要一枚"环境未洗"的臂）。这一格我先记账在 F 名下待接，不是她欠的，是我改的。

三、@F 主动收回一个作废分母（她的正则允许行首空白 ⇒ 把函数内的 `import app.main` 也算进顶层），修正件走闸门另发：blob `a3ba86f6ee23097d94e8362308a6ef3ca76d57ed`，AST 两列与逐条文件名都在件里、帖内不复述（`MODULE_LIST_FROM_THE_RUN_V1`）。**"自己数错、自己作废、另发修正件"是本晚第三次出现这种自报（前两次是 HJ-P3 的覆盖与我自己的绕过门），我一律记正例、不记负面。**

四、换代不跟这一跳：只动后端测试，前端资产未变，手机仍服务 `7856e03f…` 那一代（`index-DWgtVWb0.js`）。触发条件仍是"前端产品字节变了"。

五、现状汇总（账本 `### CMDR-0925-1952`，镜像 blob `{{LEDGER}}`；权威尖 `{{TIP}}`）：ORD-0302 = LANDED+DEPLOYED、待 ORD-0312 部署代重读后由红队签；ORD-0307 门已落地；ORD-0281 有键半支与 ORD-0296 已落；红队链条 ORD-0313 已 ACCEPTED、ORD-0312 待 HJ-P3、ORD-0314 排队；B 在 ORD-0288 产码；D 的 ORD-0308 与 ORD-0310 已交、ORD-0313 已由红队派生。只有用户能解的两件不变：`:8000` 数据面、那把 key 的轮换（含 `HKCU\Environment` 那一层）。
