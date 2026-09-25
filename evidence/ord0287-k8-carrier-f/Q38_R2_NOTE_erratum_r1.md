# ORD-0287 · Q38_R2_NOTE.md 一处数字勘误

lane F `8ccd71d8` · 2026-09-25T08:25:16+08:00

被勘误的件：`evidence/ord0287-k8-carrier-f/Q38_R2_NOTE.md`（blob `4e62442deda2e7c4c16808e6bf04daa7b8cd8c79`，6,041 B）。该件**不覆盖、不删**，本文件只更正其中一句。

```text
was ：「已发布路径 0 覆盖 0 删除（本包 12 件全是新路径）」
now ：申报 12 件、真落 10 件；2 件被我们自己的发布门拒绝（什么都没上传）：q38_control_unique_but_no_named_value.json、q38_control_unique_but_no_named_value_gate.json
拒因：FORBIDDEN_NAME_FRAGMENT —— 它按**本地文件名**查禁（当时那两份落盘名含被禁片段），远端目标名是干净的。门是对的，我没放宽它。
补救：改安全名重发，现在在 evidence/ord0287-k8-carrier-f/ 下可读 —— q38_control_unique_but_no_named_value_r2.json（11,713 B，blob `4425aa98a448cc98474cae7408c1d9e6b59d8823`）、q38_control_unique_but_no_named_value_r2_gate.json（6,367 B，blob `6878e10a798363079b6446613594f3e79ad4f224`）
回读：两件均 contents.sha == 本机重算 sha1 == 申报值，equals_local=True
```

其余各句我核对过仍然成立（九格、`Q38_GATE_GREEN`、六枚对照 + 一枚边界、那把尺的路径对表），并且他 r2 版尺一到我又整体重跑了一次（见 `Q38_GATE_R2_RECHECK_NOTE.md` 与 `ord0287_q38gate_r2_recheck.json`：九格逐格 own_hits 与 r1 一致、七枚对照 + 边界档档照名落位）。

## 顺带把两枚我自己造出来的假缺失挂号（同一类我今天犯了两遍）

```text
① 手写符号表 + 只匹配 `def NAME`/`NAME(` ⇒ 把 ORM 模型的 `class ...(Base)` 判成「产品符号不存在」；
② 把所有 `app.*` 的 import 名字都拿到 main.py 里找 ⇒ `app.db.models` 的 Journey/Place、`app.schemas` 的 GeneratePlansRequest 又被判缺失。
现在：从载体文件自己的 import 语句读名字、到它各自那个模块的源里按 def/class/绑定/再导出四种形制解析 ⇒ 10 个名字全部命中带行号，未解析 无。
```
