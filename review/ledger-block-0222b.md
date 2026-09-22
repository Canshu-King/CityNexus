### 📦 e345b9d6（SESSION=e345b9d6）ORD-0222 证据面我自己发布了：`evidence/ord0222/` 10 个 blob 全 BYTE-LEVEL MATCH（含两层扫描原始读数与并排收据）@2026-09-22 20:5x +08

同一把尺子量 ORD-0220 之后，把 ORD-0222（`f7ce8ff`）也发到可读位置。`https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0222` — **10 次 PUT 全 201 ＋ BYTE-LEVEL MATCH，0 次 REFUSED**；独立回读 `remote entries=10 disagreements=0 on-disk-but-not-published=[]`（`review/readback-0222.txt`）。发布器 v3（本地 9,244 B，我算 blob `d0b1bb1eeb3d87f2`）。

| 文件 | 字节 | blob sha1[:16] | 是什么 |
|---|---|---|---|
| `f7ce8ff__source-and-parent.txt` | 672 | `9091bd2f5fe33b70` | source＋parent SHA、解释器、跑法 |
| `f7ce8ff__changed-files.txt` | 336 | `391a0c529bfc39d5` | changed-files |
| `f7ce8ff__f7ce8ff.patch` | 36,283 | `21435ccfea01aa85` | patch |
| `visual-text-scan.json` | 4,959 | `9b124843221ef811` | **VISUAL_TEXT_SCAN** 原始读数：四屏（hub/live/map/studio）逐屏 `hits`、`mixed`、`seen`（每屏该看到的行看到几枚） |
| `accessible-text-scan.json` | 4,555 | `c803ff567a013e8d` | **ACCESSIBLE_TEXT_SCAN** 原始读数（含 sr-only 与 aria-label 文本） |
| `unknown-value-fail-closed.json` | 398 | `10b358a9eb8f02b8` | 合成未知值那屏的实际渲染文字 |
| `days-payload-versus-visible-card.json` | 2,259 | `388491de9f69d4c8` | 仲裁要的**并排收据**：`options[].days[]` 原始字段 vs 日卡可见文本 ＋ `sourceOf` |
| `dark-scheme-scan.json` | 184 | `bfe2e3e6daff1f34` | 深色三屏扫描（`perScreen` 三个空数组＝0 命中） |
| `mutation-receipts.json` | 2,580 | `5e0d4906996978ee` | 四条突变的 nodeid／anchor_hits／anchor_bytes／bytes_changed／verdict ＋ 变红原文：本单的 `killAA1`（KILLED），并附 `killU1`/`killU2`（KILLED）与 `killV1`（SURVIVED）作对照 |
| `MANIFEST.txt` | 1,067 | `eb1886d8d2b12eb0` | 九件的名字、字节、sha256 |

**读数口径提醒（免得这批 blob 被读过头）**：这批收据钉的是"内部枚举不上屏、不上读屏输出"与"本单碰过的行不中英混排"，**不签"整屏无英文"**——`Arrival`/`Check in`/`Overnight`/`Five Great Avenues` 是服务器写进 `days[].activities[]` 的内容，`sourceOf` 那一栏就是给这一格定界的（星期属形式，已按 `days[].date` 本地化）。反向对照也在账：把三个产品文件退回 `f7ce8ff^` 跑同一条链 ⇒ 47 passed / **4 failed 全是这把新门**（`review/run-run079431.log`）。

**现场**：产品分支仍 0 次 push；未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；本轮 GitHub＝10 次 PUT ＋ 1 次只读 GET；账本只追加本块。

status: ORD-0222 **证据面闭合**（代码 `f7ce8ff`；`evidence/ord0222/` 10/10 MATCH）。至此 D 名下三批可读坐标：`evidence/ord0220/`（12）、`evidence/ord0221/`（7）、`evidence/ord0222/`（10）。
evidence: `review/evidence/ord0222/`、`review/readback-0222.txt`、`review/build-evidence-payload.py`、`review/readback-evidence.py`。
