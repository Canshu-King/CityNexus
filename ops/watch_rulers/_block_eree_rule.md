## commander 执行令（第五条）@2026-09-22T18:54+08 —— **`EXTERNALLY_READABLE_EVIDENCE` 正式立为常驻规则**（仲裁 `5775164855` 点头）；ORD-0210 三个源文件已发布待他审；发布器自己也补发了

### ① 冻结原文照录（全体车道必须遵守，从本块生效）

```text
EXTERNALLY_READABLE_EVIDENCE

Any deliverable that requires external audit MUST expose an auditor-resolvable coordinate.
Accepted coordinates:
- a public/readable commit SHA, or
- readable repo + ref + path + Git blob sha1 for an evidence bundle.

A local-only SHA is NOT an audit coordinate.
If only a local SHA exists, state that explicitly.

If external audit is required and no resolvable coordinate exists:
  => EXTERNAL_AUDIT_BLOCKED / EVIDENCE_NOT_REACHABLE
  => no ACCEPTED-CODE / REPRODUCED claim may be signed by the external auditor.
```

配套（他上一轮已给、这轮重申）：交付 bundle 必须含 **source/parent SHA、changed-files、parent..source patch、必要运行收据**；publisher 上传后做一次**逐字节回读**。
**禁止**上载：secret / token / cookie / `.env` / `_live.db` / 用户库 / 未脱敏用户数据。
**并且他把上一轮的 `AUDIT_EVIDENCE_PUBLICATION` 并入本条**（"同一件事不长出两个名字"）——所以车道只需记这一个名字。

**给车道的动作（我把它翻成可执行的）**：
```text
交单时，凡要外部审计的：
1) 给出 source SHA 与 parent SHA；
2) 给出 changed-files 列表 + parent..source 的 patch；
3) 运行收据一并给；
4) 若这些只存在于本地，明确写 "LOCAL-ONLY, no resolvable coordinate" —— 不写就等于没交；
5) 用 live_checks/publish_evidence.py 发布到 Canshu-King/CityNexus @ commander/control，
   它会给回 blob sha1；把那个 sha1 贴进你的交付块。
```
**为什么立这条（今天的实证）**：`50b35e0` / `3e259bd` / `522c414` / `9514eb7` 在 GitHub 两仓**全部 422**（"No commit found for SHA"）⇒ 工作尖从未 push，**账本里写本地 SHA 对外部审计者等于不存在**。

### ② 他当场抓到我一个讽刺，我已修（这条我认）

他原话大意：**"`publish_evidence.py` 要成为默认动作的话，工具本身也必须先满足这条规则；我在两仓的 `commander/control/live_checks/publish_evidence.py` 都解析不到 ⇒ 先把它自己发布成可读 blob，再宣布所有车道默认用它。不然发布器自己是本地幽灵，多少有点讽刺。"**
⇒ **成立，已补**：

```text
live_checks/publish_evidence.py   3,372 B   blob sha1 1006c995fb6a526f   （PUT 201，BYTE-LEVEL MATCH）
```

### ③ ORD-0210 源审计包已发布（他列的四个待比对点都在里面）

他要审的是"我让他审的三个改动文件本身"，此前只有本地 `9514eb7`。现已发布：

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0210
  50b35e0__9514eb7.patch                    74,692 B  blob a20a989f847bf99a   （parent..source 全量）
  50b35e0__9514eb7.files.txt                   131 B  blob c96b5855a6e5d9e0
  _qoder_streak_receipt.py                  22,125 B  blob d3297d44bd60d26c   （= 9514eb7 里的 blob，git rev-parse 亲取）
  test_qoder_db_isolation_same_verdict.py   45,402 B  blob d1d466ce5819525e
  gate-acceptance-streak.yaml                5,140 B  blob 0b8947799280ff6c
```

**注**：那三个 `.py`/`.yaml` 的 blob sha1 我是用 `git rev-parse 9514eb7:<path>` **直接取的**，不是重新算的 ⇒ 他比对时拿到的就是源对象本身。
他列的四个比对点（classifier 是否真按 `(SHA,nodeid,shape)` 定性；whole-command exit 是否不会冒充 target-node verdict；YAML 是否覆盖 1–10 条与 reverse-mutation 条款；是否有偷加 sleep/retry/降并发/放宽断言的逃生口）——**我不预先替他答**，这是他的活。

### ④ 他这轮签的两条（我照录，不扩大）

```text
ORD-0210 RUNTIME RECEIPT / CLASSIFICATION OUTPUT = ACCEPTED-EVIDENCE
ORD-0210 IMPLEMENTATION MECHANISM              = PENDING-SOURCE-AUDIT
```

⇒ **运行收据那张（10 进程、10 库、全红、拒签 CLOSED）他接受了**；机制本身等他比对源文件。**我这边不动**，等他的源审计结论。

### ⑤ 现场

working tip `25165d9`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
