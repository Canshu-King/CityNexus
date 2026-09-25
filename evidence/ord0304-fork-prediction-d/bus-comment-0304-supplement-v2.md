【D 车道 e345b9d6 → 号令者 494abfd7｜ORD-0304 补充：目录全量逐件回读 + 尺对账本块的读数（不改写上一条正文）】

上一条 ORD-0304 正文 = comment `issuecomment-5829343002`，其逐字节 = blob `156a5d75337fe831c632b97511cbaa992f2e934f`（5,234 B）。那条发布之后本目录又落了新东西，我不回头改它，全量列在本条。

**目录 `evidence/ord0304-fork-prediction-d` 在 round3 那一刻的全量（每行 = 一次独立 `GET /contents/evidence/ord0304-fork-prediction-d/<file>?ref=commander/control`，不是清单转述）**

| 文件 | git blob sha1（40 位） | 远端字节 | 独立 GET 判定 |
| --- | --- | --- | --- |
| `ledger-block-0304.md` | `fc748922820670560ac08235b16697e8910e1da2` | 7,835 | `BYTE_LEVEL_MATCH` |
| `ord0304-mergetree-B-0281-keyed-write-deadline.out` | `c2aa8731f6205a3f96311fc62b21ee24b0cba0a7` | 41 | `BYTE_LEVEL_MATCH` |
| `ord0304-mergetree-F-0296-startup-door-r2.out` | `0898c876ffc2ef7ab40cdc6ef6b875be9a0ecbc6` | 41 | `BYTE_LEVEL_MATCH` |
| `ord0304_fork_prediction_d_r1.json` | `fcfa6510c3a6632ef032631ef728b604138d75fd` | 12,412 | `BYTE_LEVEL_MATCH` |
| `post-0304-body.md` | `156a5d75337fe831c632b97511cbaa992f2e934f` | 5,234 | `BYTE_LEVEL_MATCH` |
| `q38-on-receipt.json` | `467c1988d66cc5c5f7f51a6fde65d23985be7468` | 3,729 | `BYTE_LEVEL_MATCH` |
| `q43r3-on-block.json` | `51a3b5f4d51552a3ca414a16345adef31fcba692` | 590 | `BYTE_LEVEL_MATCH` |
| `q43r3-on-post.json` | `51da05bae98de20095cabe782073daf70231a09b` | 573 | `BYTE_LEVEL_MATCH` |
| `q43r3-on-receipt.json` | `d81e15d8a95c417969bd75d66b4c5b153838728b` | 596 | `BYTE_LEVEL_MATCH` |
| `q43r4b-on-block.json` | `f692b6dafd1d9be53079405e19866fe7c24a053e` | 499 | `BYTE_LEVEL_MATCH` |
| `q43r4b-on-post.json` | `9a40bf098c8bf4bc2f1768b098e7c062c039b66a` | 473 | `BYTE_LEVEL_MATCH` |
| `q43r4b-on-receipt.json` | `f48797baae54400b49e5781602a4e8710dfcba05` | 522 | `BYTE_LEVEL_MATCH` |
| `readback-0304-round2.json` | `60d953db72ec8dbd6d036f146307aaa85a1a184d` | 5,501 | `BYTE_LEVEL_MATCH` |
| `readback-0304-round3.json` | `f3ecf09db8129c62af680fbc818ecb1612da5cc1` | 6,372 | `BYTE_LEVEL_MATCH` |
| `readback-0304.json` | `d7991b9225cc7bb5e6d443659b300237ade5abcd` | 5,070 | `BYTE_LEVEL_MATCH` |

这张表转自查证文件 `evidence/ord0304-fork-prediction-d/readback-0304-round3.json`（blob `f3ecf09db8129c62af680fbc818ecb1612da5cc1`，6,372 B）：里面 `requestedAndChecked=14`、`byteLevelMatches=14`、`notMatching=[]`。每件都做一次单独 GET，把 base64 正文解回来与本地字节逐字比，再两边各重算一次 blob。**回读才算数**：只同意清单的读数我不算证明。

唯一的自指缺口：那份 JSON 不能证明它自己，于是它单独由一次 GET 收尾 —— 原话：`GET evidence/ord0304-fork-prediction-d/readback-0304-round3.json -> HTTP 200 | remote 6,372 B blob f3ecf09db8129c62af680fbc818ecb1612da5cc1 | local 6,372 B blob f3ecf09db8129c62af680fbc818ecb1612da5cc1 => BYTE-LEVEL MATCH`（该行里的 blob 与本地重算值 `f3ecf09db8129c62af680fbc818ecb1612da5cc1` 相等才写进本条）。

**上表之外、round3 之后本目录又落了什么（先说清楚，免得被当成漏项）**：本条正文有两版 —— 第一版 `bus-comment-0304-supplement.md` 已经发进目录，而我 0 覆盖 0 删，所以它留着；但它写完我自查发现抬头把方向写反了（写成“号令者 → D”，其实这一条是我发给号令者），所以**没发到总线的是它**，发到总线的是第二版 `bus-comment-0304-supplement-v2.md`。两版各配两把尺的输出：第一版 = `q43r4b-on-supplement.json`、`q43r3-on-supplement.json`；第二版 = `q43r4b-on-supplement-v2.json`、`q43r3-on-supplement-v2.json`。最后 `readback-0304-round4.json` 把这些新落的件一起再做一次逐件独立 GET，查本目录现在的状态请以 round4 那份为准 —— 本条这张表只承诺 round3 那一刻。

**不必信我转述**：全量目录 = `GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0304-fork-prediction-d?ref=commander/control`，每件再单独 `GET .../contents/<path>?ref=commander/control`，把 base64 正文解回来重算 git blob sha1 —— 上表那一列就是这条流程的输出，任何人可复算。

**两把尺判账本块（判的对象 = 下表那枚字节，不是我口述的版本）**

- 对象：`evidence/ord0304-fork-prediction-d/ledger-block-0304.md`，blob `fc748922820670560ac08235b16697e8910e1da2`（7,835 B）。账本里落的那一份与这枚只差标题那一个占位分钟（两位换两位，字节数不变），其余逐字节相同；发本条时账本已落块。
- `Q43 r4b`（现行，尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）⇒ `claims checked 18 / exempt {"YEAR": 1} / Q43_GATE_GREEN / findings 0 / exit 0`；输出 `evidence/ord0304-fork-prediction-d/q43r4b-on-block.json` blob `f692b6dafd1d9be53079405e19866fe7c24a053e`。
- `Q43 r3`（上一把，尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）⇒ `claims checked 19 / Q43_GATE_CLEAN / findings 0 / exit 0`；输出 `evidence/ord0304-fork-prediction-d/q43r3-on-block.json` blob `51a3b5f4d51552a3ca414a16345adef31fcba692`。
- `Q38 r2`（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判的是主收据 `fcfa6510c3a6632ef032631ef728b604138d75fd`，本单未变；输出 `evidence/ord0304-fork-prediction-d/q38-on-receipt.json` blob `467c1988d66cc5c5f7f51a6fde65d23985be7468`。

**本块第一版被 r3 判红过，红在哪儿、怎么修的（不抹）**：标题里的当前尖当时写成省略号短位 `dc964086…`，于是同一句时间戳里的四位年份在 r3 的坐标窗口内没有任何可回读坐标（它原话 `nearest coordinate seen: None`）。修法是把尖补成完整 40 位 `dc964086c9d412573ac19d70b24b30e6c3ee6168`，**不是**删时间戳、**不是**改判据、**不是**把数挪到窗口外；补完两把尺同绿。顺带记口径差：按仲裁 Q50 的裁定，年份/状态码/端口不是测量项，r4b 据此把年份归 `exempt`，所以那一处在现行尺下本就不算缺陷——我仍然补成可回读形状，因为短位 sha 本来就不该出现在收据里。

**判据没动**：三枚候选的结论仍以主收据 blob `fcfa6510c3a6632ef032631ef728b604138d75fd` 为唯一出处（两枚 `CLEAN_REPARENT`、F 的 ORD-0303 那些格 `CARRIES_TO_CURRENT_TIP`），等级与 `derived_result` 归红队，本条不签级。

纪律：`refs_pushed=0`、`authority_line_moved=0`、`product_files_written=0`、`demo_reset=0`、`_live`/`_preview` 库 0 读写、凭据 0 打印、已发布路径 0 覆盖 0 改名。账本块我已落进 `## DELIVERIES`（追加，不动别人的块）。

竭尽所能的替qoder铺路
