### CMDR 18:34 尺侧已修（车道 `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb`）：G4 补上「低于量程的第二处」这一半——**已经向模块要这个数的文件，一枚内联的 `busy_timeout = <整数>` 都不许再写**；候选 `2a648d7c09de1e6c19c8c368ef2657d811c78545`，五枚探针两向都跑并且逐枚点名是哪条断言咬住的

**基座与候选**：基座 `e7ff7938ea41c5ac69afb1172acc4625159c7911`（裁语那枚针），候选枝 `refs/heads/review/1d64acf5-ord0296-g4-floor-r1` = `2a648d7c09de1e6c19c8c368ef2657d811c78545`（`git ls-remote --refs` 现读逐字相同），只动一件：`backend/tests/test_qoder_ord0296_write_deadline.py` 从 blob `d3e21e9084a3589678d08f7b50afe5119b2b85b8` 到 `86636d66014dc29d2289496eb401315623f303be`。产品字节 0 枚——裁语第一节「不动产品」我照做，`PLAN_CLAIM_LEASE_MS` 那一格的语义未碰。

**改了什么（一句话）**：臂本来只把「内联数 ≥ 现读量程」当第二处来源，所以 `busy_timeout = 1200` 这种**低于量程**的抄件从底下走过（裁语点名的就是它）。现在加的是按**文件角色**判的一格：同一枚文件里只要出现具名符号（`busy_timeout_ms` / `write_busy_timeout_ms` / `busy_timeout_seconds`，也就是它已经在向模块或配置要数），它再写任何一枚内联 `busy_timeout = <整数>` 就当场红，不看大小。量程退回它本来那一半：不向模块要数的 worker 短等待照旧放行，但内联值不得 ≥ 量程。

**裁语里那句「`main.py` 命中数 == 1」我按现读改写了，具名报**：针 `e7ff7938ea41c5ac69afb1172acc4625159c7911` 上 `git grep -nE "busy_timeout *= *[0-9]+" backend/app/main.py` 命中 **0 枚**——main.py 只 `int(settings.write_busy_timeout_ms)`，不写数字；带内联数的三枚在 `app/catalog_hydration_operations.py:550`（500）与 `app/stay_generation_operations.py:310`（200）、`:505`（1500）。所以「命中数 == 1 在 main.py」这条如果逐字实现，臂今天就红。我实现的等价读法是：**具名那一处 = 它引用模块/配置符号；引用者不再写内联数**，这与裁语后半句「即只有具名那一处」同义。若号令者要的是别的数法，一句我就换。

**五枚探针（`floor_probe_r1.json`，跑在一枚私有导出树、每枚跑完 `git checkout --` 还原并 `hash-object` 与针上 blob 对回）**：P0_control=绿（期望 green）；P1_consumer_copy=红（期望 red）；P2_worker_at_floor=红（期望 red）；P3_new_worker_below=绿（期望 green）；P4_whole_family=绿（期望 green）。P1 红在新格（`backend/tests/test_qoder_ord0296_write_deadline.py:250`），P2 红在旧格（`backend/tests/test_qoder_ord0296_write_deadline.py:230`）——**这点很重要：量程那一半本来就有执法者，我这一格补的是它底下的空洞，不是重复执法**。P3 证明我没顺手收紧到把 worker 的 800 ms 也咬掉。

**族回归**：`tests/test_qoder_ord0296_write_deadline.py + tests/test_qoder_ord0479_dictionary_key_shape.py` 与字典键形尺两文件整跑 = `21 passed`（这代 21 枚），两枚 07:57 转绿的锚点格未回退。

**裁语第三件我已执行**：草稿架 `evidence/ord0479-0296-anchor-1605/` 的 6 枚与权威架 `evidence/ord0479-0296-anchor-1552/` 同名 6 枚逐枚 blob 相同，按「blob 对比后你自己执行」我把草稿架摘掉，前后各做一次整目录清点，除那 6 枚消失外其余逐枚不变；清点与删除的流水在同名件里。

**坐标与边界**：探针脚本 `floor_probe_r1.py`、流水 `floor_probe_r1.json`、候选收据 `land_g4_floor_receipt_r1.json`、补丁 `g4_floor_diff_r1.patch`（本块自身也按同名上架，落地后代次为 `2a648d7c09de1e6c19c8c368ef2657d811c78545`）；写这块时权威枝现读 `e7ff7938ea41c5ac69afb1172acc4625159c7911`，我的基座是上一枚针，换代请按常规 rebase。本轮 0 产品字节、0 其他测试文件改动、权威线 0 移动、账本 0 直写、`demo/reset` 0 次、共享 `_preview.db` 0 写、我这一道 0 个端口在跑。

