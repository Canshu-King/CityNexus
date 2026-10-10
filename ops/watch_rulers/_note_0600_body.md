S1-q64sweep · ORD-0326 附带件交清：字段实到清单（量的那一代 5d7335721106c20092dd4d90181bb99accd0a32b，另附新尖重跑件）

给 F 的 ORD-0332 当输入，也给号令者销那一件。量的是我已落地的两枚前端文件真调的三条 POST 腿「路上的回答」：六个允许字段里哪几枚真到、叫什么键、在哪一行产生。缺的写 NOT-EMITTED，没有自造编号。

件：evidence/ord0326-server-reason-S1/agent_fields_r2.json（blob 5d3c684dfb28d6d0e0ddc3367a69b799be379b36）
量具：evidence/ord0326-server-reason-S1/field_arrival_builder_r2.py（blob 64ec7d8af049f8d2311147d56ba67789ca8d874e）
上一枚 r1 不覆盖，仍在架上：agent_fields_r1.json（blob c80f6f61bff8d574dc529a27ba21dd9cbc5cb328）
账本：本车道块 S1-q64sweep_0600.md，ledger blob {{LEDGER}}，发帖现读尖 {{TIP}}

六格结论
- http_status：到，而且真上屏。它是传输状态不是正文键（backend/app/main.py:496 产生 → frontend/src/api/citynexus.ts:681 读 → Attribution.http_status）。
- content_type：只在一个态里读得到。全文唯一读点 frontend/src/api/citynexus.ts:687 站在 :686 那道守卫里面，非 2xx 在 :680 就先抛了 —— 所以「服务器拒答」这一面它根本进不了归属层。
- body_bytes：NOT-EMITTED。正文在 frontend/src/api/citynexus.ts:663 读成 text，长度从未留下。
- response_received：没有这个键名；同一个事实叫 evidence_kind（frontend/src/lib/failureAttribution.ts:42）。
- elapsed_ms：服务器今晚开始发了，客户端不读。F 的写期限中间件对每个请求上表（backend/app/main.py:634），过界由 backend/app/main.py:618 回 503 并在 backend/app/db/write_deadline.py:164 带上 elapsed_ms，落点 error.details.elapsed_ms；我那四个 catch 面全是单参数 classifyReadFailure(cause)（frontend/src/features/agent/AgentComposer.tsx:103、frontend/src/features/agent/CopilotDock.tsx:348、:368、:628），body 从头就没读，所以它进不了屏。
- request_id：NOT-EMITTED。backend/app/main.py 全文 0 命中（该文件 11490 行，行数量具现数）；拒答带的是 error.trace_id（backend/app/main.py:491，def :460，一枚一次性的 uuid4）。这名字只在入向活着（backend/app/schemas.py:130）。

给 ORD-0332 的两条可行动事实
1. 这三条腿都是 POST 且不带幂等键，所以在 frontend/src/lib/readDeadline.ts:51 转手以后由 frontend/src/lib/writeDeadline.ts:128 原样透传：客户端这段既没期限也没计时。也就是说 elapsed_ms 在客户端不是「没读」，是「没人测」——想让屏上有可复述编号，测点得新建，不是接线就行。
2. copilot 这条腿遇到 AI 侧失败会回落成确定性解释并照常答 200（backend/app/main.py:10663、backend/app/main.py:10664），屏上无从归属；DeepSeek 的 x-request-id 确实被抓进 backend/app/integrations/ai/responses.py:336 存到 :34，但 main.py 里 response_id 0 命中，从没往信封走过。

自测双向跑过：正臂 41 枚引用全过；反臂把 frontend/src/lib/failureAttribution.ts:133 往下错一行读成 :134，必须 ABORT —— 它真 ABORT，所以判定是「那一行含那个子串」，不是全文案搜索。
尖又动了一笔（ORD-0334，只碰 agent-mcp/）：现读 a8237d7b50a1df419ae7e89ae6c075dabb6513f8。同一张引用表在新尖上原样重跑，我引用到的 9 枚文件逐枚 blob 全等，41 枚引用全部重过，六格判定一字未变 —— 件 evidence/ord0326-server-reason-S1/field_arrival_repin_receipt_r1.json（blob fccc803a4543b32dfae0f4cf9b1cfb1b91609a4f）。反控另跑一枚：把 backend/app/db/write_deadline.py:164 的 elapsed_ms 临时改成 elapsed，量具当场 ABORT 且不写文件，还原后与尖上那枚相等。
边界：0 改产品字节（只读 git archive 导出树）；0 推权威分支；已发布路径不覆盖；未 demo/reset；未碰 *_live.db / *_preview.db；未打印任何凭据。这张表不是门，我也不宣布任何一单 CLOSED。
一处更正留给归档：路由真名是复数 messages（backend/app/main.py:11090），单数写法对不上任何处理器。
