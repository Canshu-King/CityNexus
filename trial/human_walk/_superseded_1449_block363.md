### 494abfd7 交「221 处里旅客最先撞到的头几条」可点单清单（#363，接 §14.29 那条待裁）

- 这把尺不复打口径：trial/human_walk/_cmdr_what_traveller_reads_r307.py:46 直接复用 §14.29 那把尺的同一份 collect()，与已发布的 221 处对不上就 ABORT 不出表（现读 221 处，回执 trial/results/20261026_gozero/bw307-what-a-traveller-would-read.txt:2）。
- 排序口径（回执 trial/results/20261026_gozero/bw307-what-a-traveller-would-read.txt:3）：先旅客路径（/journeys、/plans、/trips、/travellers），再内部词汇，再裸 id 槽，最后比长度。221 处里落在这四条路径上的 132 处（:61），带内部词汇的 45 处（:62），带裸 id 槽的 36 处（:63）。
- 头 8 条逐枚（下面每行都从回执解析，不是我手抄）：
　1｜backend/app/main.py:20046（route_decorator）在 `app /api/v1/journeys/{journey_id}/start` 上端给屏上的是「f'PlanVersion {plan.id} is not authoritative: {start_authority_blocker}'」——内部词汇 1 处、id 槽 2 处
　2｜backend/app/main.py:18221（route_decorator）在 `app /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` 上端给屏上的是「f'PlanVersion {plan.id} is not authoritative: {authority_blocker}'」——内部词汇 1 处、id 槽 2 处
　3｜backend/app/main.py:7783（route_decorator）在 `app /api/v1/journeys/{journey_id}/undelete` 上端给屏上的是「f'Journey {journey_id} is still in the recycle bin'」——内部词汇 1 处、id 槽 1 处
　4｜backend/app/main.py:7762（route_decorator）在 `app /api/v1/journeys/{journey_id}/undelete` 上端给屏上的是「f'Journey {journey_id} was not in the recycle bin'」——内部词汇 1 处、id 槽 1 处
　5｜backend/app/main.py:18167（route_decorator）在 `app /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` 上端给屏上的是「f'PlanVersion {plan_version_id} was not found'」——内部词汇 1 处、id 槽 1 处
　6｜backend/app/main.py:7691（route_decorator）在 `app /api/v1/journeys/{journey_id}` 上端给屏上的是「f'Journey {journey_id} was not found'」——内部词汇 1 处、id 槽 1 处
　7｜backend/app/main.py:7696（route_decorator）在 `app /api/v1/journeys/{journey_id}` 上端给屏上的是「f'Journey {journey_id} is already deleted'」——内部词汇 1 处、id 槽 1 处
　8｜backend/app/main.py:7756（route_decorator）在 `app /api/v1/journeys/{journey_id}/undelete` 上端给屏上的是「f'Journey {journey_id} was not found'」——内部词汇 1 处、id 槽 1 处
- 清单里能一刀罩几条先说清：头两条是同一句模板的两半（出发口 backend/app/main.py:19990、选用口 backend/app/main.py:18139），改一处文案等于改两处；其余各条各自一条路由，一刀罩不住，要点单就得逐条点。
- 待裁（不代裁）：甲，这 45 处带内部词汇、36 处带裸 id 的是否统一改成「点名地点＋人话＋不端 id」那一形制；乙，是否给它们配各自具名键——现状是统一出口按状态码拼键（backend/app/main.py:784），同码不同句共用一枚，不配就仍接不上中文。本班 0 改产品字节。
- 落点与代次：正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3738；上一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3730；本批工件的提交代次为 git 对象 17552ea27e26ef56116db3417e83b95be720462b，可 git cat-file -t 取回。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
