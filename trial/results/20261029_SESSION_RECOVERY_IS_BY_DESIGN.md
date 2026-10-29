# 「重开浏览器回不到旧行程」——量到的是设计，不是要修的 bug

日期：2026-10-29 凌晨 · 代次 `d3fb23b526` 之后（本件未改任何产品文件）
关联：#332（重启身份恢复）、#164（Q1 已定「禁裸 ID 换 token」）、#285、#333
结论一句话：**旧行程回不去，是因为凭据被有意只放在本次浏览的会话里；要改的是"要不要给这台设备一张可续期凭据"这个产品决定，不是补一个按钮。**

## 一、现场读数（真 Chrome、真点击、390×844、隔离 canary 栈）

臂 bp136（`trial/results/20261026_gozero/bp136-session-recovery-390.txt`）：

    :4-5   首访签了新身份并建了行程：POST 201 /api/v1/travelers、POST 201 /api/v1/journeys
    :8     建完之后 sessionStorage 里有 citynexus.traveler.bearer（195 字节）与
           citynexus.traveler.session-id（36 字节）——只印键名与长度，值不落任何文件
    :13    关掉浏览器、用同一个 profile 重开：sessionStorage 只剩 citynexus.revolution.v3.space
           —— 两枚凭据都不在了；localStorage 里 firstlook.journey / recent-journeys 两条仍在
    :15    「我的旅程」屏原话：这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度。
           屏上给的两个动作是「课堂演示：进入示例行程」与「开始探索 →」，没有指向那趟旧行程的键。

臂 bq137（`trial/results/20261026_gozero/bq137-stranger-can-back-390.txt`）问的是下一个问题：
**一台新身份，能不能读到那趟旧行程？**

    :2     设备本地指针的键是 ["id","cityCode","cityName","status","ownerTravelerId"] —— 产品自己记着
           那趟行程属于哪个 traveler
    :5-6   重开后页面自己又签了一张新身份（POST 201 /api/v1/travelers）
    :8     用这张新身份直接访问旧行程的地址：屏上落到「用你自己的城市试用 CITYNEXUS 新建行程 三步完成」
           —— 既没读到旧行程，也没读到一句拒绝，只被送回新建向导

所以"前端加一个回到旧行程的按钮"这条路是假的：按下去读不到东西（:8 就是证据）。

## 二、码上写明的就是同一件事

`frontend/src/lib/travelerSession.ts`：

    :1-2    SESSION_KEY = "citynexus.traveler.bearer"；TRAVELER_ID_KEY = "citynexus.traveler.session-id"
    :10-13  注释原话：「The bearer is the credential. A paired session-local traveler id is only a
            navigation hint and never grants access or replaces server authorization.」
    :17 / :30-31 / :40-41 / :54-55   读写一律走 window.sessionStorage，没有任何 localStorage 分支
    :59-62  注释原话：轮询 bearer 是「a small privacy boundary」

也就是说：关标签页就丢身份，是这枚文件自己声明的设计意图。而 `:10-13` 那句"travelerId 只是导航提示、
不授予访问"，与既有裁语 #164「禁裸 ID 换 token」是同一口径 —— 所以"拿 localStorage 里那个
`ownerTravelerId` 去换一张能用的凭据"不是没做，是**已经被明令禁止**的做法。

## 三、因此 #332 真正欠的是一条裁语，不是一个改动

要让人重开浏览器还能回到自己的行程，只有三条路，各自代价不同：

甲、**可续期凭据**：给设备一张能重新换发 bearer 的东西（httpOnly cookie 或 localStorage 里的 refresh
令牌）。这是唯一能真正做到"回来"的路，代价是把"关标签页即失效"这条隐私边界换掉 —— 需要主人明确点头，
并且要一并决定 #333（裸 `/journeys/:id` 对非成员仍回 200）要不要同时收紧。

乙、**主动再认证**：保持现有隐私边界，重开时明确问一句"要不要重新登录这趟行程"，并给一条真走得通的路
（例如输入行程编号 + 一次性配对码）。屏上那句「这次打开没有登录到它」已经是这句话的一半，缺的是后半句
与入口。代价：多一步，且配对码机制目前不存在。

丙、**只把话说全**：承认这台设备回不去，把「开始探索 →」改成不会让人误以为"继续"的措辞，并给"清掉这台
设备上留存的行程指针"一个动作。代价最小，但旅客的旧行程仍然读不到。

我按 #164 与 `travelerSession.ts:10-13` 的既有口径**没有动鉴权，也没有动这枚文件**；甲/乙/丙要哪一条，
点一句我就照做并补屏证。

## 四、本班顺手量到的两枚仪表缺陷（已记，未粉饰）

一、两枚臂都从 `POST 201 /api/v1/journeys` 这行 URL 里找 journey id，而该响应的 URL 本身不带 id
（`bp136…:6` 报 `not_seen_in_receipt`、`bq137…:7` 同样）。正解是像 bq137 的 `:2` 那样从产品自己的
localStorage 指针取 uuid —— 后续臂一律用这个取法。
二、bq137 的 `VERDICT UNKNOWN`（`:9`）不是产品含糊，是我的判据只写了"拒绝词/看到旧城名/有卡片"三种，
没覆盖"被重定向到新建向导"这第四种真实形状。判据要补这一格，否则下次仍会报 UNKNOWN。

## 五、更正：§一 里那条推论不成立（正对照失败了）

§一 末句写的是「所以『前端加一个回到旧行程的按钮』这条路是假的：按下去读不到东西（:8 就是证据）」。
证据本身没读错，但它不判别。臂 bs140 把两半都跑了一遍 —— 同一身份**自己刚建**的那趟，和**上一身份**建的
那趟（`trial/results/20261026_gozero/bs140-ownership-discriminated-390.txt:7` 现读 `different_owner=true`）：

    A_OWN_JOURNEY            shape=REDIRECTED_TO_CREATE            （:8）
    B_OTHER_SESSION_JOURNEY  shape=REDIRECTED_TO_CREATE            （:9）
    VERDICT ROUTE_BOUNCES_EVERYONE_control_failed_…                （:11）

也就是说：拿自己刚建的行程做正对照，也被送回新建向导。既然 owner 自己也读不到，「陌生人读不到」这件事
就**不能**归因到归属或权限上 —— §一 那句推论降级为未证。r139 的 `:6-9` 是同一形状的另一次读数，
它的 `VERDICT CONTROL_FAILED` 已经把警报报出来了，是我当时没有把它当成对前一条推论的反驳。

## 六、换掉它的新事实：Revolution 根本没有「能用地址打开某趟行程」这扇门

`frontend/src/main.tsx:52` 只把 `/revolution` 前缀交给 Revolution，其余路径一律落到 V8 壳
（`:55-59`）。而 Revolution 这一侧（`frontend/src/trial/**`）出现的十四处 `/journeys/` 全部是
`/api/v1/...` 的取数地址，**没有一处是页面地址** —— 现读法：`grep -rn "/journeys/" frontend/src/trial/`。
所以 `/journeys/<id>` 从来就不在 Revolution 的路由里：它由 V8 壳渲染，V8 壳认的是另一套会话，看不见
Revolution 建的行程，于是显示它自己的新建向导 —— 这与 bs140 两半都 REDIRECTED 完全吻合，
也跟归属无关。旁证：`main.tsx:64-71` 那段补丁专门处理「粘贴链接带星号」的情况，注释原话就是不想
「silently showing the unrelated V8 "New Journey" wizard」，说明这面墙早就被人撞见过一次。

于是 #332 的完整根因是两件事叠在一起，缺一条都回不去：

一、凭据只在这次浏览的会话里（`frontend/src/lib/travelerSession.ts:17`、`:40-41`，注释 `:10-13`、`:59-62`）；
二、Revolution 没有可分享、可回访的行程地址（`frontend/src/main.tsx:52` 与上面那十四处的形制）。

因此裁语清单要在 §三 的甲/乙/丙之外加一条 **丁**：先给 Revolution 一条真能打开某趟行程的地址
（例如 `/revolution/journey/<id>`，并把 `/journeys/:id` 在持有 traveler bearer 时导进 Revolution 而不是 V8）。
丁不解决身份持久化，但没有丁，甲/乙做完旅客仍然只能靠 tab 与卡片找路。这条与 #404（深链接要落到那一屏）
同族 —— #404 闭在 V8 线上，Revolution 这一线没被它罩住。**我没有动 `main.tsx`，也没有动任何路由**：
把 `/journeys/:id` 改道会直接改变 V8 现有行为，属跨树口径，要点名。

补一句仪表账：撞车尺在 r139 上架那一刻就咬住了它复用 r137 profile 这件事（`PROFILE_CLASH _chrome_gozero_bp136b` ⇒ `COLLISIONS 1`），已给它独立 profile 并在文件头声明不再重跑；判别读数由带正/
负对照的 r140 承担。尺又一次比我先发现问题。

