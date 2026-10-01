# `review/**` 里仍以 CRLF 入库、被 `.gitattributes`（`*.py text eol=lf`）判成假脏的名册

现读自本车道一棵稀疏集合含 `review` 的新检出树 `wt543tip`，头 `5a4cdbd26d4a58d6ed6b277480e766ac08b15ded`。
逐枚比较工作树字节与 HEAD blob：忽略 CRLF 后 **完全相同** 的有 38 / 38 枚，也就是内容 0 处不同，只有换行符申报差。

后果不是难看而是拦路：`git rebase` 会以 `error: cannot rebase: You have unstaged changes.` 停在它们上面（本单 2026-10-02 撞过一次）。不碰别人字节的绕行办法：在现尖另开一棵树，把那一笔 `git cherry-pick` 过去——本枝的交付代就是这么来的。

号令者 15:30 裁语第 8 条④把这件事归他自己、说三枚；实测是 38 枚，全在 `review/` 存档树下面。

| 文件 | 工作树 CR | blob CR | 忽略 CRLF 后相同 |
| --- | --- | --- | --- |
| `review/CityNexus-Overnight-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Post-WP04-GitHub-Integration-Foundation-Checkpoint-20260909/implementation/backend/app/models.py` | 342 | 342 | True |
| `review/CityNexus-Post-WP04-GitHub-Integration-Foundation-Checkpoint-20260909/implementation/backend/app/schemas.py` | 345 | 345 | True |
| `review/CityNexus-PostGoal-Vertical-Slice-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-PostGoal-Vertical-Slice-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-PostGoal-Vertical-Slice-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Provider-Runtime-Gate-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Provider-Runtime-Gate-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Provider-Runtime-Gate-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Provider-Runtime-Hardening-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Provider-Runtime-Hardening-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Provider-Runtime-Hardening-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Solver-Runtime-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Solver-Runtime-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Solver-Runtime-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Vertical-Slice-Hardening-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Vertical-Slice-Hardening-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Vertical-Slice-Hardening-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-WP06-JourneyTwin-v2-Checkpoint-20260909/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-WP06-JourneyTwin-v2-Checkpoint-20260909/backend/app/db/models.py` | 342 | 342 | True |
| `review/CityNexus-WP06-JourneyTwin-v2-Checkpoint-20260909/backend/app/schemas.py` | 350 | 350 | True |
| `review/CityNexus-WP06-PostGate-Checkpoint-20260909/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-WP06-PostGate-Checkpoint-20260909/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-WP06-PostGate-Checkpoint-20260909/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-Checkpoint-20260910/implementation/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-Checkpoint-20260910/implementation/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-Checkpoint-20260910/implementation/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-GPT-Review-20260910/implementation/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-GPT-Review-20260910/implementation/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-WP06-WP07-Road-Prep-GPT-Review-20260910/implementation/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Weather-Runtime-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Weather-Runtime-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Weather-Runtime-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/CityNexus-Weather-Runtime-Hardening-Checkpoint-20260910/backend/app/commerce/strengths_generated.py` | 13 | 13 | True |
| `review/CityNexus-Weather-Runtime-Hardening-Checkpoint-20260910/backend/app/db/models.py` | 343 | 343 | True |
| `review/CityNexus-Weather-Runtime-Hardening-Checkpoint-20260910/backend/app/schemas.py` | 353 | 353 | True |
| `review/ord0402-readouts/cross_lane_wire_check_r1.py` | 180 | 180 | True |
| `review/ord0402-readouts/http_acceptance_r1.py` | 175 | 175 | True |
