### 494abfd7 交「旅客面 ∩ 内部词汇」= 21 处的逐枚清单（#365，接 §14.32）

- 前两节各数各的：§14.30 报 132 处（旅客路径），§14.31 报 45 处（内部词汇），要改文案的人真正要的是「既在旅客面上、又端出内部词汇」那一部分。尺 trial/human_walk/_cmdr_smallest_fix_set_r313.py:27 复用同一份 collect() 与同一份旅客面判定，三枚读数与父回执现读一致：221 / 132 / 45（回执 trial/results/20261026_gozero/bw313-traveller-side-and-internal-vocabulary.txt:2、父回执 trial/results/20261026_gozero/bw307-what-a-traveller-would-read.txt:62）。
- 交集 21 处，另有 24 处落在非旅客面（Agent 或管理面），21 + 24 = 45 对账闭合；行身份取 (文件, 行)，模块级 helper 按自己那枚 raise 计、不替它编 URL（回执 :3、:68、:70）。
- 下面 21 行整串由回执解析，不是手抄：
　1｜backend/app/main.py:1932 路由 `app /api/v1/journeys/{journey_id}/agent/mobile-compat-runs` 端给屏上的是「provider consent is required」——术语 provider
　2｜backend/app/main.py:3424 路由 `app /api/v1/journeys/{journey_id}/launch-origin` 端给屏上的是「place_id is required for PLACE」——术语 place_id
　3｜backend/app/main.py:3715 路由 `app /api/v1/journeys/{journey_id}/in-transit/reroute` 端给屏上的是「journey must have an ACTIVE plan」——术语 journey
　4｜backend/app/main.py:5507 路由 `app /api/v1/journeys/{journey_id}/missions/{mission_id}/clarification` 端给屏上的是「clarification payload is invalid」——术语 payload
　5｜backend/app/main.py:5606 路由 `app /api/v1/journeys/{journey_id}/missions/{mission_id}/collective-clarification/{member_id}` 端给屏上的是「authenticated traveler cannot answer for another Journey member」——术语 Journey member
　6｜backend/app/main.py:7691 路由 `app /api/v1/journeys/{journey_id}` 端给屏上的是「f'Journey {journey_id} was not found'」——术语 journey
　7｜backend/app/main.py:7696 路由 `app /api/v1/journeys/{journey_id}` 端给屏上的是「f'Journey {journey_id} is already deleted'」——术语 journey
　8｜backend/app/main.py:7756 路由 `app /api/v1/journeys/{journey_id}/undelete` 端给屏上的是「f'Journey {journey_id} was not found'」——术语 journey
　9｜backend/app/main.py:7762 路由 `app /api/v1/journeys/{journey_id}/undelete` 端给屏上的是「f'Journey {journey_id} was not in the recycle bin'」——术语 journey
　10｜backend/app/main.py:7783 路由 `app /api/v1/journeys/{journey_id}/undelete` 端给屏上的是「f'Journey {journey_id} is still in the recycle bin'」——术语 journey
　11｜backend/app/main.py:11042 路由 `app /api/v1/journeys/{journey_id}/stay-options/{option_id}/mode` 端给屏上的是「f'mode {payload.mode} is unavailable for the requested leg'」——术语 payload
　12｜backend/app/main.py:11519 路由 `app /api/v1/journeys/{journey_id}/operator/reality/provider-replay` 端给屏上的是「captured provider replay was not found」——术语 provider
　13｜backend/app/main.py:16917 路由 `app /api/v1/journeys/{journey_id}/group-recovery/apply` 端给屏上的是「group recovery idempotency record is invalid」——术语 idempotency
　14｜backend/app/main.py:17621 路由 `app /api/v1/journeys/{journey_id}/plans/generate` 端给屏上的是「Select different bootstrap candidates without additional place_ids」——术语 place_id
　15｜backend/app/main.py:18152 路由 `app /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` 端给屏上的是「f'Journey {journey_id} was not found'」——术语 journey
　16｜backend/app/main.py:18167 路由 `app /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` 端给屏上的是「f'PlanVersion {plan_version_id} was not found'」——术语 plan_version
　17｜backend/app/main.py:18221 路由 `app /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` 端给屏上的是「f'PlanVersion {plan.id} is not authoritative: {authority_blocker}'」——术语 authority
　18｜backend/app/main.py:20012 路由 `app /api/v1/journeys/{journey_id}/start` 端给屏上的是「Journey member role cannot start execution」——术语 Journey member
　19｜backend/app/main.py:20020 路由 `app /api/v1/journeys/{journey_id}/start` 端给屏上的是「journey must be PLANNED with a selected plan」——术语 journey
　20｜backend/app/main.py:20046 路由 `app /api/v1/journeys/{journey_id}/start` 端给屏上的是「f'PlanVersion {plan.id} is not authoritative: {start_authority_blocker}'」——术语 authority
　21｜backend/app/main.py:21498 路由 `app /api/v1/journeys/{journey_id}/events` 端给屏上的是「provider_key is server-assigned for public event input」——术语 provider
- 这一格同样带口径（先自己说清）：21 是大小写敏感的读法，同一词表改成不区分大小写会把交集撑到 57 处（多 36 处）——回执 :69；父桶 45 也是同一口径下的数，它的对照数在 §14.31 那份回执里。所以「就 21 处」在当前口径内成立。
- 待裁三档（不代裁）：甲一，只动这 21 处；甲二，动 45 处全桶（含 Agent 面）；甲三，动 132 处旅客面全量（含不带内部词汇的那些）。乙（给 raise 配各自具名键）三档都要。本班 0 改产品字节。
- 具名对照：回执 :71 那一行同时验过第一枚既在旅客面又带词表术语。
- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3757；上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3746；本批工件的提交代次为 git 对象 96e4c7fefbaf68d8af5d5364d8c182aa35254484，可 git cat-file -t 取回。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
