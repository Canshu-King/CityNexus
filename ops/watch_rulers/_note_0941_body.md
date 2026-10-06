S1 · ORD-0350 候选交：复核页九行各有具名出口，按下真到得了那一格的编辑位并带回原值；出口放行标题里，因为三枚已上线的门在逐字读答复格

给号令者，抄送 D（那几枚门是他的）与 HJ-P3（读数来源）。基线现读 046fc98723e2eacfe3cb8eb00a7fd3abdbd26efe；枝 review/S1-ord0350-review-row-exits = commit cbd69ef8f8eec2a2019f15a8af77854a7b649000（只从尖开枝，与 0344-b、0349 两枝零文件重叠；对 0349 那枝只读预合 rc 0）。账本块 S1-q64sweep_0941.md，ledger blob {{LEDGER}}。

做的：9 行各有自己的出口（review-edit-city/-arrival/-departure/-party/-budget/-pace/-interests/-special/-auto-set）。可见文字是「改这一项」，具名在无障碍名里（改这一项：人数 / 房间）—— 一行里连念两遍条目名比只念一遍差。跳转用的是 ORD-0135 ③ 已有那条路（第 3 步去前面那步的字段必须先挂载再聚焦），我把它抽成共用 jumpToField，没有第二份实现。节奏/兴趣两格没有可聚焦的落点（只有一排 chip），所以给两个 fieldset 加了 data-testid 与 tabIndex=-1，落在组上而不是随便指第一枚 —— 指第一枚 chip 会让读屏以为在建议选它。「自动设置」一次改三个值且那三控件在第 1 步「显示高级」后面，所以它的出口就是那枚披露按钮，具名说明，不假装能聚焦藏起来的输入框。样式复用 .trial-missing-jump 那条内联规则（那条评论记着实测：做成独立小盒会撑高 58px，移动端 44px 覆盖门随即红）。

判据双向，全部在真产品页面上走：存在（9 行全有、各自点名）；到得了且带回原值 —— 出口按下前那格控件根本不在 DOM 里（计数为零，这就是"红"的那一半），按下后挂出所属步、焦点落在 trial-party、原值还在、且能改（填 3 读回 3）；第 1 步同理（焦点 trial-city、值仍是 seed 的「天津」）；不破坏别人的门 —— 出口在行标题里、答复格 innerText 一字未增（review-pace / review-interests / review-party / review-budget / review-city 五格都测了不含「改这一项」且非空）。最后这条不是洁癖：qoder-stated-versus-stored-versus-planned.spec.ts:64 拿 review-interests 与 review-pace 的整格文字与冻结串逐字判等，出口若塞进格里那两臂当场红。共用路由的回归也量了：点「抵达」那条缺字段跳转，焦点仍落在 trial-arrival。

没跑：D 名下走完整向导的三组门（要活后端与种子，此刻 :8000 无人监听）—— 我能复现的是它们读的那几格文字没变；手机侧复走归 HJ-P3。r6 --tree 全量输出已上架（evidence/ord0350-review-row-exits-S1/r6_tree_candidate_r1.json = 09901799d7cfd09f8ddc1ef921db6fe13c29187c）：与 ORD-0349 那份相比格数一致、无新增暴露，JourneyTrialSetup.tsx 不在 hits 里；差集是我会话内算的没另存件，要复核请对两棵导出树各跑一次同一枚尺。
另记一处仪器坑（会影响别的车道的自测）：我第一次自测把哈希预检跑在 git fetch 之前，结果刚上架的那枚 blob 被报成 OFFENDER —— 预检只认本地对象库。fetch 之后复检八枚全可解析、offenders 归零。发布后自测，顺序得先 fetch。
还有一处我自己差点交错：第一版我沿 ORD-0339 那招用 fixture 把组件再挂一份，结果产品自己的向导也同时挂载，页面上出现两份 trial-step3-body、门位全歧义 —— 这单直接走产品自己的入口（清 journey_id + 把草稿写进它自己会恢复的那枚 key），fixture 删了。

验证与边界：tsc 两份配置各自 rc 0；五臂 spec 全绿；只动 JourneyTrialSetup.tsx 与 styles.css 两枚产品文件（后者只是给一条既有规则加一个共用选择器）+ 我新增的一枚 spec 一枚 config；V8Experience.tsx、D 的 spec、B/S2/S4 文件一字未动；权威线零移动；未 demo/reset；未碰 *_live.db / *_preview.db；凭据零打印；已发布路径零覆盖零删除（本单五枚新证据在 evidence/ord0350-review-row-exits-S1/：reading_r1.json = 6f0a4961a0ab18e0977cb09a0060428b88b2f646、witness_exists.json = 80878ff611bd0f97da4b355ce793803e72fc5b77、witness_step2-press.json = 8a17ac45ce9e5e0bc7dfcf20794d4634d9eae100、witness_answer-cells.json = 9d1a483fc268917a5650432873971a1bed5c79f1、上面那枚 r6；按路径取 blob 逐字回读，回读当代 84dac8792ac32feb1f9baabe89138b1901c02fdb）；junction 已拆。
我名下现在三枝都在架：ORD-0344-b（391c6d0a…）、ORD-0349（d1b82c8b…）、ORD-0350（cbd69ef8…），彼此可独立重切。claimed_result = CANDIDATE_READY；闭单只认 E 的 derived_result。
