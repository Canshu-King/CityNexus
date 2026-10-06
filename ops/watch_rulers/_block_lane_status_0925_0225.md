## commander 收单 @2026-09-25T02:2x+08 —— D 的 0269/0273 门 v5（9/9 反突变全 KILLED，两枚原本存活的现在各翻自己那格）与 B 的 B2c 状态收进账；顺带两条**新落地的产品真相**要各车道改基线

### ① `@D` 交回的（三句 status 全部按已落盘工件答，未交的地方直说未交）
```text
0269/0273 门 v5：9/9 枚反突变 KILLED，treeUnchangedByThisRun=True
   收据 review/evidence/ui-overnight/ord0269-0273-arms-v5-a1d7442.json，尖 a1d7442bd892285e54dd9ab1e403968760907dfa
   上次存活的两枚现在只翻自己那格：
     K269_MALFORMED_FEED_SILENT -> 红集 = 只有格3（独占）。前提是她修了一处真产品缺陷：hook 里 `events: ?? []`
        把"答了但不可用"伪造成"本页没有"——既谎报了具名原因，又让分类器那道守卫根本不可达（所以 v2 它活了）
     K269_GLOBAL_MARKER         -> 红集 = R-4 + cell1（cell1 按 collateral 记，不当独立证据）；
        R-4 先自证前提 bScopedReadsObserved=8（App 真读了行程 B 的 8 个请求）才允许说"B 上没卡"
   两处她自己仪器曾骗她的也已修并具名：R-6 只断言缺席（变异体 1.3s 混过 => 现在 16.2s 红）；
   驱动曾在 run_spec.py 截断的 90 行控制台里读自己的运行（四红被读成 BASELINE_RED）=> 改读全文日志、tally 全留
ORD-0278：代码未动（明说未开工），但字段名是从 F 的真 schema 读的：GeneratePlansRequest 新增 mission_id: str | None（body）
R-SCHEMA 归属：属"不必重跑"那一类（她的行全部经产品 API 造）
```
### ② 一枚她顺手量出来、但**随落地而变**的产品真相（我要求她分开写两代，不要只留新结论）
```text
她在旧尖 c79e2b4（落地前）用 3.12.14 venv 实测：AgentCommandRequest.model_config = {'extra':'forbid'}
                                            GeneratePlansRequest.model_config = {}（默认 ignore）
⇒ 在旧尖上，往第二腿 body 塞 mission_id 会被**静默忽略、不 422**——"客户端这一半可以先行且惰性"成立；
   但她同时给出边界：**绝不能往第一腿 body 加任何新键**（那才是 422 那一面）。
   落地那一代 schemas.py 已含该字段（blob 2e6e26c，与 aa29612 同一枚），所以这个结论必须在 dcae1bc96 上重测一遍。
   我为什么较真这个：同一个"extra 形状"在两代里答案不同，这正是我们避免的那类混淆——结论要带它那一代的名字。
```
### ③ `@B` 交回的（三句 + 具名结论，未测处不写 KILLED）
```text
B2c：4 文件已写（新增 lib/inFlightWrites.ts 只登记非幂等方法；v8Request/requestJson 各包 begin/release，try/finally
     任何结局都释放；main.tsx handover 改成 onNonIdempotentRequestsQuiet(()=>reload())，有写在飞先落
     citynexus.sw.generation-handover-pending 再派事件，进终态即自动收敛；无写在飞时 quiet point 就是"现在"，
     不新增用户导航）。typecheck rc=0；**运行时读数 0、反控未跑 => 她不写 KILLED，只写"未测"**（这是我要的形状）
B2b：未开始、0 读数；只做了源码确认承载已存在（TRIAL_DRAFT_KEY 写/恢复读/仅成功创建或卸载清），按边界不造第二套草稿宇宙
0263 七项在那一代的复跑：**一格都没有**，明说没跑（不说"在跑"）
R-SCHEMA 具名结论：不依赖表结构 => 不必重跑；且她的库本来就是"一次性新 db + 产品 ensure_schema() + seed_demo"，
     属方法本就合规，不是"重跑后合规"
```
### ④ 我给两条车道下的指令（也是给全线的基线通知）
```text
新基线 = dcae1bc964125c3a975916f6bf667794cc19622a（02:2x 我落的可读权威线尖）
@B：**先把 B2c 那 4 个文件 commit 到她自己的候选枝并回读 ls-remote sha**——理由不是我催交：早上我要做 ORD-0271-A/0277
   的同代换代复跑，那一步要 vite build 重建 dist，而 vite build 读工作树；她 frontend/src 脏着 = 我一构建就把未验收
   代码发到用户手机上。顺序：commit -> 换代断言改用字节判定尺 -> B2c 运行时 + 反控 -> B2b。
@D：从 dcae1bc96 开 0278；把 v5 收据插进账本 + 另存 commander/control 可外读路径；那处 `events: ?? []` 的产品缺陷
   要单独具名给我（修没修、在哪个 commit，没修就开单——它是"判据能判但产品不配合"的形状）。
HJ-P1 仍然不在（23:43 之后冷），所以 D 的 #2c v5 / #2d 验件我不让她等：改派 @红队 或另开窗，不拿"验方睡了"当交付停滞的理由。
```
纪律读数：`demo/reset` 0、用户库写 0、凭据 0 打印、已发布路径 0 覆盖 0 删除（本时段 0 新增产物）、产品码 0 写；权威尖只由我动，今晚已 ff-only 落过一笔。

