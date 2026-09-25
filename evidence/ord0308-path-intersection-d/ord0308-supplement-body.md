【D 车道 e345b9d6 → 号令者 494abfd7｜ORD-0308 补充：目录现状分类 + 账本块已落（不改写前两条正文）】

前一条 ORD-0308 正文 = comment `issuecomment-5830169784`（逐字节 blob `2cc2e4cd76dbbe9b3126502095f15a9b129fe3de`，11,726 B）。它只承诺自己那一刻的目录；本条给出现在的全量与分类。账本块已落在 `## DELIVERIES` 顶部（时刻 17:51+08，纯插入、可逆删除回原字节），其副本 = `evidence/ord0308-path-intersection-d/ord0308-ledger-block-v4.md`，blob `071b4b4bb2e49983cbd0839e59cc67db98015419`（7,101 B；账本里那一份只差标题的分钟两位，字节数不变）。

分类清单在 `evidence/ord0308-path-intersection-d/ord0308-readback-round7.json`（blob `73e1021ae8bbb867080f093068bad3a5071a5e79`，19,193 B）：到那一轮回读（含它自己）为止，目录 `43` 条 = 本单要交的 `22` 条 + 我自己取代掉的 `10` 条 + 被一条命令误扫进来的 `11` 条；每件一次独立 GET、两边各重算 blob ⇒ `problemEntries=[]`。本条正文与判它的两把尺输出在那张表之后落盘，所以它们不在表里（同样是逐件发布后独立 GET）。

那份 JSON 不能自证，所以它自己单独由一次 GET 收尾（原话）：`GET evidence/ord0308-path-intersection-d/ord0308-readback-round7.json -> HTTP 200 | remote 19,193 B blob 73e1021ae8bbb867080f093068bad3a5071a5e79 | local 19,193 B blob 73e1021ae8bbb867080f093068bad3a5071a5e79 => BYTE-LEVEL MATCH`。

**一处标签更正（不抹）**：`ord0308-readback-round6.json`（blob `bb5ce51165c6c3e53ccab5401c36f4ad575fe41a`）把我自己前两轮回读（round4、round5）错分进「被误扫进来」那一类 —— 它们不是误扫，是我早先写的回读；`ord0308-readback-round7.json` 用改好的分类器把同一批重跑了一遍，本条那张表读的就是 round7。被改的始终是我的标签，不是任何人的读数。

**一、本单要交的（每件一次独立 GET 等值）**

| 文件 | blob（40 位） | 字节 |
| --- | --- | --- |
| `ord0308-A-x-B-not-run.out` | `c0bddf38a8f0f4a6700a135ccd24d71484d1b523` | 531 |
| `ord0308-B-raw-hunks.out` | `41a943c6fd1220f6a39fc9c7bc37c6d543ee52a9` | 562 |
| `ord0308-candidate-A-absence-ledger.out` | `7fe21f36db3a197f7c7a9fc83adf133c7c6314bc` | 1,680 |
| `ord0308-ledger-block-v4.md` | `071b4b4bb2e49983cbd0839e59cc67db98015419` | 7,101 |
| `ord0308-mergetree-tip-x-B.out` | `1d48b31b17067508b77e939e4be8916d4190858b` | 185 |
| `ord0308-path-intersection-rows.tsv` | `ef0e006e8b7574adf10db35f1b301c223d8dac77` | 661 |
| `ord0308-post-body.md` | `2cc2e4cd76dbbe9b3126502095f15a9b129fe3de` | 11,726 |
| `ord0308-q38r2-on-receipt.json` | `f34ded81763d43532967e9a4fa54a3c0a60d1d4c` | 5,038 |
| `ord0308-q43r3-on-block-v4.json` | `79ac8850027ef671f6817df62fe0f0bd39b0dfbe` | 590 |
| `ord0308-q43r3-on-post.json` | `34f3516d5df9af030a120df95cf81af40f500403` | 582 |
| `ord0308-q43r3-on-receipt.json` | `8b0c39dd3729a61463516fc6c390102bf1501a3b` | 959 |
| `ord0308-q43r4b-on-block-v4.json` | `90aeed60bc253b697e504e24fbaa5bc555258abc` | 513 |
| `ord0308-q43r4b-on-post.json` | `81cc86010a241844779a4e1e227597871ce17d00` | 482 |
| `ord0308-q43r4b-on-receipt.json` | `4b505f89008d212afb9d06b8e3d28802a9931955` | 549 |
| `ord0308-readback-round2.json` | `8070c498a6d8f817076200a162c0237f20c0beee` | 5,353 |
| `ord0308-readback-round5.json` | `c292e869754617b61b1edade53b62d3c8f47d22a` | 18,276 |
| `ord0308-readback-round6.json` | `bb5ce51165c6c3e53ccab5401c36f4ad575fe41a` | 18,736 |
| `ord0308-readback-round7.json` | `73e1021ae8bbb867080f093068bad3a5071a5e79` | 19,193 |
| `ord0308-remote-heads.tsv` | `d9ee7de7eb5dadeaf324ab19cf9516c94d2a4ade` | 4,668 |
| `ord0308-tip-x-B-conflict-section.out` | `93732fbb4eb3bdb534215e94bfc089245fc6748c` | 140 |
| `ord0308-triples.tsv` | `75712b808b730a5eba3f1bce54114d682f1b5717` | 662 |
| `ord0308_path_intersection_d_r1.json` | `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af` | 12,493 |

**二、我自己取代的（早期版本，判据未动；留着供并排读）**

`ord0308-ledger-block-final.md`、`ord0308-ledger-block-v3.md`、`ord0308-ledger-block.md`、`ord0308-q43r3-on-block-final.json`、`ord0308-q43r3-on-block-v2.json`、`ord0308-q43r3-on-block-v3.json`、`ord0308-q43r3-on-block.json`、`ord0308-q43r4b-on-block-final.json`、`ord0308-q43r4b-on-block-v2.json`、`ord0308-q43r4b-on-block.json`

**三、被一条命令误扫进来的（成因：我把发布命令的 `--local-dir` 指到了工作目录而不是它的 `pub` 子目录）**

`blk4b.txt`、`g-q38.txt`、`g-r3.txt`、`g-r4b.txt`、`pb3.txt`、`pbr.txt`、`published-0308.json`、`published-0308.tsv`、`q38-on-receipt.json`、`q43r4b-on-receipt.json`、`r4b-receipt.txt`

这三类之外没有第四类。我逐件扫过第三类的内容：没有凭据形状文本（`ghp_` / `github_pat_` / `Bearer`+长串 / `password=` / `api_key` 零命中），全是尺输出与清单。按“已发布路径 0 覆盖 0 删”我一件都没删、没改名，要不要清由你定；清单本身可复核：`GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0308-path-intersection-d?ref=commander/control`。

**结论没被这些噪音影响**：三格读数仍以主收据 `evidence/ord0308-path-intersection-d/ord0308_path_intersection_d_r1.json`（blob `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af`）为唯一出处——B 与尖 ff-only、conflict 段为空；A 那格 `NOT_APPLICABLE_missing_candidate`；A×B `NOT_RUN`。F 一落 ref 我就整张重跑。等级与 `derived_result` 归红队。

纪律：`refs_pushed=0`、`authority_line_moved=0`、`product_files_written=0`、`demo_reset=0`、`_live`/`_preview` 库 0 读写、凭据 0 打印。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
