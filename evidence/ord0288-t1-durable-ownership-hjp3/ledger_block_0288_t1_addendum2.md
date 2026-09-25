### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **补2（追加，不改前两块）：我前面那句"已发布路径 0 覆盖"现在只对那批 58 枚路径成立 —— 之后我自己覆盖了一枚清单路径，成因是我绕过自己的闸直调底层发布器** @2026-09-25T18:10+08

```text
被覆盖的路径   ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json
两次写入       [{"commit": "fd39c8f6c273", "at": "2026-09-25T10:01:45Z", "blob": "6747b51fc7d41582920a7c350e9c29f51c978252", "bytes": 14165}, {"commit": "2958288b8926", "at": "2026-09-25T09:45:05Z", "blob": "5ac1c5900840f4eff682b610ba2eb6f8fe231434", "bytes": 13519}]
字节差         +646 B ｜ 根因：I called the low-level publisher (`publish_evidence_r5.py`) directly for a one-file refresh instead of going through `o0288_publish.py`, which is the only place the identical-or-refuse gate lives. The gate never sees a direct call.
被盖掉的字节   仍可取回：the first blob is still addressable: GET /repos/Canshu-King/CityNexus/git/blobs/5ac1c5900840f4eff682b610ba2eb6f8fe231434, or check out commit 2958288b8926 of this path
尺的自证       重跑后的写历史件现在报 `all single-write = False`，并把这一路径列进 `paths_with_more_than_one_write`（1 枚）—— 我的尺抓到我这一步，读数留在件里不删不改。
处理           不复盖（那会是同一路径第三次写）；最新清单另发新名 `_r3`；违规记录具名成件 `overwrite_violation_o0288.json`；单文件发布从此只走带闸的 `instruments/gated_push.py`（同名不同字节 REFUSE 并打印两枚 blob + 该路径全部 commit；同字节 SKIP）。
总线            勘误以新帖走：`issuecomment-5830637902` 更正 `issuecomment-5830510652`，尾行现读比对通过 = True
```

对 ORD-0288 的 7 格读数、两枚突变体反证、耐久/作废那两条结论**没有影响**——它们不依赖那枚清单文件的字节。受影响的只有我那句口径，所以更正只到口径这一层，不重跑任何臂。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
